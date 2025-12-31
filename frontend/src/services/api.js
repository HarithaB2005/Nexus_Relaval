// src/services/api.js
import axios from 'axios';

// Use Vite environment for API URL, fallback to localhost
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// --- 1. Registration (JWT flow) ---
export const registerClient = async (name, email, password) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/auth/register`, {
            name,
            email,
            password,
        });
        return response.data; // { access_token, token_type, user }
    } catch (error) {
        throw error.response?.data?.detail || 'Registration failed due to server error.';
    }
};

// --- 2A. Generation for logged-in users (JWT Protected) ---
// Relies on axios default Authorization header set by AuthProvider
export const generateContent = async (requestData) => {
    const payload = {
        messages: requestData.messages,
        document_context: requestData.documentContext || null,
        max_iterations: requestData.maxIterations,
        quality_threshold: requestData.qualityThreshold,
    };

    try {
        const response = await axios.post(`${API_BASE_URL}/generate`, payload, {
            headers: { 'Content-Type': 'application/json' },
        });
        return response.data; // APOResponse
    } catch (error) {
        throw error.response?.data?.detail || error.message || 'Unknown API call error.';
    }
};

// --- 2B. Generation for external clients (API Key Protected) ---
export const generateWithApiKey = async (apiKey, requestData) => {
    if (!apiKey) throw 'API Key is missing';
    const payload = {
        messages: requestData.messages,
        document_context: requestData.documentContext || null,
        max_iterations: requestData.maxIterations,
        quality_threshold: requestData.qualityThreshold,
    };

    try {
        const response = await axios.post(`${API_BASE_URL}/api/v1/generate-prompt`, payload, {
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${apiKey}`,
            },
        });
        return response.data; // APOResponse
    } catch (error) {
        throw error.response?.data?.detail || error.message || 'Unknown API call error.';
    }
};