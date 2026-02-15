#!/bin/bash
# Quick Deploy Script (Optional Helper)
# Run this to validate your setup before deploying to cloud

set -e

echo "🚀 Relevo Pre-Deployment Validation"
echo "======================================"

# Check Python
echo "✓ Checking Python..."
python --version

# Check Node
echo "✓ Checking Node..."
node --version
npm --version

# Check Docker (optional)
if command -v docker &> /dev/null; then
    echo "✓ Docker is installed"
else
    echo "⚠ Docker not found (optional for cloud deployment)"
fi

# Check backend dependencies
echo "✓ Checking backend dependencies..."
pip list | grep -E "fastapi|asyncpg|pydantic" || echo "⚠ Install requirements: pip install -r backend/requirements.txt"

# Check frontend dependencies
echo "✓ Checking frontend dependencies..."
cd frontend && npm list react react-router-dom || echo "⚠ Install dependencies: npm install"
cd ..

# Check environment files
echo "✓ Checking environment files..."
[ -f "backend/.env" ] && echo "  ✓ backend/.env exists" || echo "  ⚠ Create backend/.env from .env.example"
[ -f ".env.production.example" ] && echo "  ✓ .env.production.example exists" || echo "  ⚠ Missing .env.production.example"

# Check migration files
echo "✓ Checking migrations..."
[ -f "db/migrations/2025-12-28_add_vip_and_usage_fields.sql" ] && echo "  ✓ Migration file exists" || echo "  ⚠ Migration file missing"

# Summary
echo ""
echo "======================================"
echo "✅ Pre-deployment checks complete!"
echo ""
echo "Next: Follow DEPLOYMENT.md for cloud setup"
echo "======================================"
