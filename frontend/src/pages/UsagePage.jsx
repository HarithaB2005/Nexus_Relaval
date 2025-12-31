import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../components/AuthProvider';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function UsagePage() {
  const { currentUser } = useAuth();
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function fetchUsage() {
      try {
        const [sumRes, histRes] = await Promise.all([
          axios.get(`${API_BASE_URL}/usage/summary`),
          axios.get(`${API_BASE_URL}/usage/history`),
        ]);
        if (!mounted) return;
        setSummary(sumRes.data || {});
        setHistory(histRes.data || []);
      } catch (err) {
        if (!mounted) return;
        console.warn('Usage fetch failed', err);
        setError(err?.response?.data?.detail || 'Unable to load usage data right now.');
      } finally {
        if (mounted) setLoading(false);
      }
    }
    fetchUsage();
    return () => { mounted = false; };
  }, []);

  const exportCSV = () => {
    const rows = history.map(h => `${h.date},${h.requests},${h.tokens},${h.cost}`).join('\n');
    const csv = 'date,requests,tokens,cost\n' + rows;
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'usage_history.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen gradient-bg text-white">
      <div className="container mx-auto px-6 py-12">
        <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-300">Account: {currentUser?.client_name || '—'}</p>
            <h1 className="text-4xl font-bold gradient-text">Usage & Analytics</h1>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-2 bg-brand-purple/20 border border-brand-purple/30 rounded-lg text-sm max-w-max">
            <span className="text-gray-200">Plan limit:</span>
            <span className="font-semibold text-white">{formatPlanLimit(currentUser?.plan_limit ?? summary?.plan_limit)}</span>
          </div>
        </header>

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/50 text-red-300 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="card col-span-1">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Summary (30d)</h2>
              <span className="text-xs text-gray-400">Last 30 days</span>
            </div>
            {loading ? <p className="text-gray-400">Loading summary...</p> : (
              <div className="space-y-3">
                <Stat label="Requests" value={formatNumber(summary?.requests_30d ?? 0)} />
                <Stat label="Tokens" value={formatNumber(summary?.tokens_30d ?? 0)} />
                <Stat label="Estimated Cost" value={formatCurrency(summary?.cost_30d ?? 0)} />
                {typeof (currentUser?.plan_limit ?? summary?.plan_limit) === 'number' && typeof summary?.requests_30d === 'number' && (
                  <div className="mt-2">
                    <p className="text-xs text-gray-300 mb-1">Usage vs Plan</p>
                    <div className="w-full h-2 bg-brand-darker rounded">
                      <div
                        className="h-2 bg-brand-purple rounded"
                        style={{ width: `${Math.min(100, Math.round((summary.requests_30d / Math.max(1, (currentUser?.plan_limit ?? summary.plan_limit))) * 100))}%` }}
                      />
                    </div>
                  </div>
                )}
                <div className="mt-4">
                  <button onClick={exportCSV} className="btn-primary w-full">Export CSV</button>
                </div>
              </div>
            )}
          </section>

          <section className="card col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white">Recent Usage</h2>
              <span className="text-xs text-gray-400">Daily aggregates</span>
            </div>
            {loading ? <p className="text-gray-400">Loading history...</p> : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-gray-200">
                  <thead className="text-gray-400">
                    <tr>
                      <th className="py-2 text-left">Date</th>
                      <th className="py-2 text-right">Requests</th>
                      <th className="py-2 text-right">Tokens</th>
                      <th className="py-2 text-right">Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.length === 0 ? (
                      <tr><td colSpan={4} className="py-4 text-gray-500 text-center">No usage data available.</td></tr>
                    ) : (
                      history.map(row => (
                        <tr key={row.date} className="border-t border-brand-purple/10">
                           <td className="py-2">{new Date(row.date).toLocaleDateString()}</td>
                          <td className="py-2 text-right">{formatNumber(row.requests)}</td>
                          <td className="py-2 text-right">{formatNumber(row.tokens)}</td>
                          <td className="py-2 text-right">{formatCurrency(row.cost)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </main>
      </div>
    </div>
  );
}

const Stat = ({ label, value }) => (
  <div className="flex items-center justify-between bg-brand-darker rounded-lg px-4 py-3 border border-brand-purple/10">
    <span className="text-gray-400 text-sm">{label}</span>
    <span className="text-white font-semibold">{value}</span>
  </div>
);

function formatNumber(n) {
  try { return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(Number(n) || 0); }
  catch { return String(n); }
}

function formatCurrency(n) {
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(Number(n) || 0); }
  catch { return `$${Number(n).toFixed(2)}`; }
}

function formatPlanLimit(n) {
  const num = Number(n);
  if (!num || Number.isNaN(num)) return '—';
  if (num >= 1_000_000) return 'Unlimited';
  return `${formatNumber(num)} requests`;
}
