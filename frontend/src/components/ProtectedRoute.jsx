// /frontend/src/components/ProtectedRoute.jsx (NEW FILE)
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from './AuthProvider';

const ProtectedRoute = () => {
    // Check if the user is authenticated (token is available)
    const { token, isLoading } = useAuth();
    
    // While loading, return null or a loading indicator
    if (isLoading) {
        return null; // The AuthProvider handles the full screen loading state
    }

    // If authenticated, render the child routes/components
    if (token) {
        return <Outlet />;
    }

    // If not authenticated, redirect to the login page
    return <Navigate to="/login" replace />;
};

export default ProtectedRoute;