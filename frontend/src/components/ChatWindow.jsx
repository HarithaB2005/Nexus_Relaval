// src/components/ChatWindow.jsx
import React, { useEffect, useRef, useState } from 'react';

/**
 * Message rendering component
 * Updated with enterprise dark-mode styling and score indicators
 */
const Message = ({ message, onContinueOptimization }) => {
    const isUser = message.role === 'user';
    const isSystem = message.role === 'system';
    const [showPrompt, setShowPrompt] = useState(false);
    const optimizedPrompt = message.debug?.optimized_prompt;
    const optimizedPreview = optimizedPrompt ? (optimizedPrompt.length > 120 ? optimizedPrompt.slice(0, 117) + '...' : optimizedPrompt) : null;
    const metadata = message.metadata;
    const continuationData = message.debug?.continuation_available ? message.debug : null;

    const base = 'p-4 my-3 rounded-2xl max-w-[72%] transition-all';
    const bubbleClass = isUser
        ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white ml-auto rounded-br-none shadow-lg'
        : isSystem
            ? 'bg-yellow-100 dark:bg-yellow-900/30 border border-yellow-300 dark:border-yellow-700 text-yellow-900 dark:text-yellow-100 mr-auto rounded-bl-none'
            : 'bg-slate-800 border border-slate-700 text-slate-100 mr-auto';

    const roleLabel = isUser ? 'You' : isSystem ? 'System' : 'Relevo';

    return (
        <div className={`${base} ${bubbleClass}`}>
            <div className="flex items-start gap-3">
                <div className="flex-shrink-0">
                    <div className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold ${isUser ? 'bg-indigo-700' : isSystem ? 'bg-rose-600' : 'bg-slate-700'}`}>
                        {roleLabel[0]}
                    </div>
                </div>
                <div className="min-w-0">
                    <div className="flex items-baseline justify-between gap-4">
                        <div className="flex items-center gap-3">
                            <div className="text-[11px] font-semibold tracking-wider opacity-90">{roleLabel}</div>
                            {/* Inline optimized-prompt preview next to assistant label */}
                            {optimizedPreview && !isUser && (
                                <button
                                    onClick={() => setShowPrompt(s => !s)}
                                    title={optimizedPrompt}
                                    className="text-xs text-indigo-300 font-mono bg-slate-800/60 px-2 py-1 rounded-md hover:opacity-90 truncate max-w-[40ch]"
                                >
                                    {optimizedPreview}
                                </button>
                            )}
                        </div>
                        {message.timestamp && <div className="text-[11px] text-slate-400">{message.timestamp}</div>}
                    </div>

                    <div className="mt-2 whitespace-pre-wrap leading-relaxed text-sm text-slate-100 break-words max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-slate-600">
                        {message.content}
                    </div>

                    {/* New simple metadata display */}
                    {metadata && (
                        <div className="mt-3 pt-2 border-t border-slate-700/40 flex gap-3 text-xs text-slate-400">
                            <span>✓ Quality: {(metadata.quality * 100).toFixed(0)}%</span>
                            <span>⚡ {metadata.executionTime}s</span>
                            <span>🔄 {metadata.iterations} iterations</span>
                        </div>
                    )}

                    {/* Continuation offer */}
                    {continuationData && (
                        <div className="mt-3 p-3 bg-yellow-900/20 border border-yellow-600/40 rounded-lg">
                            <div className="flex items-start gap-3">
                                <div className="text-yellow-500 text-xl">⚠️</div>
                                <div className="flex-1">
                                    <div className="text-sm font-semibold text-yellow-200 mb-1">Quality Below Threshold</div>
                                    <div className="text-xs text-slate-300 mb-3">{continuationData.continuation_message}</div>
                                    <button
                                        onClick={() => onContinueOptimization && onContinueOptimization(continuationData)}
                                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
                                    >
                                        🔄 Continue Optimizing
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}

                    {message.debug && (
                        <div className="mt-3 pt-3 border-t border-slate-700/40 flex flex-col gap-3 text-xs text-slate-300">
                            <div className="flex flex-wrap gap-4">
                                <div className="flex items-center gap-1.5">
                                    <span className="text-green-400 text-xs">●</span>
                                    <div className="font-mono">SCORE: <span className="font-bold text-white">{message.debug.critic_score}</span></div>
                                </div>
                                <div className="flex items-center gap-1.5">
                                    <span className="text-purple-400 text-xs">●</span>
                                    <div className="font-mono">ROLE: <span className="font-bold text-white">{message.debug.role_selected}</span></div>
                                </div>
                            </div>

                            {/* Optimized Prompt (if available) */}
                            {message.debug.optimized_prompt && (
                                <div className="mt-1">
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="text-[12px] font-semibold text-slate-300">Optimized Prompt</div>
                                        <div className="flex items-center gap-2">
                                            <button onClick={() => { navigator.clipboard?.writeText(message.debug.optimized_prompt); }} className="text-xs px-2 py-1 bg-slate-700 rounded-md hover:opacity-90">Copy</button>
                                            <button onClick={() => setShowPrompt(s => !s)} className="text-xs px-2 py-1 bg-slate-700 rounded-md hover:opacity-90">{showPrompt ? 'Hide' : 'Show'}</button>
                                        </div>
                                    </div>

                                    {showPrompt && (
                                        <pre className="mt-2 p-3 rounded-md bg-slate-800 border border-slate-700 text-sm font-mono text-slate-200 whitespace-pre-wrap">{message.debug.optimized_prompt}</pre>
                                    )}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

const ChatWindow = ({ history, isLoading, onContinueOptimization }) => {
    const messagesEndRef = useRef(null);

    // Auto-scroll logic for real-time orchestration updates
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history, isLoading]);

    return (
        <main className="flex-1 overflow-y-auto p-6 space-y-2 scrollbar-thin scrollbar-thumb-gray-700">
            {history.length === 0 && (
                <div className="h-full flex flex-col items-center justify-center opacity-20 select-none">
                    <div className="text-6xl mb-4">⚡</div>
                    <p className="text-xl font-bold tracking-widest uppercase">Relevo Engine Ready</p>
                </div>
            )}

            {history.map((msg, index) => (
                <Message key={index} message={msg} onContinueOptimization={onContinueOptimization} />
            ))}
            
            {/* Orchestration Loading State */}
            {isLoading && (
                <div className="mr-auto p-4 bg-[#1e293b]/50 border border-indigo-500/30 rounded-2xl max-w-[72%] animate-pulse">
                    <div className="flex items-center space-x-3 text-indigo-400">
                        <div className="relative flex h-3 w-3">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                            <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
                        </div>
                        <span className="text-xs font-bold uppercase tracking-tighter">
                            Orchestrating 4-Agent Workflow (LLM-0 to LLM-3)...
                        </span>
                    </div>
                </div>
            )}
            
            <div ref={messagesEndRef} className="h-4" />
        </main>
    );
};

export default ChatWindow;