// src/services/api.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Target your FastAPI server

// --- 1. Registration (Unauthenticated) ---
export const registerClient = async (name, email) => {
    try {
        const response = await axios.post(`${API_BASE_URL}/register`, {
            client_name: name,
            client_email: email,
        });
        return response.data; // Should contain { client_id, api_key, message }
    } catch (error) {
        throw error.response?.data?.detail || "Registration failed due to server error.";
    }
};

// --- 2. Generation (Authenticated) ---
export const generateContent = async (apiKey, requestData) => {
    if (!apiKey) {
        throw "API Key is missing. Please sign in or register.";
    }
    
    // The requestData must strictly match the APORequest Pydantic model
    const payload = {
        messages: requestData.messages,
        document_context: requestData.documentContext || null, 
        video_url: requestData.videoUrl || null,             
        max_iterations: requestData.maxIterations,
        quality_threshold: requestData.qualityThreshold,
    };

    try {
        const response = await axios.post(`${API_BASE_URL}/generate`, payload, {
            headers: {
                'Content-Type': 'application/json',
                'X-APO-Key': apiKey, 
            },
        });
        return response.data; // Returns APOResponse schema
    } catch (error) {
        // Return detailed backend error messages (401 Unauthorized, 429 Rate Limit)
        throw error.response?.data?.detail || error.message || "Unknown API call error.";
    }
};