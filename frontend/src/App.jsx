// /frontend/src/App.jsx (UPDATED)
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage'; // Assuming this is your main app page
import NotFoundPage from './pages/NotFoundPage'; // Good practice for 404
import { AuthProvider } from './components/AuthProvider';
import ProtectedRoute from './components/ProtectedRoute'; // Import the new component

function App() {
    return (
        <Router>
            {/* Wrap the entire application in the AuthProvider */}
            <AuthProvider>
                <Routes>
                    {/* Public Routes */}
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    
                    {/* Protected Routes: Only accessible if authenticated */}
                    <Route element={<ProtectedRoute />}>
                        <Route path="/" element={<DashboardPage />} /> {/* Redirect '/' to dashboard */}
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/chat" element={<ChatPage />} />
                        {/* Add more protected routes here */}
                    </Route>

                    {/* Fallback route */}
                    <Route path="*" element={<NotFoundPage />} />
                </Routes>
            </AuthProvider>
        </Router>
    );
}

export default App;