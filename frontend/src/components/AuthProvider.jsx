// /frontend/src/components/AuthProvider.jsx (NEW FILE)
import React, { createContext, useContext, useState, useMemo, useEffect } from 'react';
import axios from 'axios';

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// 1. Create the Context
const AuthContext = createContext();

// 2. AuthProvider Component
export const AuthProvider = ({ children }) => {
    // Initialize token from localStorage if it exists
    const [token, setToken_] = useState(localStorage.getItem('access_token'));
    const [currentUser, setCurrentUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    // Function to set the token and update localStorage/Axios defaults
    const setToken = (newToken) => {
        setToken_(newToken);
        if (newToken) {
            localStorage.setItem('access_token', newToken);
            axios.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
        } else {
            localStorage.removeItem('access_token');
            delete axios.defaults.headers.common["Authorization"];
            setCurrentUser(null);
        }
    };

    // Effect to fetch user data on token change or initial load
    useEffect(() => {
        const fetchUser = async () => {
            setIsLoading(true);
            if (token) {
                try {
                    // Use the /auth/me endpoint to validate the token and get user data
                    const response = await axios.get(`${API_BASE_URL}/auth/me`);
                    setCurrentUser(response.data);
                } catch (error) {
                    console.error("Token validation failed, logging out:", error);
                    setToken(null); // Invalid token, force logout
                }
            }
            setIsLoading(false);
        };
        fetchUser();
    }, [token]);


    // Context value memoization
    const contextValue = useMemo(
        () => ({
            token,
            currentUser,
            isLoading,
            setToken,
            // Simplified Login and Logout for clarity, actual logic is in LoginPage/DashboardPage
            login: (token) => setToken(token),
            logout: () => setToken(null),
        }),
        [token, currentUser, isLoading]
    );

    // 3. Global Axios Interceptor for 401 Unauthorized errors
    useEffect(() => {
        const interceptor = axios.interceptors.response.use(
            (response) => response,
            (error) => {
                // If response is 401 (Unauthorized) and we have a token, it means the token expired
                if (error.response?.status === 401 && token) {
                    // Clear the token and force user to log in again
                    setToken(null);
                    // You might want to redirect to '/login' here
                }
                return Promise.reject(error);
            }
        );
        return () => axios.interceptors.response.eject(interceptor);
    }, [token]);


    return (
        <AuthContext.Provider value={contextValue}>
            {/* Show a loading state while checking token */}
            {isLoading ? (
                <div className="flex justify-center items-center h-screen text-lg">
                    Loading User Session...
                </div>
            ) : (
                children
            )}
        </AuthContext.Provider>
    );
};

// 4. Custom Hook to use the context
export const useAuth = () => {
    return useContext(AuthContext);
};