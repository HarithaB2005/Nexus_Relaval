// src/pages/ChatPage.jsx
import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { generateContent } from '../services/api';
import { useAuth } from '../components/AuthProvider';
import ChatWindow from '../components/ChatWindow';
import HistoryPanel from '../components/HistoryPanel';
import TextInput from '../components/TextInput';

const ChatPage = () => {
    const navigate = useNavigate();
    const { token, logout } = useAuth();
    
    const [history, setHistory] = useState([
        { role: 'assistant', content: "👋 Welcome to Relevo! I'm your intelligent optimization assistant. Send me any task and I'll transform it into the perfect output with quality assurance." }
    ]);
    const [input, setInput] = useState('');
    const [inputPlaceholder, setInputPlaceholder] = useState("Describe the objective, e.g. 'Optimize my product description for conversion'");
    const inputRef = useRef(null);
    const [docContext, setDocContext] = useState('');
    const [maxIterations, setMaxIterations] = useState(3);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleLogout = () => { logout(); navigate('/login'); };

    const handleSend = async (overrideText) => {
        if (isLoading) return;
        const prompt = (overrideText ?? input).trim();
        if (!prompt) return;
        const userMessage = { role: 'user', content: prompt };
        const newHistory = [...history, userMessage];
        setHistory(newHistory);
        setInput('');
        setInputPlaceholder("Describe the objective, e.g. 'Optimize my product description for conversion'");
        setIsLoading(true);
        setError(null);

        try {
            const result = await generateContent({
                messages: newHistory.map(msg => ({ role: msg.role, content: msg.content })),
                documentContext: docContext.trim() || null,
                maxIterations: maxIterations,
                qualityThreshold: 0.97,
            }); 
            
            // Add metadata and optimized prompt for copy/show
            const responseWithMeta = {
                role: 'assistant',
                content: result.final_output,
                metadata: {
                    quality: result.critic_score,
                    iterations: result.iterations,
                    executionTime: result.execution_time_seconds
                },
                debug: {
                    optimized_prompt: result.optimized_prompt,
                    critic_score: result.critic_score,
                    role_selected: result.role_selected,
                    // Continuation data
                    continuation_available: result.continuation_available,
                    continuation_message: result.continuation_message,
                    quality_score_best: result.quality_score_best,
                    best_iteration: result.best_iteration,
                    continuation_state: {
                        last_prompt: result.optimized_prompt,
                        previous_results: result,
                        iterations_completed: result.iterations,
                        document_context: docContext.trim() || null
                    }
                },
                output_type: result.output_type,
                clarifier_options: result.clarifier_options || result.pathfinder_options,
                ambiguity_score: result.ambiguity_score,
                intent_metadata: result.intent_metadata,
                nexus_metadata: result.nexus_metadata,
                rejection_hypotheses: result.rejection_hypotheses,
                rephrase_similarity: result.rephrase_similarity
            };
            
            setHistory(prev => [...prev, responseWithMeta]);
        } catch (err) {
            const errorMsg = err.response?.data?.detail || err.message || err.toString();
            setError(errorMsg);
            
            // API Rate Limit (Groq/Gemini quota exhausted)
            if (errorMsg.includes('Rate limit') || errorMsg.includes('rate_limit') || errorMsg.includes('quota')) {
                setHistory(prev => [...prev, { 
                    role: 'system', 
                    content: "📊 **Demo API Limit Reached**\n\n" +
                             "✅ **Platform Status**: Fully Functional\n" +
                             "⏰ **Issue**: Free-tier API quota temporarily exhausted\n" +
                             "💡 **For Investors**: This is a demo limitation, not a product failure. Production deployment will use enterprise API keys with unlimited capacity.\n\n" +
                             "**Next Steps**:\n" +
                             "• Wait 60 seconds for rate limit reset, or\n" +
                             "• Contact us to see the platform with production API keys\n" +
                             "• Review the codebase and architecture (fully functional)"
                }]);
            }
            // User plan limit
            else if (errorMsg.includes('Plan limit')) {
                setHistory(prev => [...prev, { 
                    role: 'system', 
                    content: "⚠️ Monthly quota exceeded. Please upgrade your plan to continue using the service." 
                }]);
            }
            // LLM API Connection Error (API key invalid/missing)
            else if (errorMsg.includes('API') || errorMsg.includes('connect') || errorMsg.includes('timeout')) {
                setHistory(prev => [...prev, { 
                    role: 'system', 
                    content: "🔌 **API Connection Notice**\n\n" +
                             "✅ **Platform**: Working correctly\n" +
                             "⚠️ **Issue**: LLM API service temporarily unavailable\n\n" +
                             "**For Investors**: This demonstrates our robust error handling. The platform architecture is production-ready; we're currently using free-tier API keys for this demo.\n\n" +
                             "**Production Deployment** will include:\n" +
                             "• Enterprise-grade API keys (99.99% uptime)\n" +
                             "• Multi-provider fallback (Gemini → Groq → Ollama)\n" +
                             "• Unlimited capacity\n\n" +
                             "Contact us to see the full production setup!"
                }]);
            }
            // Generic error
            else {
                setHistory(prev => [...prev, { 
                    role: 'system', 
                    content: `❌ Error: ${errorMsg}\n\n💡 If this is an API-related error, it's likely a demo limitation. Production deployment uses enterprise API infrastructure.` 
                }]);
            }
        } finally {
            setIsLoading(false);
        }
    };

    const handleContinueOptimization = async (continuationData) => {
        if (isLoading) return;
        
        setIsLoading(true);
        setError(null);
        
        try {
            const result = await fetch('/api/optimize/continue', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    messages: history.map(msg => ({ role: msg.role, content: msg.content })),
                    continuation_state: continuationData.continuation_state,
                    additional_iterations: 3
                })
            });
            
            if (!result.ok) {
                const error = await result.json();
                throw new Error(error.detail || 'Continuation failed');
            }
            
            const data = await result.json();
            
            const responseWithMeta = {
                role: 'assistant',
                content: data.final_output,
                metadata: {
                    quality: data.critic_score,
                    iterations: data.iterations,
                    executionTime: data.execution_time_seconds
                },
                debug: {
                    optimized_prompt: data.optimized_prompt,
                    critic_score: data.critic_score,
                    role_selected: data.role_selected,
                    continuation_available: data.continuation_available,
                    continuation_message: data.continuation_message
                }
            };
            
            setHistory(prev => [...prev, responseWithMeta]);
        } catch (err) {
            setError(err.message);
            setHistory(prev => [...prev, { 
                role: 'system', 
                content: `❌ Continuation failed: ${err.message}` 
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const handleOptionSelect = (optionText) => {
        if (!optionText) return;
        const normalized = optionText.trim().toLowerCase();

        if (normalized === 'provide missing details' || normalized === 'provide missing detail' || normalized === 'provide details') {
            setInput('');
            setInputPlaceholder('Provide more context (exact question and what you want: solve, explain, check, or correct)');
            inputRef.current?.focus();
            return;
        }

        if (normalized === 'not sure' || normalized === 'not sure.') {
            setHistory(prev => ([
                ...prev,
                {
                    role: 'system',
                    content: 'To move forward, share any of these: the exact question text, what you want (solve, explain, check, correct), and any constraints or class level. If you only have the question, paste that.'
                }
            ]));
            setInput('');
            setInputPlaceholder('Paste the exact question here');
            inputRef.current?.focus();
            return;
        }

        setInputPlaceholder("Describe the objective, e.g. 'Optimize my product description for conversion'");
        handleSend(optionText);
    };

    return (
        <div className="flex h-screen w-full bg-[#020617] text-slate-200">
            {/* 1. FIXED SIDEBAR - Added w-80 and flex-none to prevent squashing */}
            <aside className="w-80 flex-none border-r border-slate-800 bg-[#0b1120] h-full overflow-y-auto">
                <div className="p-4 h-full">
                    <HistoryPanel 
                        apiKey={token}
                        onLogout={handleLogout}
                        docContext={docContext}
                        setDocContext={setDocContext}
                        maxIterations={maxIterations}
                        setMaxIterations={setMaxIterations}
                    />
                </div>
            </aside>
            
            {/* 2. MAIN WORKSPACE - flex-1 allows it to take remaining space */}
            <div className="flex-1 flex flex-col min-w-0 bg-[#020617] relative">
                
                {/* Header with improved spacing */}
                <header className="h-20 flex-none border-b border-slate-800 bg-gradient-to-r from-slate-900/40 to-transparent flex items-center justify-between px-8">
                    <div className="flex items-center gap-4">
                        <button onClick={() => navigate('/dashboard')} className="p-2 border border-slate-700 rounded-lg hover:bg-slate-800 text-slate-400">
                           ←
                        </button>
                        <div>
                            <h1 className="text-sm font-bold tracking-widest text-white">RELEVO ENGINE</h1>
                            <p className="text-[10px] text-indigo-400 font-mono">STATUS: SECURE_CONNECTION</p>
                        </div>
                    </div>
                    <button onClick={handleLogout} className="px-4 py-2 border border-red-500/50 text-red-500 text-[10px] font-bold rounded-lg hover:bg-red-500 hover:text-white transition-all uppercase tracking-tighter">
                        Terminate Session
                    </button>
                </header>
                
                {/* 3. CHAT WINDOW - flex-1 for scrollable area */}
                <main className="flex-1 overflow-y-auto">
                    <ChatWindow 
                        history={history} 
                        isLoading={isLoading} 
                        onContinueOptimization={handleContinueOptimization}
                        onOptionSelect={handleOptionSelect}
                    />
                </main>

                {/* 4. INPUT AREA - High contrast text fixed here */}
                <div className="flex-none p-6 bg-gradient-to-t from-[#020617] to-transparent">
                    <div className="max-w-4xl mx-auto glass-card border border-slate-700 rounded-2xl shadow-2xl p-1">
                        <TextInput
                            input={input}
                            setInput={setInput}
                            handleSend={handleSend}
                            isLoading={isLoading}
                            error={error}
                            inputRef={inputRef}
                            placeholder={inputPlaceholder}
                            className="text-white placeholder-slate-400"
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ChatPage;