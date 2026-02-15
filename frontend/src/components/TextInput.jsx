// src/components/TextInput.jsx
import React from 'react';

const TextInput = ({ input, setInput, handleSend, isLoading, error, inputRef, placeholder, className = '' }) => {
    return (
        <footer className={`p-4 border-t border-slate-700 bg-slate-900/60 relative z-30 shadow-inner ${className}`}>
            {error && (
                <div className="p-2 mb-3 text-sm bg-red-900/60 text-red-200 rounded-md border border-red-700">
                    API Error: {error}
                </div>
            )}

            <div className="flex items-center gap-3 max-w-4xl mx-auto">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                    ref={inputRef}
                    className="flex-1 p-3 bg-slate-800 border border-slate-700 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-400 text-slate-100 placeholder-slate-400 transition"
                    placeholder={placeholder || "Describe the objective, e.g. 'Optimize my product description for conversion'"}
                    disabled={isLoading}
                />

                <button
                    onClick={handleSend}
                    className="flex items-center gap-2 bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-5 py-2 rounded-xl font-semibold hover:opacity-95 disabled:opacity-50 transition"
                    disabled={isLoading}
                    aria-label="Send message"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                    </svg>
                    <span className="text-sm">Send</span>
                </button>
            </div>
        </footer>
    );
};

export default TextInput;