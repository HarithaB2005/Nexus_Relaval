// /frontend/src/pages/NotFoundPage.jsx (NEW FILE)
import React from 'react';
import { useNavigate } from 'react-router-dom';

const NotFoundPage = () => {
    const navigate = useNavigate();

    return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-gray-900 text-gray-800 dark:text-gray-200 p-4">
            <h1 className="text-9xl font-extrabold text-purple-600 dark:text-purple-400">
                404
            </h1>
            <h2 className="text-3xl font-semibold mb-4">
                Page Not Found
            </h2>
            <p className="text-lg text-center mb-8">
                The content you are looking for does not exist or has been moved.
            </p>
            <button 
                onClick={() => navigate('/dashboard')}
                className="px-6 py-3 bg-purple-600 text-white font-medium rounded-lg shadow-md hover:bg-purple-700 transition"
            >
                Go to Dashboard
            </button>
        </div>
    );
};

export default NotFoundPage;