// /frontend/src/pages/DashboardPage.jsx (UPDATED)
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../components/AuthProvider'; // Import useAuth

const API_BASE_URL = 'http://localhost:8000';

// NOTE: The global Axios interceptor is now handled within AuthProvider.jsx

const DashboardPage = () => {
    const navigate = useNavigate();
    const { logout, currentUser } = useAuth(); // Use logout and currentUser from context
    const [darkMode, setDarkMode] = useState(
        localStorage.getItem('theme') === 'dark'
    );
    const [apiKeyValue, setApiKeyValue] = useState(null);
    const [apiKeyError, setApiKeyError] = useState(null);

    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark');
            localStorage.setItem('theme', 'dark');
        } else {
            document.documentElement.classList.remove('dark');
            localStorage.setItem('theme', 'light');
        }
    }, [darkMode]);

    const handleLogout = () => {
        logout(); // Logout via context
        navigate('/login');
    };

    const handleCreateApiKey = async () => {
        setApiKeyValue(null);
        setApiKeyError(null);
        try {
            // Call the protected endpoint to generate a new key. Axios includes JWT automatically.
            const response = await axios.post(`${API_BASE_URL}/client/apikey`);
            setApiKeyValue(response.data.api_key);
        } catch (error) {
            console.error("API Key Generation Failed:", error);
            // The AuthProvider interceptor will handle 401 and log out automatically
            setApiKeyError(error.response?.data?.detail || "Failed to generate key. Session expired or internal error.");
        }
    };

    const toggleDarkMode = () => setDarkMode(!darkMode);

    return (
        <div className={`min-h-screen transition-colors duration-300 ${darkMode ? 'bg-gray-900 text-gray-100' : 'bg-gray-100 text-gray-900'}`}>
            {/* --- Header/Nav --- */}
            <header className="flex justify-between items-center p-4 shadow-md bg-white dark:bg-gray-800">
                <h1 className="text-xl font-bold text-purple-600">APO Dashboard</h1>
                <div className="space-x-4 flex items-center">
                    <span className="text-sm font-medium hidden sm:block">
                        Welcome, {currentUser?.client_name || 'User'}!
                    </span>
                    <button onClick={toggleDarkMode} className="p-2 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition text-gray-600 dark:text-gray-300">
                        {darkMode ? '☀️ Light Mode' : '🌙 Dark Mode'}
                    </button>
                    <button onClick={handleLogout} className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition">
                        Logout
                    </button>
                </div>
            </header>

            {/* --- Main Content --- */}
            <main className="container mx-auto p-6">
                <h2 className="text-4xl font-extrabold mb-8">
                    Dashboard for {currentUser?.client_name || 'Your Account'}
                </h2>
                
                <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-lg mb-8">
                    <h3 className="text-2xl font-semibold mb-4 text-purple-600">API Key Management</h3>
                    <p className="mb-4 text-gray-600 dark:text-gray-300">
                        Generate your client-side API key to access endpoints outside the web app.
                    </p>
                    
                    <button 
                        onClick={handleCreateApiKey} 
                        className="px-6 py-3 bg-purple-500 text-white rounded-lg font-medium hover:bg-purple-600 transition"
                    >
                        Create New API Key
                    </button>

                    {apiKeyError && (
                        <div className="mt-4 p-3 bg-red-100 text-red-700 rounded-lg text-sm">
                            Error: {apiKeyError}
                        </div>
                    )}

                    {apiKeyValue && (
                        <div className="mt-6 p-4 bg-yellow-50 dark:bg-gray-700 border border-yellow-300 rounded-lg text-sm">
                            <p className="font-semibold mb-2 text-yellow-800 dark:text-yellow-200">
                                Your New API Key:
                            </p>
                            <code className="block break-all bg-white dark:bg-gray-800 p-3 rounded shadow-inner">{apiKeyValue}</code>
                            <p className="mt-2 text-red-600 dark:text-red-300">
                                **WARNING: Save this key immediately. It will not be shown again.**
                            </p>
                        </div>
                    )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    <FeatureCard title="Prompt Generator" description="Access the core Agent-based Prompt Optimization service." onClick={() => navigate('/chat')} />
                    <FeatureCard title="Usage Analytics" description="View your historical prompt usage and cost reports." />
                    <FeatureCard title="Billing & Plans" description="Manage your subscription and update payment details." />
                </div>
            </main>
        </div>
    );
};

const FeatureCard = ({ title, description, onClick }) => (
    <div 
        onClick={onClick}
        className={`bg-white dark:bg-gray-800 p-6 rounded-lg shadow-md border-t-4 border-purple-500 hover:shadow-xl transition duration-300 cursor-pointer ${onClick ? 'hover:scale-[1.02]' : ''}`}
    >
        <h4 className="text-xl font-bold mb-2 text-purple-600">{title}</h4>
        <p className="text-sm text-gray-600 dark:text-gray-300">{description}</p>
    </div>
);

export default DashboardPage;