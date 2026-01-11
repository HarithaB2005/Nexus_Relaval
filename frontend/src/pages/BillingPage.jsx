import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../components/AuthProvider';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function BillingPage() {
  const { currentUser } = useAuth();
  const [plan, setPlan] = useState(null);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function fetchBilling() {
        try {
            const [planRes, invRes] = await Promise.all([
              axios.get(`${API_BASE_URL}/billing/plan`),
              axios.get(`${API_BASE_URL}/billing/invoices`),
            ]);
            if (!mounted) return;
            setPlan(planRes.data || null);
            setInvoices(invRes.data || []);
        } catch (err) {
            if (!mounted) return;
            console.warn('Billing fetch failed', err);
        setError(err?.response?.data?.detail || 'Unable to load billing data right now.');
        } finally {
            if (mounted) setLoading(false);
        }
    }
    fetchBilling();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="min-h-screen gradient-bg text-white">
      <div className="container mx-auto px-6 py-12">
        <header className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm text-gray-300">Account: {currentUser?.client_name || '—'}</p>
            <h1 className="text-4xl font-bold gradient-text">Billing & Subscription</h1>
          </div>
          <div className="inline-flex items-center gap-2 px-3 py-2 bg-brand-purple/20 border border-brand-purple/30 rounded-lg text-sm max-w-max">
            <span className="text-gray-200">Plan limit:</span>
            <span className="font-semibold text-white">{formatPlanLimit(currentUser?.plan_limit)}</span>
          </div>
        </header>

        {error && (
          <div className="mb-6 bg-red-500/10 border border-red-500/50 text-red-300 px-4 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        <main className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="card col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Current Plan</h2>
              <span className="text-xs text-gray-300">Auto-billed monthly</span>
            </div>
            {loading ? (
              <p className="text-gray-400">Loading plan...</p>
            ) : (
              <div>
                {plan ? (
                  <div className="space-y-2">
                    <p className="font-semibold text-white">{plan.name} — {formatCurrency(plan.price_monthly)}/mo</p>
                    <p className="text-sm text-gray-400">{plan.description}</p>
                    <div className="mt-4 flex gap-3">
                      <button onClick={() => setShowPlanModal(true)} className="btn-primary">Change Plan</button>
                      <button onClick={() => alert('Contract generation coming soon!')} className="btn-secondary">Download Contract</button>
                    </div>
                  </div>
                ) : (
                  <div>
                    <p className="text-gray-400">No active plan found. Contact sales to provision enterprise plans.</p>
                    <div className="mt-4">
                      <button className="btn-primary">Contact Sales</button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>

          <aside className="card">
            <h3 className="font-semibold mb-2 text-white">Payment Method</h3>
            <p className="text-sm text-gray-300">Card ending in •••• 4242 (Stripe)</p>
            <div className="mt-4">
              <button onClick={() => setShowPaymentModal(true)} className="btn-secondary w-full">Update Payment Method</button>
            </div>
          </aside>

          <section className="card col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">Invoices</h2>
              <span className="text-xs text-gray-400">Past charges</span>
            </div>
            {loading ? (
              <p className="text-gray-300">Loading invoices...</p>
            ) : invoices.length === 0 ? (
              <p className="text-gray-300">No invoices available.</p>
            ) : (
              <table className="w-full text-left border-collapse text-sm text-gray-200">
                <thead>
                  <tr className="text-gray-400">
                    <th className="pb-2">Date</th>
                    <th className="pb-2">Amount</th>
                    <th className="pb-2">Status</th>
                    <th className="pb-2">Download</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map(inv => (
                    <tr key={inv.id} className="border-t border-brand-purple/10">
                      <td className="py-2">{new Date(inv.date).toLocaleDateString()}</td>
                      <td className="py-2">{formatCurrency(inv.amount)}</td>
                      <td className="py-2">{inv.status}</td>
                      <td className="py-2">{inv.download_url ? (<a href={inv.download_url} className="text-brand-purple-lighter">PDF</a>) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        </main>

        {/* Plan Change Modal */}
        {showPlanModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowPlanModal(false)}>
            <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-6 max-w-2xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Choose Your Plan</h2>
                <button onClick={() => setShowPlanModal(false)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Free Plan */}
                <div className="border border-slate-600 rounded-lg p-4 hover:border-brand-purple transition-colors">
                  <h3 className="text-lg font-semibold text-white mb-2">Free</h3>
                  <p className="text-3xl font-bold text-white mb-2">$0<span className="text-sm text-gray-400">/mo</span></p>
                  <ul className="text-sm text-gray-300 space-y-2 mb-4">
                    <li>✓ 50 requests/month</li>
                    <li>✓ Basic support</li>
                    <li>✓ Community access</li>
                  </ul>
                  <button onClick={() => { alert('Already on Free plan or contact support to downgrade'); setShowPlanModal(false); }} className="btn-secondary w-full">Select Free</button>
                </div>

                {/* Pro Plan */}
                <div className="border-2 border-brand-purple rounded-lg p-4 bg-brand-purple/5">
                  <div className="text-xs bg-brand-purple text-white px-2 py-1 rounded-full w-fit mb-2">Popular</div>
                  <h3 className="text-lg font-semibold text-white mb-2">Pro</h3>
                  <p className="text-3xl font-bold text-white mb-2">$29<span className="text-sm text-gray-400">/mo</span></p>
                  <ul className="text-sm text-gray-300 space-y-2 mb-4">
                    <li>✓ 1,000 requests/month</li>
                    <li>✓ Priority support</li>
                    <li>✓ Advanced features</li>
                    <li>✓ API access</li>
                  </ul>
                  <button onClick={async () => {
                    try {
                      const res = await axios.post(`${API_BASE_URL}/billing/upgrade/pro`, {}, {
                        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` }
                      });
                      alert(`✓ Upgraded to VIP! Plan limit: ${res.data.plan_limit} requests/month`);
                      setShowPlanModal(false);
                      window.location.reload();
                    } catch (e) {
                      alert(`Error: ${e.response?.data?.detail || e.message}`);
                    }
                  }} className="btn-primary w-full">Upgrade to Pro</button>
                </div>

                {/* Enterprise Plan */}
                <div className="border border-slate-600 rounded-lg p-4 hover:border-brand-purple transition-colors">
                  <h3 className="text-lg font-semibold text-white mb-2">Enterprise</h3>
                  <p className="text-3xl font-bold text-white mb-2">$99<span className="text-sm text-gray-400">/mo</span></p>
                  <ul className="text-sm text-gray-300 space-y-2 mb-4">
                    <li>✓ Unlimited requests</li>
                    <li>✓ Dedicated support</li>
                    <li>✓ Custom integration</li>
                    <li>✓ SLA guarantee</li>
                  </ul>
                  <button onClick={() => { alert('Contact sales@relevo.ai for Enterprise'); setShowPlanModal(false); }} className="btn-secondary w-full">Contact Sales</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Payment Method Modal */}
        {showPaymentModal && (
          <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setShowPaymentModal(false)}>
            <div className="bg-[#1e293b] border border-slate-700 rounded-xl p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-white">Update Payment Method</h2>
                <button onClick={() => setShowPaymentModal(false)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
              </div>
              
              <div className="space-y-4">
                <p className="text-sm text-gray-300 mb-4">Secure payment processing via Stripe</p>
                
                <div className="border border-yellow-500/50 bg-yellow-500/10 rounded-lg p-4">
                  <p className="text-sm text-yellow-200">
                    🔒 Stripe integration will be enabled in production. For now, payment method updates are simulated.
                  </p>
                </div>

                <div className="bg-slate-800 rounded-lg p-4 space-y-3">
                  <div>
                    <label className="text-xs text-gray-400">Current Method</label>
                    <p className="text-white">Visa •••• 4242</p>
                  </div>
                  <div>
                    <label className="text-xs text-gray-400">Expires</label>
                    <p className="text-white">12/2026</p>
                  </div>
                </div>

                <div className="flex gap-3">
                  <button onClick={() => { alert('Stripe checkout will open here in production'); setShowPaymentModal(false); }} className="btn-primary flex-1">Update via Stripe</button>
                  <button onClick={() => setShowPaymentModal(false)} className="btn-secondary flex-1">Cancel</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function formatCurrency(n) {
  try { return new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' }).format(Number(n) || 0); }
  catch { return `$${Number(n).toFixed(2)}`; }
}

// Helpers missing earlier: keep consistent with UsagePage
function formatNumber(n) {
  try { return new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(Number(n) || 0); }
  catch { return String(n); }
}

function formatPlanLimit(n) {
  const num = Number(n);
  if (!num || Number.isNaN(num)) return '—';
  if (num >= 1_000_000) return 'Unlimited';
  return `${formatNumber(num)} requests`;
}
