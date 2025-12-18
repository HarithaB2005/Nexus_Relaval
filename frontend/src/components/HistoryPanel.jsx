// src/components/HistoryPanel.jsx
import React from 'react';

const HistoryPanel = ({ 
    apiKey, 
    onLogout, 
    docContext, 
    setDocContext, 
    videoUrl, 
    setVideoUrl, 
    maxIterations, 
    setMaxIterations 
}) => {
    return (
        <div className="w-1/4 p-4 bg-gray-900 text-white flex flex-col justify-between overflow-y-auto">
            <div>
                <h3 className="text-2xl font-extrabold mb-4 border-b border-gray-700 pb-2 text-indigo-400">
                    Context Controls
                </h3>
                
                {/* Document Context */}
                <label className="block text-sm font-medium mb-1 mt-3 text-indigo-200">Document Context (Text Input)</label>
                <textarea 
                    rows="4" 
                    value={docContext} 
                    onChange={(e) => setDocContext(e.target.value)}
                    placeholder="Paste document text here (Planner LLM-1 will use this)"
                    className="w-full p-2 text-gray-900 rounded-md text-sm bg-gray-200"
                />

                {/* Video URL */}
                <label className="block text-sm font-medium mb-1 mt-3 text-indigo-200">Video URL (Grounding)</label>
                <input 
                    type="url" 
                    value={videoUrl} 
                    onChange={(e) => setVideoUrl(e.target.value)}
                    placeholder="e.g. YouTube URL (Gemini/Search LLM-0)"
                    className="w-full p-2 text-gray-900 rounded-md text-sm bg-gray-200"
                />
                
                {/* Iterations */}
                <label className="block text-sm font-medium mb-1 mt-3 text-indigo-200">Max Critic Iterations (A2 Loop)</label>
                <input 
                    type="number" 
                    value={maxIterations} 
                    onChange={(e) => setMaxIterations(Math.max(1, Math.min(5, parseInt(e.target.value) || 1)))}
                    min="1" max="5"
                    className="w-full p-2 text-gray-900 rounded-md text-sm bg-gray-200"
                />
            </div>
            
            {/* User Info / Logout */}
            <div className="pt-4 border-t border-gray-700">
                <p className="text-xs font-mono break-all mb-2 text-gray-400">Key: {apiKey ? `${apiKey.substring(0, 15)}...` : 'Not signed in'}</p>
                <button 
                    onClick={onLogout} 
                    className="w-full py-2 bg-red-600 hover:bg-red-700 rounded-md text-white text-sm font-semibold transition duration-150"
                >
                    Logout
                </button>
            </div>
        </div>
    );
};

export default HistoryPanel;