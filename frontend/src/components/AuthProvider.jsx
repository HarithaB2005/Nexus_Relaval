// /frontend/src/components/AuthProvider.jsx
import React, { createContext, useContext, useState, useMemo, useEffect, useCallback } from 'react';
import axios from 'axios';

// Corrected for browser compatibility: Vite/Modern ESM uses import.meta.env
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Ensure all axios calls (including relative ones in components) target the API
axios.defaults.baseURL = API_BASE_URL;

// 1. Create the Context
const AuthContext = createContext();

// 2. AuthProvider Component
export const AuthProvider = ({ children }) => {
    // Initialize token from localStorage if it exists
    const [token, setToken_] = useState(localStorage.getItem('access_token'));
    const [currentUser, setCurrentUser] = useState(null);
    const [isLoading, setIsLoading] = useState(true);

    // Function to set the token and update localStorage/Axios defaults
    const setToken = useCallback((newToken) => {
        setToken_(newToken);
        if (newToken) {
            localStorage.setItem('access_token', newToken);
            axios.defaults.headers.common["Authorization"] = `Bearer ${newToken}`;
        } else {
            localStorage.removeItem('access_token');
            delete axios.defaults.headers.common["Authorization"];
            setCurrentUser(null);
        }
    }, []);

    // 3. refreshUser Function: Critical for Pitch Redemptions
    // Re-fetches user data from /auth/me to update global state (usage, VIP status, etc.)
    const refreshUser = useCallback(async () => {
        if (!token) return;
        try {
            const response = await axios.get(`${API_BASE_URL}/auth/me`);
            setCurrentUser(response.data);
            return response.data;
        } catch (error) {
            console.error("Failed to refresh user session:", error);
            if (error.response?.status === 401) {
                setToken(null);
            }
        }
    }, [token, setToken]);

    // Effect to fetch user data on token change or initial load
    useEffect(() => {
        const initAuth = async () => {
            setIsLoading(true);
            if (token) {
                // Set default header immediately if token exists in localStorage
                axios.defaults.headers.common["Authorization"] = `Bearer ${token}`;
                await refreshUser();
            }
            setIsLoading(false);
        };
        initAuth();
    }, [token, refreshUser]);

    // Context value memoization
    const contextValue = useMemo(
        () => ({
            token,
            currentUser,
            isLoading,
            setToken,
            refreshUser, // Exposed so PromoModal can call it
            login: (newToken, userData) => {
                setToken(newToken);
                if (userData) setCurrentUser(userData);
            },
            logout: () => setToken(null),
        }),
        [token, currentUser, isLoading, setToken, refreshUser]
    );

    // 4. Global Axios Interceptor for 401 Unauthorized errors
    useEffect(() => {
        const interceptor = axios.interceptors.response.use(
            (response) => response,
            (error) => {
                // If the backend returns 401, clear the token and trigger logout
                if (error.response?.status === 401 && token) {
                    setToken(null);
                }
                return Promise.reject(error);
            }
        );
        return () => axios.interceptors.response.eject(interceptor);
    }, [token, setToken]);

    return (
        <AuthContext.Provider value={contextValue}>
            {isLoading ? (
                <div className="flex flex-col justify-center items-center h-screen bg-[#0f172a] text-white">
                    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-500 mb-4"></div>
                    <div className="text-lg font-medium">Validating Session...</div>
                </div>
            ) : (
                children
            )}
        </AuthContext.Provider>
    );
};

// 5. Custom Hook to use the context
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};