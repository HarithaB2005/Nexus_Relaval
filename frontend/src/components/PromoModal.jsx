import React, { useState } from 'react';
import axios from 'axios';

const PromoModal = ({ isOpen, onClose, token, onRefreshUser }) => {
    const [code, setCode] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    if (!isOpen) return null;

    const handleRedeem = async () => {
        setLoading(true);
        setError('');
        try {
            await axios.post(`${process.env.REACT_APP_API_URL}/auth/redeem-promo`, 
                { code }, 
                { headers: { Authorization: `Bearer ${token}` } }
            );
            await onRefreshUser(); // Trigger a re-fetch of user data to update UI
            onClose();
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to redeem code.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-[#1e293b] border border-gray-700 w-full max-w-md rounded-2xl p-8 shadow-2xl">
                <h3 className="text-2xl font-bold mb-2">Redeem Access Code</h3>
                <p className="text-gray-400 mb-6 text-sm">Enter your partner or investor code to unlock Enterprise features.</p>
                
                <input 
                    type="text"
                    value={code}
                    onChange={(e) => setCode(e.target.value.toUpperCase())}
                    placeholder="E.G. INVESTOR2025"
                    className="w-full bg-[#0f172a] border border-gray-600 rounded-xl px-4 py-3 mb-4 focus:border-purple-500 outline-none transition-all uppercase font-mono tracking-widest"
                />

                {error && <p className="text-red-400 text-xs mb-4">{error}</p>}

                <div className="flex gap-3">
                    <button 
                        onClick={onClose}
                        className="flex-1 px-4 py-3 rounded-xl border border-gray-600 hover:bg-gray-800 transition-colors"
                    >
                        Cancel
                    </button>
                    <button 
                        onClick={handleRedeem}
                        disabled={loading || !code}
                        className="flex-1 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 px-4 py-3 rounded-xl font-bold transition-all"
                    >
                        {loading ? "Verifying..." : "Redeem Code"}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PromoModal;