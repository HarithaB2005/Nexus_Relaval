import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthProvider';

/**
 * ProtectedRoute Component
 * Uses <Outlet /> to render nested children routes defined in App.jsx
 */
const ProtectedRoute = () => {
    const { token, isLoading } = useAuth();

    // Show a high-end loader while checking session status
    if (isLoading) {
        return (
            <div className="h-screen w-full bg-[#0f172a] flex items-center justify-center">
                <div className="flex flex-col items-center gap-4">
                    <div className="animate-spin h-12 w-12 border-4 border-indigo-500 border-t-transparent rounded-full shadow-lg shadow-indigo-500/20"></div>
                    <p className="text-indigo-400 font-mono text-xs tracking-widest uppercase animate-pulse">
                        Verifying Credentials...
                    </p>
                </div>
            </div>
        );
    }

    // Redirect to login if no valid token is found in AuthContext
    if (!token) {
        return <Navigate to="/login" replace />;
    }

    // Renders the matched child route (DashboardPage, ChatPage, etc.)
    return <Outlet />;
};

export default ProtectedRoute;