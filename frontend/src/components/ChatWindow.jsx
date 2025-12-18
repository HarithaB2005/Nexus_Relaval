// src/components/ChatWindow.jsx
import React, { useEffect, useRef } from 'react';

// Message rendering component
const Message = ({ message }) => {
    // Determine message alignment and styling
    const isUser = message.role === 'user';
    
    return (
        <div className={`p-3 my-2 rounded-lg max-w-[85%] ${isUser ? 'bg-indigo-100 ml-auto' : 'bg-white shadow-lg mr-auto border border-gray-200'}`}>
            <p className={`font-semibold capitalize text-sm mb-1 ${isUser ? 'text-indigo-800' : 'text-gray-800'}`}>
                {message.role}
            </p>
            <div className="whitespace-pre-wrap">{message.content}</div>
            {/* Display debug/APO score information if available */}
            {message.debug && (
                <div className="mt-2 pt-2 border-t border-gray-200 text-left">
                    <p className="text-xs text-gray-600 font-medium">✅ APO Score: {message.debug.critic_score}</p>
                    <p className="text-xs text-gray-600 italic">🛠️ Role: {message.debug.role_selected}</p>
                </div>
            )}
        </div>
    );
};

const ChatWindow = ({ history, isLoading }) => {
    const messagesEndRef = useRef(null);

    useEffect(() => {
        // Auto-scroll to bottom on new message
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history]);

    return (
        <main className="flex-1 overflow-y-auto p-6 space-y-4">
            {history.map((msg, index) => <Message key={index} message={msg} />)}
            
            {/* Loading Indicator */}
            {isLoading && (
                <div className="text-left text-indigo-500 flex items-center space-x-2 p-3 bg-gray-100 rounded-lg max-w-[85%]">
                     <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-indigo-500"></div>
                     <span>Orchestrating 4-Agent Workflow (LLM-0 to LLM-3)...</span>
                </div>
            )}
            
            <div ref={messagesEndRef} />
        </main>
    );
};

export default ChatWindow;