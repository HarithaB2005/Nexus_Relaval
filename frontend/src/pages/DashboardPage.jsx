import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../components/AuthProvider';

// Use unified Vite environment variables
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DashboardPage = () => {
    const navigate = useNavigate();
    const { logout, currentUser, token } = useAuth(); // Grab 'token' from context
    const [darkMode, setDarkMode] = useState(localStorage.getItem('theme') === 'dark');
    const [apiKeyValue, setApiKeyValue] = useState(null);
    const [apiKeyError, setApiKeyError] = useState(null);
    const [usageStats, setUsageStats] = useState(null);

    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }, [darkMode]);

    useEffect(() => {
        // Fetch usage stats on mount
        const fetchUsage = async () => {
            try {
                const response = await axios.get(`${API_BASE_URL}/usage/summary`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                setUsageStats(response.data);
            } catch (error) {
                console.error('Failed to fetch usage:', error);
            }
        };
        if (token) fetchUsage();
    }, [token]);

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const handleCreateApiKey = async () => {
        setApiKeyValue(null);
        setApiKeyError(null);
        try {
            // FIX: Include the Authorization header to avoid "API Key missing" errors
            const response = await axios.post(
                `${API_BASE_URL}/client/apikey`, 
                {}, // Empty body
                {
                    headers: {
                        Authorization: `Bearer ${token}`
                    }
                }
            );
            setApiKeyValue(response.data.raw_key); 
        } catch (error) {
            setApiKeyError(error.response?.data?.detail || "Failed to generate key.");
        }
    };

    return (
        <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-gray-900 text-gray-100' : 'bg-gray-100 text-gray-900'}`}>
            <header className="flex justify-between items-center p-4 shadow-md bg-white dark:bg-gray-800">
                <h1 className="text-xl font-bold text-purple-600">APO Dashboard</h1>
                <div className="space-x-4 flex items-center">
                    <span className="text-sm font-medium">Welcome, {currentUser?.client_name || 'User'}!</span>
                    <button onClick={() => setDarkMode(!darkMode)} className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700">
                        {darkMode ? '☀️' : '🌙'}
                    </button>
                    <button onClick={handleLogout} className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition">Logout</button>
                </div>
            </header>

            <main className="container mx-auto p-6">
                <h2 className="text-4xl font-extrabold mb-8">Dashboard</h2>
                
                {/* Usage Stats Card */}
                {currentUser?.usage_limits?.is_vip ? (
                    <div className="bg-gradient-to-r from-purple-600 to-pink-600 p-6 rounded-lg shadow-lg mb-8 text-white">
                        <div className="flex items-center gap-3 mb-2">
                            <span className="text-3xl">👑</span>
                            <h3 className="text-2xl font-bold">VIP Access</h3>
                        </div>
                        <p className="text-lg">Unlimited requests • Priority support • No rate limits</p>
                    </div>
                ) : usageStats ? (
                    <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg mb-8 border border-purple-500/20">
                        <h3 className="text-2xl font-semibold mb-4 text-purple-600">Usage This Month</h3>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                                <div className="text-3xl font-bold text-purple-600">{usageStats.requests_30d || 0}</div>
                                <div className="text-sm text-gray-600 dark:text-gray-300">Requests Made</div>
                                <div className="text-xs text-gray-500 mt-1">Limit: {usageStats.plan_limit || 1000}</div>
                            </div>
                            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                                <div className="text-3xl font-bold text-purple-600">{usageStats.tokens_30d?.toLocaleString() || 0}</div>
                                <div className="text-sm text-gray-600 dark:text-gray-300">Tokens Processed</div>
                            </div>
                            <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                                <div className="text-3xl font-bold text-purple-600">${usageStats.cost_30d || '0.00'}</div>
                                <div className="text-sm text-gray-600 dark:text-gray-300">Estimated Cost</div>
                            </div>
                        </div>
                    </div>
                ) : null}
                
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg mb-8 border border-purple-500/20">
                    <h3 className="text-2xl font-semibold mb-4 text-purple-600">API Integration</h3>
                    <p className="mb-4 text-gray-600 dark:text-gray-300">
                        Generate your API key to integrate Relevo into your applications. 
                        {currentUser?.usage_limits?.is_vip && <span className="text-purple-600 font-semibold"> As a VIP, you have unlimited access.</span>}
                    </p>
                    <button onClick={handleCreateApiKey} className="px-6 py-3 bg-purple-500 text-white rounded-lg hover:bg-purple-600 shadow-lg shadow-purple-500/30 transition-all active:scale-95">
                        Generate New API Key
                    </button>

                    {apiKeyError && <div className="mt-4 p-3 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 rounded-lg border border-red-200 dark:border-red-800">{apiKeyError}</div>}
                    
                    {apiKeyValue && (
                        <div className="relative mt-6 p-6 bg-yellow-50 dark:bg-slate-700 border-2 border-yellow-400 rounded-xl shadow-md animate-in fade-in slide-in-from-top-4">
                            <button 
                                onClick={() => setApiKeyValue(null)}
                                className="absolute top-3 right-3 text-gray-400 hover:text-gray-600 dark:hover:text-white transition"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>

                            <div className="pr-8">
                                <p className="font-bold text-yellow-800 dark:text-yellow-400 mb-1 flex items-center">
                                    <span className="mr-2">⚠️</span> Save Your API Key Now
                                </p>
                                <p className="text-sm text-yellow-700 dark:text-yellow-300 mb-4">
                                    For security, <strong>you will not be able to view this key again</strong> once you close this message.
                                </p>
                                
                                <div className="flex items-center gap-2 mb-4">
                                    <code className="flex-1 block break-all bg-white dark:bg-gray-900 p-4 rounded border border-yellow-200 dark:border-gray-600 font-mono text-purple-600 dark:text-purple-400">
                                        {apiKeyValue}
                                    </code>
                                    <button 
                                        onClick={() => {
                                            navigator.clipboard.writeText(apiKeyValue);
                                            alert("Copied to clipboard!");
                                        }}
                                        className="p-3 bg-white dark:bg-gray-900 border border-yellow-200 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-800 transition"
                                        title="Copy to clipboard"
                                    >
                                        📋
                                    </button>
                                </div>
                                
                                <div className="bg-white dark:bg-gray-900 p-4 rounded border border-yellow-200 dark:border-gray-600">
                                    <p className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-2">Quick Integration Example:</p>
                                    <pre className="text-xs text-gray-600 dark:text-gray-400 overflow-x-auto">
{`curl -X POST https://api.relevo.ai/api/v1/generate-prompt \\
  -H "Authorization: Bearer ${apiKeyValue}" \\
  -H "Content-Type: application/json" \\
  -d '{"messages":[{"role":"user","content":"Your task"}]}'`}
                                    </pre>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <FeatureCard 
                        title="AI Chat" 
                        description="Access the intelligent optimization engine." 
                        onClick={() => navigate('/chat')}
                        icon="💬"
                    />
                    <FeatureCard 
                        title="Usage & Analytics" 
                        description="Monitor your API usage and performance." 
                        onClick={() => navigate('/usage')}
                        icon="📊"
                    />
                    <FeatureCard 
                        title="Billing & Plans" 
                        description="Manage subscription and payment methods." 
                        onClick={() => navigate('/billing')}
                        icon="💳"
                    />
                </div>
            </main>
        </div>
    );
};

const FeatureCard = ({ title, description, onClick, icon }) => (
    <div onClick={onClick} className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border-t-4 border-purple-500 hover:shadow-xl transition cursor-pointer hover:scale-[1.02]">
        <div className="text-4xl mb-3">{icon}</div>
        <h4 className="text-xl font-bold mb-2 text-purple-600">{title}</h4>
        <p className="text-sm text-gray-600 dark:text-gray-300">{description}</p>
    </div>
);

export default DashboardPage;