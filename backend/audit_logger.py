# audit_logger.py - Registry of Truth audit logging
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from db.database import get_db_pool

logger = logging.getLogger("AuditLogger")

async def log_audit_event(
    client_id: str,
    event_type: str,
    severity: str,
    reason: str,
    input_preview: Optional[str] = None,
    output_preview: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Log audit event to Registry of Truth (governance_audit_events table).
    
    This is the core of the "Registry of Truth" - tracks every rejection,
    hallucination block, quality issue, and safety violation.
    
    Args:
        client_id: User ID
        event_type: 'hallucination_blocked', 'quality_reject', 'safety_violation', 'rate_limit', 'validation_error'
        severity: 'critical', 'high', 'medium', 'low'
        reason: Human-readable explanation (e.g., "Blocked high-risk medical dosage recommendation")
        input_preview: First 500 chars of input
        output_preview: First 500 chars of output
        metadata: Additional context (scores, iterations, thresholds, etc.)
    """
    try:
        pool = get_db_pool()
        
        # Truncate previews
        if input_preview and len(input_preview) > 500:
            input_preview = input_preview[:500] + "..."
        if output_preview and len(output_preview) > 500:
            output_preview = output_preview[:500] + "..."
        
        # Extract metric from metadata if available
        metric_value = None
        metric_name = None
        if metadata:
            metric_value = metadata.get("score")
            metric_name = metadata.get("metric_name", "quality_score")
        
        event_id = uuid.uuid4()
        
        async with pool.acquire() as conn:
            # Insert into governance_audit_events (Registry of Truth)
            await conn.execute("""
                INSERT INTO governance_audit_events (
                    event_id, client_id, event_type, severity, reason, 
                    input_preview, output_preview, metric_value, metric_name
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, event_id, client_id, event_type, severity, reason, 
                input_preview, output_preview, metric_value, metric_name)
            
            # If this is a major error/rejection, also add to "Saved Errors" for quick access
            if severity in ['critical', 'high'] and event_type in ['hallucination_blocked', 'quality_reject', 'safety_violation']:
                await _save_error_to_registry(conn, client_id, event_type, reason, severity)
            
            # Update daily governance summary
            await _update_governance_summary(conn, client_id, event_type, metric_value)
        
        logger.info(f"✓ Registry event logged: {event_type} [{severity}] for {client_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        return False


async def _save_error_to_registry(conn, client_id: str, event_type: str, reason: str, severity: str) -> None:
    """Add or update saved error in the registry"""
    try:
        # Map event types to error categories
        category_map = {
            'hallucination_blocked': 'hallucination_detection',
            'quality_reject': 'quality_assurance',
            'safety_violation': 'safety_violation'
        }
        category = category_map.get(event_type, event_type)
        
        # Check if similar error already exists
        existing = await conn.fetchval("""
            SELECT error_id FROM governance_saved_errors
            WHERE client_id = $1 AND error_category = $2
            ORDER BY last_detected DESC LIMIT 1
        """, client_id, category)
        
        if existing:
            # Update existing error
            await conn.execute("""
                UPDATE governance_saved_errors
                SET times_blocked = times_blocked + 1,
                    last_detected = NOW()
                WHERE error_id = $1
            """, existing)
        else:
            # Create new saved error
            await conn.execute("""
                INSERT INTO governance_saved_errors (
                    error_id, client_id, error_category, error_description, 
                    impact_level, times_blocked
                ) VALUES ($1, $2, $3, $4, $5, 1)
            """, uuid.uuid4(), client_id, category, reason, severity)
    except Exception as e:
        logger.warning(f"Failed to save error to registry: {e}")


async def _update_governance_summary(conn, client_id: str, event_type: str, metric_value: Optional[float]) -> None:
    """Update daily governance summary statistics"""
    try:
        # Get or create today's summary
        existing = await conn.fetchrow("""
            SELECT summary_id FROM governance_summary
            WHERE client_id = $1 AND summary_date = CURRENT_DATE
        """, client_id)
        
        if existing:
            summary_id = existing['summary_id']
        else:
            summary_id = await conn.fetchval("""
                INSERT INTO governance_summary (client_id, summary_date)
                VALUES ($1, CURRENT_DATE)
                RETURNING summary_id
            """, client_id)
        
        # Increment appropriate counter
        if event_type == 'hallucination_blocked':
            await conn.execute("""
                UPDATE governance_summary
                SET hallucinations_blocked = hallucinations_blocked + 1
                WHERE summary_id = $1
            """, summary_id)
        elif event_type == 'quality_reject':
            await conn.execute("""
                UPDATE governance_summary
                SET quality_issues_found = quality_issues_found + 1
                WHERE summary_id = $1
            """, summary_id)
        elif event_type == 'safety_violation':
            await conn.execute("""
                UPDATE governance_summary
                SET safety_violations_detected = safety_violations_detected + 1
                WHERE summary_id = $1
            """, summary_id)
        
        # Increment total rejections
        await conn.execute("""
            UPDATE governance_summary
            SET total_rejections = total_rejections + 1
            WHERE summary_id = $1
        """, summary_id)
        
        # Update average quality score if metric provided
        if metric_value is not None:
            current = await conn.fetchrow("""
                SELECT avg_quality_score FROM governance_summary
                WHERE summary_id = $1
            """, summary_id)
            
            if current and current['avg_quality_score']:
                new_avg = (float(current['avg_quality_score']) + metric_value) / 2
            else:
                new_avg = metric_value
            
            await conn.execute("""
                UPDATE governance_summary
                SET avg_quality_score = $1
                WHERE summary_id = $2
            """, new_avg, summary_id)
    except Exception as e:
        logger.warning(f"Failed to update governance summary: {e}")


async def get_audit_events(
    client_id: Optional[str] = None,
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """Retrieve audit events from Registry of Truth with filters"""
    try:
        pool = get_db_pool()
        conditions = []
        params = []
        idx = 1
        
        if client_id:
            conditions.append(f"client_id = ${idx}")
            params.append(client_id)
            idx += 1
        if event_type:
            conditions.append(f"event_type = ${idx}")
            params.append(event_type)
            idx += 1
        if severity:
            conditions.append(f"severity = ${idx}")
            params.append(severity)
            idx += 1
        
        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"""
            SELECT event_id, client_id, event_type, severity, 
                   reason, input_preview, output_preview, 
                   metric_value, metric_name, created_at
            FROM governance_audit_events 
            WHERE {where}
            ORDER BY created_at DESC LIMIT ${idx} OFFSET ${idx+1}
        """
        params.extend([limit, offset])
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [
                {
                    "event_id": str(row["event_id"]),
                    "client_id": row["client_id"],
                    "event_type": row["event_type"],
                    "severity": row["severity"],
                    "reason": row["reason"],
                    "input_preview": row["input_preview"],
                    "output_preview": row["output_preview"],
                    "metric_value": float(row["metric_value"]) if row["metric_value"] else None,
                    "metric_name": row["metric_name"],
                    "created_at": row["created_at"].isoformat() if row["created_at"] else None
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get audit events: {e}")
        return []


async def get_saved_errors(client_id: str, limit: int = 50) -> list:
    """Get the 'Saved Errors' - the highest-value governance insights"""
    try:
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT error_id, error_category, error_description, impact_level,
                       times_blocked, first_detected, last_detected
                FROM governance_saved_errors
                WHERE client_id = $1
                ORDER BY times_blocked DESC, last_detected DESC
                LIMIT $2
            """, client_id, limit)
            
            return [
                {
                    "error_id": str(row["error_id"]),
                    "category": row["error_category"],
                    "description": row["error_description"],
                    "impact": row["impact_level"],
                    "blocked_count": row["times_blocked"],
                    "first_detected": row["first_detected"].isoformat(),
                    "last_detected": row["last_detected"].isoformat()
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get saved errors: {e}")
        return []


async def get_audit_summary(client_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
    """Get aggregated audit stats for the governance dashboard"""
    try:
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            # Total events in period
            conditions = f"created_at >= NOW() - INTERVAL '{days} days'"
            if client_id:
                conditions += f" AND client_id = '{client_id}'"
            
            total = await conn.fetchval(f"SELECT COUNT(*) FROM governance_audit_events WHERE {conditions}")
            
            # Get today's summary for this user
            summary = None
            if client_id:
                summary = await conn.fetchrow("""
                    SELECT * FROM governance_summary
                    WHERE client_id = $1 AND summary_date = CURRENT_DATE
                """, client_id)
            
            # Events by type
            by_type = await conn.fetch(f"""
                SELECT event_type, COUNT(*) as count
                FROM governance_audit_events WHERE {conditions}
                GROUP BY event_type ORDER BY count DESC
            """)
            
            # Events by severity
            by_severity = await conn.fetch(f"""
                SELECT severity, COUNT(*) as count
                FROM governance_audit_events WHERE {conditions}
                GROUP BY severity ORDER BY 
                CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 
                              WHEN 'medium' THEN 3 ELSE 4 END
            """)
            
            # Recent critical events
            critical = await conn.fetch(f"""
                SELECT reason, created_at FROM governance_audit_events
                WHERE {conditions} AND severity IN ('critical', 'high')
                ORDER BY created_at DESC LIMIT 10
            """)
            
            # Saved errors count
            saved_errors_count = 0
            if client_id:
                saved_errors_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM governance_saved_errors
                    WHERE client_id = $1
                """, client_id)
            
            return {
                "total_events": total or 0,
                "total_rejections": summary["total_rejections"] if summary else 0,
                "hallucinations_blocked": summary["hallucinations_blocked"] if summary else 0,
                "quality_issues_found": summary["quality_issues_found"] if summary else 0,
                "safety_violations_detected": summary["safety_violations_detected"] if summary else 0,
                "saved_errors_count": saved_errors_count or 0,
                "avg_quality_score": float(summary["avg_quality_score"]) if summary and summary["avg_quality_score"] else 0.95,
                "events_by_type": {r["event_type"]: r["count"] for r in by_type},
                "events_by_severity": {r["severity"]: r["count"] for r in by_severity},
                "critical_events": [
                    {"reason": r["reason"], "timestamp": r["created_at"].isoformat()}
                    for r in critical
                ],
                "period_days": days
            }
    except Exception as e:
        logger.error(f"Failed audit summary: {e}")
        return {
            "total_events": 0,
            "total_rejections": 0,
            "hallucinations_blocked": 0,
            "quality_issues_found": 0,
            "safety_violations_detected": 0,
            "saved_errors_count": 0,
            "avg_quality_score": 0.95,
            "events_by_type": {},
            "events_by_severity": {},
            "critical_events": [],
            "period_days": days
        }

