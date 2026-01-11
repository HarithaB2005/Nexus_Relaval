import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../components/AuthProvider';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function AuditPage() {
  const { currentUser, token } = useAuth();
  const [summary, setSummary] = useState(null);
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ type: '', severity: '' });
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchData();
  }, [token, days]);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [summaryRes, eventsRes] = await Promise.all([
        axios.get(`${API_BASE_URL}/api/v1/audit/summary?days=${days}`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_BASE_URL}/api/v1/audit/events?limit=50`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setSummary(summaryRes.data);
      setEvents(eventsRes.data.events || []);
    } catch (error) {
      console.error('Failed to fetch audit data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500';
      case 'high': return 'bg-orange-500';
      case 'medium': return 'bg-yellow-500';
      default: return 'bg-blue-500';
    }
  };

  const getEventTypeIcon = (type) => {
    switch (type) {
      case 'safety_block': return '🛡️';
      case 'quality_reject': return '⚠️';
      case 'rate_limit': return '🚦';
      case 'validation_error': return '❌';
      default: return '📋';
    }
  };

  return (
    <div className="min-h-screen gradient-bg text-white">
      <div className="container mx-auto px-6 py-12">
        <header className="mb-8">
          <h1 className="text-4xl font-bold gradient-text">Registry of Truth</h1>
          <p className="text-gray-300 mt-2">Governance Dashboard - Audit Transparency & Safety Events</p>
        </header>

        {/* Summary Stats */}
        {summary && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="card">
              <h3 className="text-sm text-gray-400 mb-2">Total Events</h3>
              <div className="text-3xl font-bold">{summary.total_events}</div>
              <p className="text-xs text-gray-500 mt-1">Last {days} days</p>
            </div>
            
            <div className="card">
              <h3 className="text-sm text-gray-400 mb-2">Safety Blocks</h3>
              <div className="text-3xl font-bold text-red-400">
                {summary.events_by_type?.safety_block || 0}
              </div>
              <p className="text-xs text-gray-500 mt-1">Content blocked</p>
            </div>
            
            <div className="card">
              <h3 className="text-sm text-gray-400 mb-2">Quality Rejections</h3>
              <div className="text-3xl font-bold text-yellow-400">
                {summary.events_by_type?.quality_reject || 0}
              </div>
              <p className="text-xs text-gray-500 mt-1">Below threshold</p>
            </div>
            
            <div className="card">
              <h3 className="text-sm text-gray-400 mb-2">Critical Events</h3>
              <div className="text-3xl font-bold text-orange-400">
                {summary.events_by_severity?.critical || 0}
              </div>
              <p className="text-xs text-gray-500 mt-1">High risk blocks</p>
            </div>
          </div>
        )}

        {/* Events by Severity */}
        {summary && (
          <div className="card mb-8">
            <h3 className="text-lg font-semibold mb-4">Events by Severity</h3>
            <div className="flex gap-4">
              {Object.entries(summary.events_by_severity || {}).map(([severity, count]) => (
                <div key={severity} className="flex items-center gap-2">
                  <div className={`w-4 h-4 rounded-full ${getSeverityColor(severity)}`}></div>
                  <span className="capitalize">{severity}</span>
                  <span className="text-gray-400">({count})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Recent Critical Events */}
        {summary?.critical_events?.length > 0 && (
          <div className="card mb-8 bg-red-500/10 border border-red-500/30">
            <h3 className="text-lg font-semibold mb-4 text-red-400">🚨 Recent Critical Events</h3>
            <div className="space-y-2">
              {summary.critical_events.slice(0, 5).map((event, idx) => (
                <div key={idx} className="flex items-start gap-3 p-3 bg-brand-darker rounded">
                  <span className="text-red-400 text-xl">⚠️</span>
                  <div className="flex-1">
                    <p className="text-sm">{event.reason}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(event.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Event Log */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Audit Event Log</h3>
            <button onClick={fetchData} className="btn-primary text-sm py-2 px-4">
              Refresh
            </button>
          </div>

          {loading ? (
            <p className="text-gray-400">Loading events...</p>
          ) : events.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No audit events found</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-gray-400 border-b border-brand-purple/20">
                  <tr>
                    <th className="py-3 text-left">Type</th>
                    <th className="py-3 text-left">Severity</th>
                    <th className="py-3 text-left">Reason</th>
                    <th className="py-3 text-left">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((event) => (
                    <tr key={event.id} className="border-t border-brand-purple/10 hover:bg-brand-purple/5">
                      <td className="py-3">
                        <span className="flex items-center gap-2">
                          {getEventTypeIcon(event.event_type)}
                          <span className="capitalize">{event.event_type.replace('_', ' ')}</span>
                        </span>
                      </td>
                      <td className="py-3">
                        <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${getSeverityColor(event.severity)} text-white`}>
                          {event.severity}
                        </span>
                      </td>
                      <td className="py-3 max-w-md">
                        <p className="truncate">{event.reason}</p>
                        {event.input_preview && (
                          <p className="text-xs text-gray-500 mt-1 truncate">Input: {event.input_preview}</p>
                        )}
                      </td>
                      <td className="py-3 text-gray-400">
                        {new Date(event.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Investor Value Proposition */}
        <div className="card mt-8 bg-gradient-to-r from-purple-600/20 to-pink-600/20 border-purple-500/30">
          <h3 className="text-lg font-semibold mb-3">💼 Legal Armor</h3>
          <p className="text-gray-300">
            This Registry of Truth provides complete audit transparency. Every time our AI Auditor blocks harmful content,
            it's logged here with full context. This is your insurance policy against "Death by AI" lawsuits and regulatory violations.
          </p>
          <div className="mt-4 grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-green-400">{summary?.total_events || 0}</div>
              <div className="text-xs text-gray-400">Events Prevented</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-blue-400">100%</div>
              <div className="text-xs text-gray-400">Audit Coverage</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-purple-400">Real-time</div>
              <div className="text-xs text-gray-400">Monitoring</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
