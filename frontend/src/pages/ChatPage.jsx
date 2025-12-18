// src/pages/ChatPage.jsx (Updated to use components)
import React, { useState } from 'react';
import { generateContent } from '../services/api';
import ChatWindow from '../components/ChatWindow';
import HistoryPanel from '../components/HistoryPanel';
import TextInput from '../components/TextInput';

const ChatPage = ({ apiKey, onLogout }) => {
    const [history, setHistory] = useState([
        { role: 'assistant', content: "Welcome to the APO Service. Enter your task and any relevant context on the left." }
    ]);
    const [input, setInput] = useState('');
    
    // State for optional context data
    const [docContext, setDocContext] = useState('');
    const [videoUrl, setVideoUrl] = useState('');
    const [maxIterations, setMaxIterations] = useState(3);

    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSend = async () => {
        if (!input.trim() || isLoading) return;

        // 1. Update history with user's message
        const userMessage = { role: 'user', content: input };
        const newHistory = [...history, userMessage];
        setHistory(newHistory);
        setInput('');
        setIsLoading(true);
        setError(null);

        // 2. Prepare request data (Matches APORequest schema)
        const requestData = {
            messages: newHistory.map(msg => ({ role: msg.role, content: msg.content })),
            documentContext: docContext.trim() || null, 
            videoUrl: videoUrl.trim() || null,
            maxIterations: maxIterations,
            qualityThreshold: 0.97,
        };

        try {
            // 3. Call the authenticated API
            const result = await generateContent(apiKey, requestData); 
            
            // 4. Update history with the final, optimized output
            setHistory(prev => [
                ...prev,
                { role: 'assistant', content: result.final_output, debug: result } 
            ]);
            
        } catch (err) {
            // Update local error state and add system message to history
            setError(err);
            setHistory(prev => [...prev, { role: 'system', content: `API Error: ${err}.` }]);
        } finally {
            setIsLoading(false);
        }
    };
    

    return (
        <div className="flex h-screen bg-gray-50">
            {/* 1. History/Context Panel (Component) */}
            <HistoryPanel 
                apiKey={apiKey}
                onLogout={onLogout}
                docContext={docContext}
                setDocContext={setDocContext}
                videoUrl={videoUrl}
                setVideoUrl={setVideoUrl}
                maxIterations={maxIterations}
                setMaxIterations={setMaxIterations}
            />
            
            {/* 2. Main Chat Area */}
            <div className="flex-1 flex flex-col">
                <header className="p-4 border-b bg-white shadow-md">
                    <h1 className="text-2xl font-bold text-gray-800">Agent-Optimized Interface</h1>
                </header>
                
                {/* 3. Chat Window (Component) */}
                <ChatWindow 
                    history={history} 
                    isLoading={isLoading} 
                />

                {/* 4. Input Bar (Component) */}
                <TextInput
                    input={input}
                    setInput={setInput}
                    handleSend={handleSend}
                    isLoading={isLoading}
                    error={error}
                />
            </div>
        </div>
    );
};

export default ChatPage;