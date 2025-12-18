// /frontend/src/pages/RegisterPage.jsx (UPDATED)
import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../components/AuthProvider'; // Import useAuth

const API_BASE_URL = 'http://localhost:8000';

const RegisterPage = () => {
    const [formData, setFormData] = useState({ name: '', email: '', password: '' });
    const [error, setError] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();
    const { setToken } = useAuth(); // Use setToken from context

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setIsLoading(true);

        try {
            const response = await axios.post(`${API_BASE_URL}/auth/register`, formData);
            
            // Registration successful, set token via context and redirect
            setToken(response.data.access_token);
            navigate('/dashboard');

        } catch (err) {
            console.error("Registration Error:", err.response ? err.response.data : err.message);
            setError(err.response?.data?.detail || 'Registration failed. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
            <div className="bg-white p-8 rounded-xl shadow-2xl w-full max-w-md">
                <h1 className="text-3xl font-bold text-purple-700 mb-6">Create Account</h1>
                
                <form onSubmit={handleSubmit} className="space-y-4">
                    <input type="text" name="name" placeholder="Full Name" onChange={handleChange} required className="w-full p-3 border border-gray-300 rounded-lg" />
                    <input type="email" name="email" placeholder="Email Address" onChange={handleChange} required className="w-full p-3 border border-gray-300 rounded-lg" />
                    <input type="password" name="password" placeholder="Password" onChange={handleChange} required className="w-full p-3 border border-gray-300 rounded-lg" />
                    
                    {error && <p className="text-red-500 text-sm bg-red-100 p-2 rounded">{error}</p>}
                    
                    <button type="submit" disabled={isLoading} className="w-full py-3 bg-purple-600 text-white font-semibold rounded-lg hover:bg-purple-700 disabled:bg-purple-400">
                        {isLoading ? 'Registering...' : 'Register and Sign In'}
                    </button>
                </form>
                
                <div className="mt-6 text-center text-sm">
                    <p className="text-gray-600">
                        Already have an account?{' '}
                        <button onClick={() => navigate('/login')} className="text-purple-600 font-medium hover:text-purple-700">
                            Login Here
                        </button>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default RegisterPage;