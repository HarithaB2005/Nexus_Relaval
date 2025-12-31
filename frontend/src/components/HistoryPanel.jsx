// src/components/HistoryPanel.jsx
import React, { useState } from 'react';
import axios from 'axios';
import { useAuth } from './AuthProvider';

const HistoryPanel = ({ 
    apiKey, 
    onLogout, 
    docContext, 
    setDocContext, 
    maxIterations, 
    setMaxIterations 
}) => {
    const { token } = useAuth();
    const [pdfUploading, setPdfUploading] = useState(false);
    const [uploadError, setUploadError] = useState(null);

    const handlePdfUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setPdfUploading(true);
        setUploadError(null);

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await axios.post('/upload/pdf', formData, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'multipart/form-data'
                }
            });

            // Auto-populate document context with extracted text
            setDocContext(response.data.extracted_text);
        } catch (err) {
            setUploadError(err.response?.data?.detail || 'PDF upload failed');
        } finally {
            setPdfUploading(false);
            e.target.value = ''; // Reset input
        }
    };

    return (
        <div className="w-full p-5 text-white flex flex-col justify-between h-full">
            <div>
                <h3 className="text-2xl font-extrabold mb-4 border-b border-slate-800 pb-3 text-indigo-300">
                    Context Controls
                </h3>
                
                {/* Upload Error Display */}
                {uploadError && (
                    <div className="mb-3 p-3 bg-red-900/30 border border-red-600/40 rounded-lg text-xs text-red-200">
                        ❌ {uploadError}
                    </div>
                )}

                {/* Document Context */}
                <label className="block text-sm font-medium mb-2 mt-3 text-slate-300">Document Context (Text Input)</label>
                <textarea 
                    rows="5" 
                    value={docContext} 
                    onChange={(e) => setDocContext(e.target.value)}
                    placeholder="Paste document text here (Planner LLM-1 will use this)"
                    className="w-full p-3 text-slate-100 rounded-lg text-sm bg-slate-800 border border-slate-700 resize-none"
                />
                
                {/* PDF Upload Button */}
                <div className="mt-2">
                    <label className="cursor-pointer inline-flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg transition-colors">
                        {pdfUploading ? (
                            <>
                                <span className="animate-spin">⏳</span>
                                Uploading PDF...
                            </>
                        ) : (
                            <>
                                📄 Upload PDF
                                <input
                                    type="file"
                                    accept=".pdf,application/pdf"
                                    onChange={handlePdfUpload}
                                    className="hidden"
                                />
                            </>
                        )}
                    </label>
                    <span className="ml-2 text-xs text-slate-400">(Max 10MB)</span>
                </div>
                
                {/* Iterations */}
                <label className="block text-sm font-medium mb-2 mt-4 text-slate-300">Max Critic Iterations (A2 Loop)</label>
                <input 
                    type="number" 
                    value={maxIterations} 
                    onChange={(e) => setMaxIterations(Math.max(1, Math.min(5, parseInt(e.target.value) || 1)))}
                    min="1" max="5"
                    className="w-full p-3 text-slate-100 rounded-lg text-sm bg-slate-800 border border-slate-700"
                />
            </div>
            
            {/* User Info / Logout */}
            <div className="pt-4 border-t border-slate-800">
                <p className="text-xs font-mono break-all mb-3 text-slate-400">Key: {apiKey ? `${apiKey.substring(0, 15)}...` : 'Not signed in'}</p>
                <button 
                    onClick={onLogout} 
                    className="w-full py-2 bg-red-600 hover:bg-red-700 rounded-lg text-white text-sm font-semibold transition duration-150"
                >
                    Logout
                </button>
            </div>
        </div>
    );
};

export default HistoryPanel;