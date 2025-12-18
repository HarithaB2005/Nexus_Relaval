// src/components/TextInput.jsx
import React from 'react';

const TextInput = ({ input, setInput, handleSend, isLoading, error }) => {
    return (
        <footer className="p-4 border-t bg-white">
            {/* Error Display */}
            {error && (
                <div className="p-2 mb-2 text-sm bg-red-100 text-red-700 rounded-md">
                    API Error: {error}
                </div>
            )}
            <div className="flex space-x-3">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    // Handle Enter key to send message
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    className="flex-1 p-3 border border-gray-300 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 shadow-sm"
                    placeholder="Enter your task for optimization..."
                    disabled={isLoading}
                />
                <button
                    onClick={handleSend}
                    className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:bg-indigo-400 transition duration-150"
                    disabled={isLoading}
                >
                    Send
                </button>
            </div>
        </footer>
    );
};

export default TextInput;