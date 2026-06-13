import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Diff, Code, AlertCircle, CheckCircle, ChevronRight, Server, Terminal, Layers } from 'lucide-react';

/**
 * Lower execution inspector with 3-tier horizontal menu interface.
 * Visualizes code diffs, styles conversational token pruning threads,
 * and tracks engine diagnostic metadata from the active stream payload.
 */
const MemoryLogInspector = ({ selectedLog }) => {
  const [activeTab, setActiveTab] = useState('diff');

  if (!selectedLog) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="w-full h-full min-h-[380px] bg-slate-900/30 rounded-xl border border-white/10 flex items-center justify-center p-8 text-center"
      >
        <div className="max-w-md">
          <div className="w-12 h-12 rounded-xl bg-slate-950 border border-white/5 flex items-center justify-center mx-auto mb-4 text-slate-500 shadow-inner">
            <Terminal className="w-5 h-5 animate-pulse" />
          </div>
          <p className="text-sm font-semibold text-white mb-1">No Epoch Selected</p>
          <p className="text-xs text-slate-500 leading-relaxed">
            Select an epoch event instance from the tracking sheet to parse context states, 
            diff records, and payload exceptions.
          </p>
        </div>
      </motion.div>
    );
  }

  const tabs = [
    { id: 'diff', label: 'Summary Diff', icon: Diff },
    { id: 'pruned', label: 'Pruned Context', icon: Code },
    { id: 'diagnostics', label: 'Diagnostics', icon: AlertCircle },
  ];

  // Format timestamp safely for localization
  const formattedTime = selectedLog.timestamp 
    ? new Date(selectedLog.timestamp).toLocaleString() 
    : 'N/A';

  // Defensive Patch: Fallback across different pipeline API data keys
  const messagePayload = selectedLog.raw_input_chunk || selectedLog.chat_history || selectedLog.messages || [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="w-full h-full min-h-[380px] flex flex-col bg-slate-900/30 rounded-xl border border-white/10 overflow-hidden shadow-2xl backdrop-blur-md"
    >
      {/* Tab Header */}
      <div className="flex border-b border-white/10 bg-slate-950/40 shrink-0 px-2 pt-2 gap-1">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                relative flex items-center gap-2 px-4 py-2.5 text-xs font-medium
                transition-all duration-200 rounded-t-lg border-t border-x border-transparent -mb-px
                ${isActive
                  ? 'bg-slate-900/70 text-white border-white/10 border-b-slate-900'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800/30'
                }
              `}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
              {isActive && (
                <motion.div 
                  layoutId="activeInspectorIndicator"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-400 z-10"
                />
              )}
            </button>
          );
        })}
      </div>

      {/* Tab Content Workspace */}
      <div className="p-5 flex-1 overflow-auto bg-slate-900/10">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 5 }}
            transition={{ duration: 0.2 }}
            className="h-full flex flex-col"
          >
            
            {/* === TAB 1: SUMMARY DIFF VIEW === */}
            {activeTab === 'diff' && (
              <div className="space-y-4 flex-1 flex flex-col h-full">
                <div className="flex flex-wrap items-center justify-between gap-4 text-xs text-slate-400 border-b border-white/5 pb-3 shrink-0">
                  <div className="flex items-center gap-4">
                    <span>Epoch Index: <strong className="text-white font-mono">#{selectedLog.epoch}</strong></span>
                    <span className="text-slate-600">|</span>
                    <span>Executed: <strong className="text-slate-300">{formattedTime}</strong></span>
                  </div>
                  <p className="text-slate-500 text-[11px]">
                    Comparison analysis for context stability between prior and updated summary states.
                  </p>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
                  {/* Prior Summary Panel */}
                  <div className="flex flex-col rounded-lg border border-white/5 bg-slate-950 overflow-hidden h-full min-h-[180px]">
                    <div className="bg-slate-900/40 px-3 py-2 border-b border-white/5 text-[10px] uppercase font-bold tracking-wider text-slate-400 flex justify-between items-center">
                      <span>Prior Summary Frame</span>
                      <span className="font-mono text-slate-600 font-normal">{selectedLog.raw_prior_summary?.length || 0} chars</span>
                    </div>
                    <div className="p-4 text-xs font-mono text-slate-400 overflow-y-auto whitespace-pre-wrap leading-relaxed flex-1 select-text selection:bg-indigo-500/20">
                      {selectedLog.raw_prior_summary ? (
                        selectedLog.raw_prior_summary
                      ) : (
                        <span className="text-slate-700 italic">No historical summary recorded prior to this compaction event runtime frame.</span>
                      )}
                    </div>
                  </div>
                  
                  {/* Updated Summary Panel */}
                  <div className="flex flex-col rounded-lg border border-white/5 bg-slate-950 overflow-hidden h-full min-h-[180px]">
                    <div className="bg-slate-900/40 px-3 py-2 border-b border-white/5 text-[10px] uppercase font-bold tracking-wider text-emerald-400 flex justify-between items-center">
                      <span>Mutated Output Summary</span>
                      <span className="font-mono text-slate-600 font-normal">{selectedLog.raw_output_summary?.length || 0} chars</span>
                    </div>
                    <div className="p-4 text-xs font-mono text-slate-200 overflow-y-auto whitespace-pre-wrap leading-relaxed flex-1 select-text selection:bg-emerald-500/20">
                      {selectedLog.status === 'ERROR' ? (
                        <span className="text-rose-400/80">Compilation execution failed. Check full system traceback metrics under Diagnostics.</span>
                      ) : selectedLog.raw_output_summary ? (
                        selectedLog.raw_output_summary
                      ) : (
                        <span className="text-slate-700 italic">No compaction data produced during this active tick event.</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* === TAB 2: PRUNED TRANSCRIPT CONTEXT === */}
            {activeTab === 'pruned' && (
              <div className="space-y-4 flex-1 flex flex-col h-full">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs text-slate-400 border-b border-white/5 pb-3 shrink-0">
                  <div>Context Cache Size: <span className="text-white font-mono font-bold">{selectedLog.tokens_before?.toLocaleString()} t</span></div>
                  <div>Compressed Footprint: <span className="text-white font-mono font-bold">{selectedLog.tokens_after?.toLocaleString()} t</span></div>
                  <div>Reduction Savings: <span className="text-emerald-400 font-mono font-bold">+{selectedLog.tokens_saved?.toLocaleString()} tokens</span></div>
                  <p className="text-slate-500 text-[11px] text-right self-center hidden sm:block">Exact array logs sliced out of sliding chat memory.</p>
                </div>
                
                <div className="bg-slate-950 rounded-lg border border-white/5 p-4 overflow-y-auto flex-1 flex flex-col gap-3 max-h-[380px]">
                  {Array.isArray(messagePayload) && messagePayload.length > 0 ? (
                    messagePayload.map((msg, index) => (
                      <div 
                        key={index}
                        className={`p-3 rounded-lg border text-xs max-w-[85%] leading-relaxed ${
                          msg.role === 'user' 
                            ? 'bg-slate-900/90 border-white/5 self-end text-slate-200' 
                            : msg.role === 'system'
                            ? 'bg-indigo-950/20 border-indigo-500/10 self-center text-indigo-300 font-mono text-[11px] max-w-full w-full'
                            : 'bg-slate-900/30 border-slate-800/80 self-start text-slate-300'
                        }`}
                      >
                        <div className="text-[10px] uppercase tracking-wider font-bold text-slate-500 mb-1 flex items-center justify-between">
                          <span>{msg.role || 'unknown'}</span>
                          <span className="text-slate-600 text-[9px] font-mono font-normal">#{index}</span>
                        </div>
                        <p className="whitespace-pre-wrap select-text">{msg.content || JSON.stringify(msg)}</p>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-12 text-slate-600 italic text-xs font-mono">
                      {`// No conversational elements sliced out during this compaction cycle yet.`}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* === TAB 3: DIAGNOSTICS & HARDWARE MATRIX === */}
            {activeTab === 'diagnostics' && (
              <div className="space-y-4 flex-1 flex flex-col h-full">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 shrink-0">
                  <div className="p-3 bg-slate-950 rounded-lg border border-white/5 flex items-center gap-3">
                    <Server className="w-4 h-4 text-indigo-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-bold">Chat Core</span>
                      <span className="text-xs text-slate-300 font-mono truncate block" title={selectedLog.model_name}>{selectedLog.model_name || 'openai/gpt-oss-120b'}</span>
                    </div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-white/5 flex items-center gap-3">
                    <Layers className="w-4 h-4 text-emerald-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-bold">Compactor Engine</span>
                      <span className="text-xs text-slate-300 font-mono truncate block">{selectedLog.memory_model || 'llama-3.1-8b-instant'}</span>
                    </div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-white/5 flex items-center gap-3">
                    <Terminal className="w-4 h-4 text-amber-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-bold">Latency Profile</span>
                      <span className="text-xs text-slate-300 font-mono block">{selectedLog.latency_ms || 0} ms</span>
                    </div>
                  </div>
                  <div className="p-3 bg-slate-950 rounded-lg border border-white/5 flex items-center gap-3">
                    <Code className="w-4 h-4 text-slate-400 shrink-0" />
                    <div className="min-w-0">
                      <span className="block text-[10px] text-slate-500 uppercase tracking-wider font-bold">Grounding State</span>
                      <span className="text-xs text-slate-300 font-mono block">{selectedLog.grounding_applied ? 'ANCHORED (True)' : 'STANDBY (False)'}</span>
                    </div>
                  </div>
                </div>

                <div className="flex-1 min-h-[180px] flex flex-col">
                  {selectedLog.status === 'ERROR' ? (
                    <div className="flex flex-col flex-1 rounded-lg border border-rose-500/30 overflow-hidden bg-rose-950/10">
                      <div className="bg-rose-950/40 px-3 py-2 border-b border-rose-500/20 text-xs font-semibold text-rose-400 flex items-center gap-2">
                        <AlertCircle className="w-4 h-4 shrink-0" />
                        <span>Exception Traceback Output Logs</span>
                      </div>
                      <pre className="p-4 text-xs font-mono text-rose-300/90 overflow-y-auto whitespace-pre-wrap leading-relaxed select-text bg-slate-950 flex-1">
                        {selectedLog.raw_output_summary || 
                        `Error: Context construction failure or timeout at epoch ${selectedLog.epoch}
Timestamp: ${formattedTime}
Latency: ${selectedLog.latency_ms} ms
Compression Ratio: ${(selectedLog.compression_ratio * 100).toFixed(1)}%

This indicates a structural network boundary timeout, downstream orchestration failure, or context allocation threshold overflow.`}
                      </pre>
                    </div>
                  ) : (
                    <div className="flex flex-col flex-1 rounded-lg border border-white/5 bg-slate-950/50 p-4 min-h-0 overflow-hidden">
                      <div className="flex items-center gap-3 border-b border-white/5 pb-3 shrink-0">
                        <div className="w-8 h-8 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 shrink-0">
                          <CheckCircle className="w-4 h-4" />
                        </div>
                        <div>
                          <h5 className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Pipeline Execution Stabilized</h5>
                          <p className="text-slate-500 text-[11px]">Compactor cycle running cleanly inside boundary constraints.</p>
                        </div>
                      </div>

                      <div className="mt-3 flex-1 overflow-y-auto pr-1">
                        <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block mb-2">
                          Extracted Fact History Ledger ({selectedLog.summary_history?.length || 0})
                        </span>
                        {Array.isArray(selectedLog.summary_history) && selectedLog.summary_history.length > 0 ? (
                          <div className="flex flex-col gap-1.5 font-mono text-[11px]">
                            {selectedLog.summary_history.map((fact, idx) => (
                              <div key={idx} className="flex gap-2 p-2 rounded bg-slate-950 border border-white/5 text-slate-400 leading-normal">
                                <ChevronRight className="w-3.5 h-3.5 text-slate-600 shrink-0 mt-0.5" />
                                <span className="select-text">{fact}</span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="text-slate-600 italic text-xs font-mono p-4 bg-slate-950 rounded border border-white/5">
                            {`// Ledger array empty. Summary context stable with no unique incremental mutations recorded.`}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

          </motion.div>
        </AnimatePresence>
      </div>
    </motion.div>
  );
};

export default MemoryLogInspector;