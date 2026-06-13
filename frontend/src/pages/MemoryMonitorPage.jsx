import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Power, Trash2, Table, MessageSquare, Cpu, Settings, Zap } from 'lucide-react';
import { useMemoryMonitor } from '../hooks/useMemoryMonitor';
import MemoryMetricsGrid from '../components/MemoryMetricsGrid';
import MemoryVisualizerCharts from '../components/MemoryVisualizerCharts';
import MemoryLogInspector from '../components/MemoryLogInspector';

/**
 * Memory & Pruning Telemetry Console - Mission Control Center
 * High-performance dashboard for token pruning, context compression, and live state configurations
 */
const MemoryMonitorPage = () => {
  const {
    isTracking,
    logs,
    selectedLog,
    isLoading,
    error,
    toggleTracking,
    clearLogs,
    selectLog,
    refresh,
    activePreset,
    activeMemoryModel,
    activeChatModel,
    rawBufferLimit,
    summaryCapTokens,
    triggerThreshold,
    groundingInterval,
  } = useMemoryMonitor();

  // Format timestamp for display
  const formatTimestamp = (timestamp) => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return 'Invalid timestamp';
    }
  };

  // Get status badge styling
  const getStatusBadge = (status) => {
    const styles = {
      SUCCESS: { text: 'Success', bg: 'bg-emerald-500/10', textColor: 'text-emerald-400', border: 'border-emerald-500/20' },
      ERROR: { text: 'Error', bg: 'bg-rose-500/10', textColor: 'text-rose-400', border: 'border-rose-500/20' },
      COMPRESSING: { text: 'Compressing', bg: 'bg-amber-500/10', textColor: 'text-amber-400', border: 'border-amber-500/20' },
      UNKNOWN: { text: 'Unknown', bg: 'bg-slate-500/10', textColor: 'text-slate-400', border: 'border-slate-500/20' },
    };
    return styles[status] || styles.UNKNOWN;
  };

  // Calculate compilation velocity (tokens/ms)
  const getCompilationVelocity = (log) => {
    if (!log || log.latency_ms === 0) return '0';
    return (log.tokens_saved / log.latency_ms).toFixed(2);
  };

  // Persist tracking state to localStorage
  const handleToggleTracking = (newState) => {
    toggleTracking(newState);
    localStorage.setItem('agent.memoryMonitoringEnabled', JSON.stringify(newState));
  };

  // Handle refresh with sessionStorage sync
  const handleRefresh = () => {
    refresh();
    sessionStorage.setItem('lastMemoryRefresh', Date.now().toString());
  };

  return (
    <div className="min-h-screen bg-slate-950 p-2 sm:p-3 md:p-4 lg:p-6">
      {/* ===== HEADER WITH DYNAMIC METADATA BAR ===== */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col gap-3 sm:gap-4 mb-4 sm:mb-6 border-b border-white/5 pb-4 sm:pb-6"
      >
        {/* Title + Status Row */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="space-y-1.5 flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl md:text-3xl font-bold text-white truncate">
              Memory & Pruning Telemetry Console
            </h1>

            {/* High-Density Status Toolbar */}
            <div className="flex flex-wrap items-center gap-x-3 sm:gap-x-4 gap-y-1.5 text-xs text-slate-400">
              {/* Engine Code */}
              <div className="flex items-center gap-1">
                <Cpu className="w-3 h-3 text-indigo-400" />
                <span className="text-slate-500">Engine:</span>
                <span className="text-indigo-400 font-medium">{activeChatModel || 'Awaiting Handshake...'}</span>
              </div>

              {/* Memory Sub-Engine */}
              <div className="flex items-center gap-1">
                <MessageSquare className="w-3 h-3 text-cyan-400" />
                <span className="text-slate-500">Memory:</span>
                <span className="text-cyan-400 font-medium">{activeMemoryModel || 'Offline'}</span>
              </div>

              {/* Active Strategy Mode */}
              <div className="flex items-center gap-1">
                <Settings className="w-3 h-3 text-emerald-400" />
                <span className="text-slate-500">Preset:</span>
                <span className={`font-medium ${activePreset === 'custom' ? 'text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded' : 'text-emerald-400'}`}>
                  {activePreset ? activePreset.charAt(0).toUpperCase() + activePreset.slice(1) : 'N/A'}
                </span>
              </div>

              {/* Sliding Scale Parameters (Hidden on mobile) */}
              <div className="hidden md:flex items-center gap-1">
                <Zap className="w-3 h-3 text-amber-400" />
                <span className="text-slate-500">Buffer:</span>
                <span className="text-amber-400 font-medium">{rawBufferLimit ? `${rawBufferLimit} slots` : 'N/A'}</span>
              </div>

              <div className="hidden md:flex items-center gap-1">
                <span className="text-slate-500">Token Cap:</span>
                <span className="text-rose-400 font-medium">{summaryCapTokens ? `${summaryCapTokens}t` : 'N/A'}</span>
              </div>
            </div>
          </div>

          {/* Tracking Status Badge */}
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs sm:text-sm max-w-fit shrink-0 self-start sm:self-center border
            ${isTracking ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-slate-800/50 text-slate-400 border-slate-700/20'}`}>
            <div className={`w-1.5 h-1.5 rounded-full ${isTracking ? 'bg-emerald-400 animate-pulse' : 'bg-slate-600'}`} />
            <span>{isTracking ? 'Tracking Active' : 'Tracking Paused'}</span>
          </div>
        </div>

        {/* Action Buttons - Wraps on mobile */}
        <div className="flex flex-wrap gap-2 sm:gap-3 justify-start sm:justify-end">
          <motion.button
            whileTap={{ scale: 0.98 }}
            onClick={handleRefresh}
            disabled={!isTracking}
            className="flex items-center gap-1.5 px-2 py-1.5 sm:px-3 sm:py-2 bg-slate-800/50 border border-white/10 rounded-lg text-xs sm:text-sm text-white hover:bg-slate-700/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Table className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            <span>Refresh</span>
          </motion.button>

          <motion.button
            whileTap={{ scale: 0.98 }}
            onClick={clearLogs}
            className="flex items-center gap-1.5 px-2 py-1.5 sm:px-3 sm:py-2 bg-slate-800/50 border border-white/10 rounded-lg text-xs sm:text-sm text-white hover:bg-rose-500/10 transition-all"
          >
            <Trash2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            <span>Clear Logs</span>
          </motion.button>

          <motion.button
            whileTap={{ scale: 0.98 }}
            onClick={() => handleToggleTracking(!isTracking)}
            className={`flex items-center gap-1.5 px-2 py-1.5 sm:px-3 sm:py-2 rounded-lg text-xs sm:text-sm text-white transition-all shadow-md font-medium
              ${isTracking ? 'bg-amber-600 hover:bg-amber-700' : 'bg-indigo-600 hover:bg-indigo-700'}`}>
            <Power className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            <span>{isTracking ? 'Pause Tracking' : 'Start Tracking'}</span>
          </motion.button>
        </div>
      </motion.div>

      {/* ===== ERROR STATE ===== */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-4 p-3 sm:p-4 bg-rose-900/20 border border-rose-500/30 rounded-lg"
          >
            <p className="text-rose-400 text-xs sm:text-sm">{error}</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ===== METRICS GRID ===== */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.1 }}
        className="mb-4 sm:mb-6"
      >
        <MemoryMetricsGrid logs={logs} isLoading={isLoading} />
      </motion.div>

      {/* ===== CHARTS ===== */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.2 }}
        className="mb-4 sm:mb-6"
      >
        <MemoryVisualizerCharts logs={logs} isLoading={isLoading} />
      </motion.div>

      {/* ===== SPLIT PANE LAYOUT ===== */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 md:gap-6 min-h-[300px] sm:min-h-[400px] lg:min-h-[500px]"
      >
        {/* --- Left: Execution Feed (100% mobile, 50% tablet, 33% desktop) --- */}
        <motion.div
          layout
          className="lg:col-span-1 bg-slate-900/30 rounded-xl border border-white/10 overflow-hidden flex flex-col"
        >
          <div className="p-2 sm:p-3 border-b border-white/10 shrink-0 bg-slate-900/50">
            <h3 className="text-white font-semibold flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
              <Table className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              Execution Feed
            </h3>
          </div>

          {/* Responsive Table with Hidden Columns */}
          <div className="overflow-auto flex-1">
            {isLoading && Array.isArray(logs) && logs.length === 0 ? (
              <div className="p-4 text-center text-slate-500">
                <p className="text-xs sm:text-sm animate-pulse">Loading logs...</p>
              </div>
            ) : Array.isArray(logs) && logs.length === 0 ? (
              <div className="p-4 text-center text-slate-500">
                <p className="text-xs sm:text-sm">No logs. Start tracking to see metrics.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs sm:text-sm">
                  <thead className="text-left text-slate-500 border-b border-white/10 bg-slate-950 sticky top-0 backdrop-blur-sm z-10">
                    <tr>
                      <th className="p-2 sm:p-3 whitespace-nowrap">Epoch</th>
                      <th className="p-2 sm:p-3 whitespace-nowrap hidden md:table-cell">Timestamp</th>
                      <th className="p-2 sm:p-3 whitespace-nowrap hidden lg:table-cell">Velocity</th>
                      <th className="p-2 sm:p-3 whitespace-nowrap font-mono">Δ Tokens</th>
                      <th className="p-2 sm:p-3 whitespace-nowrap font-mono">Velocity (t/ms)</th>
                      <th className="p-2 sm:p-3 whitespace-nowrap">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Array.isArray(logs) && logs.map((log) => {
                      const badge = getStatusBadge(log.status);
                      return (
                        <motion.tr
                          key={log.epoch}
                          onClick={() => selectLog(log)}
                          whileHover={{ scale: 1.01 }}
                          className={`border-b border-white/5 transition-colors
                            ${selectedLog?.epoch === log.epoch ? 'bg-slate-800/40 font-medium' : 'hover:bg-slate-800/50'}
                            cursor-pointer`}
                        >
                          <td className="p-2 sm:p-3 text-white whitespace-nowrap">{log.epoch}</td>
                          <td className="p-2 sm:p-3 text-slate-400 whitespace-nowrap hidden md:table-cell">
                            {formatTimestamp(log.timestamp)}
                          </td>
                          <td className="p-2 sm:p-3 text-indigo-400 whitespace-nowrap hidden lg:table-cell">
                            {getCompilationVelocity(log)}
                          </td>
                          <td className="p-2 sm:p-3 text-emerald-400 whitespace-nowrap font-mono">
                            +{log.tokens_saved?.toLocaleString() || 0}
                          </td>
                          <td className="p-2 sm:p-3 text-cyan-400 whitespace-nowrap font-mono">
                            {getCompilationVelocity(log)}
                          </td>
                          <td className="p-2 sm:p-3 whitespace-nowrap">
                            <span className={`px-1.5 py-0.5 sm:px-2 sm:py-1 rounded-full text-xs font-medium inline-block border ${badge.bg} ${badge.textColor} ${badge.border}`}>
                              {badge.text}
                            </span>
                          </td>
                        </motion.tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </motion.div>

        {/* --- Right: Inspector (100% mobile/tablet, 66% desktop) --- */}
        <motion.div
          layout
          className="md:col-span-2 lg:col-span-2 min-h-[250px] sm:min-h-[350px] lg:min-h-[450px]"
        >
          <MemoryLogInspector selectedLog={selectedLog} />
        </motion.div>
      </motion.div>
    </div>
  );
};

export default MemoryMonitorPage;