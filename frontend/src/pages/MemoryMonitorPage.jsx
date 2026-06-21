import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Brain, Database, Layers, FileText, FileSearch, RefreshCw,
  MessageSquare, Bot, User, Cpu, Activity, Zap, ShieldCheck,
  AlertTriangle, Copy, ChevronDown, ChevronUp, Search, AlertCircle
} from 'lucide-react';

// Default fallback payload for empty/missing fields
const defaultPayload = {
  compression_chunk: [],
  compression_epoch: 0,
  memory_grounding_interval: 5,
  memory_model: 'N/A',
  memory_preset: 'N/A',
  memory_provider: 'N/A',
  memory_raw_buffer: 0,
  memory_summary_cap_tokens: 0,
  memory_trigger_threshold: 1,
  messages: [],
  should_compress: false,
  summary_history: [],
  use_memory: false
};

const MemoryMonitorPage = () => {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [expandedSummaries, setExpandedSummaries] = useState({});
  const [expandedChunks, setExpandedChunks] = useState({});
  const [isPayloadExpanded, setIsPayloadExpanded] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Function to safely parse and merge payload
  const parsePayload = (storedPayload) => {
    try {
      const parsed = storedPayload ? JSON.parse(storedPayload) : {};
      // Merge with defaults to handle missing fields
      return { ...defaultPayload, ...parsed };
    } catch (e) {
      console.error('Failed to parse payload:', e);
      setError('Invalid payload format in localStorage');
      return defaultPayload;
    }
  };

  // Load and subscribe to localStorage changes
  useEffect(() => {
    const loadPayload = () => {
      const storedPayload = localStorage.getItem('agent.live_payload_stream');
      const newPayload = parsePayload(storedPayload);

      // Also read an on-session summary from localStorage (key: 'summary')
      // Parse it as an array/object/string and merge all entries into
      // `summary_history` so each item is rendered individually.
      const rawSessionSummary = localStorage.getItem('summary');
      let sessionEntries = [];
      if (rawSessionSummary) {
        try {
          const parsed = JSON.parse(rawSessionSummary);
          if (Array.isArray(parsed)) {
            sessionEntries = parsed.map(entry => typeof entry === 'string' ? entry : JSON.stringify(entry, null, 2));
          } else if (parsed && typeof parsed === 'object') {
            const keys = Object.keys(parsed);
            const allNumeric = keys.length > 0 && keys.every(k => !isNaN(Number(k)));
            if (allNumeric) {
              sessionEntries = keys
                .sort((a, b) => Number(a) - Number(b))
                .map(k => (typeof parsed[k] === 'string' ? parsed[k] : JSON.stringify(parsed[k], null, 2)));
            } else {
              sessionEntries = [JSON.stringify(parsed, null, 2)];
            }
          } else if (typeof parsed === 'string') {
            sessionEntries = [parsed];
          }
        } catch (e) {
          // Not JSON — try splitting by newline and strip numeric prefixes like `0: `
          sessionEntries = rawSessionSummary
            .split(/\r?\n/)
            .map(s => s.trim())
            .filter(Boolean)
            .map(s => s.replace(/^\s*\d+\s*:\s*/, ''));
        }
      }

      // Use only localStorage `summary` entries for the Summary History UI.
      // If none present, expose an empty array so the UI shows the empty state.
      const mergedHistory = sessionEntries.length ? sessionEntries : [];

      setPayload({ ...newPayload, summary_history: mergedHistory });
    };

    // Initial load
    loadPayload();

    // Listen for storage changes (cross-tab updates)
    const handleStorageChange = (e) => {
      if (e.key === 'agent.live_payload_stream') {
        loadPayload();
      }
    };
    window.addEventListener('storage', handleStorageChange);

    // Polling for same-tab updates (since storage events don't fire in the same tab)
    const intervalId = setInterval(loadPayload, 1000);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(intervalId);
    };
  }, []);

  // Show loading state only while initial payload is being fetched
  if (payload === null) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <div className="text-zinc-400 flex items-center gap-2">
          <Activity className="animate-spin" />
          Loading memory payload...
        </div>
      </div>
    );
  }

  // Calculate derived values with fallbacks
  const messageCount = payload.messages?.length || 0;
  const memoryUtilization = payload.memory_trigger_threshold > 0
    ? Math.min(
        Math.round((messageCount / payload.memory_trigger_threshold) * 100),
        100
      )
    : 0;
  const messagesRemaining = Math.max(
    (payload.memory_trigger_threshold || 0) - messageCount,
    0
  );

  // Status logic
  const getHealthStatus = () => {
    if (memoryUtilization < 50) return { color: 'text-green-400', label: 'Healthy' };
    if (memoryUtilization < 90) return { color: 'text-yellow-400', label: 'Approaching Compression' };
    return { color: 'text-red-400', label: 'Compression Imminent' };
  };

  const healthStatus = getHealthStatus();

  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { duration: 0.5, staggerChildren: 0.1 },
    },
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.5 },
    },
  };

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text);
  };

  const toggleSummary = (index) => {
    setExpandedSummaries(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const toggleChunk = (index) => {
    setExpandedChunks(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  // Helper to safely get array length
  const getArrayLength = (arr) => arr?.length || 0;

  return (
    <div className="min-h-screen bg-zinc-950 p-4 md:p-6 lg:p-8">
      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400"
        >
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-red-300 hover:text-red-200"
          >
            Dismiss
          </button>
        </motion.div>
      )}

      {/* Header */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="mb-8"
      >
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold text-zinc-100 flex items-center gap-2">
              <Brain className="text-blue-400" />
              Memory Monitor Dashboard
            </h1>
            <p className="text-zinc-400 mt-1">
              Real-time visibility into memory compression, conversation state, summarization, grounding, and memory health.
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className={`px-4 py-2 rounded-full text-sm font-medium flex items-center gap-2 ${
              payload.use_memory
                ? 'bg-green-500/10 text-green-400 border border-green-500/20'
                : 'bg-red-500/10 text-red-400 border border-red-500/20'
            }`}>
              <Cpu className="w-4 h-4" />
              {payload.use_memory ? 'MEMORY ACTIVE' : 'MEMORY DISABLED'}
            </div>
            <div className="px-4 py-2 bg-zinc-900 rounded-xl border border-zinc-800">
              <span className="text-zinc-400 text-sm">Total Messages</span>
              <span className="text-zinc-100 font-bold ml-2">{messageCount}</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Memory Metrics Grid */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={containerVariants}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
      >
        {[
          {
            icon: Layers,
            value: payload.compression_epoch,
            label: 'Compression Epoch',
            description: 'Current compression cycle',
            color: 'text-blue-400'
          },
          {
            icon: Database,
            value: payload.memory_raw_buffer,
            label: 'Raw Buffer Size',
            description: 'Messages retained before processing',
            color: 'text-purple-400'
          },
          {
            icon: Zap,
            value: payload.memory_trigger_threshold,
            label: 'Trigger Threshold',
            description: 'Message threshold before compression',
            color: 'text-yellow-400'
          },
          {
            icon: RefreshCw,
            value: payload.memory_grounding_interval,
            label: 'Grounding Interval',
            description: 'Grounding refresh frequency',
            color: 'text-green-400'
          },
          {
            icon: FileText,
            value: payload.memory_summary_cap_tokens,
            label: 'Summary Token Cap',
            description: 'Maximum summary token limit',
            color: 'text-cyan-400'
          },
          {
            icon: MessageSquare,
            value: messageCount,
            label: 'Message Count',
            description: 'Current conversation size',
            color: 'text-orange-400'
          }
        ].map((metric, index) => (
          <motion.div
            key={index}
            variants={itemVariants}
            whileHover={{ scale: 1.02, borderColor: '#3b82f6' }}
            className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur transition-all duration-300 cursor-pointer"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className={`p-2 rounded-xl bg-zinc-800 ${metric.color}`}>
                <metric.icon className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-zinc-100 font-semibold">{metric.label}</h3>
                <p className="text-zinc-400 text-sm">{metric.description}</p>
              </div>
            </div>
            <div className="text-3xl font-bold text-zinc-100">{metric.value}</div>
          </motion.div>
        ))}
      </motion.div>

      {/* Memory Configuration Panel */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={itemVariants}
        className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur mb-8"
      >
        <h2 className="text-xl font-bold text-zinc-100 mb-4 flex items-center gap-2">
          <Cpu className="text-blue-400" />
          Memory Configuration
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <p className="text-zinc-400 text-sm">Provider</p>
              <p className="text-zinc-100 font-medium">{payload.memory_provider || 'N/A'}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
              <Brain className="w-6 h-6" />
            </div>
            <div>
              <p className="text-zinc-400 text-sm">Model</p>
              <p className="text-zinc-100 font-medium">{payload.memory_model || 'N/A'}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-green-500/10 text-green-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="text-zinc-400 text-sm">Preset</p>
              <p className="text-zinc-100 font-medium">{payload.memory_preset || 'N/A'}</p>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Compression Status Panel */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={itemVariants}
        className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur mb-8"
      >
        <h2 className="text-xl font-bold text-zinc-100 mb-4 flex items-center gap-2">
          <Layers className="text-yellow-400" />
          Compression Status
        </h2>
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-xl ${
              payload.should_compress
                ? 'bg-green-500/10 text-green-400'
                : 'bg-zinc-800 text-zinc-400'
            }`}>
              {payload.should_compress ? (
                <AlertTriangle className="w-6 h-6" />
              ) : (
                <ShieldCheck className="w-6 h-6" />
              )}
            </div>
            <div>
              <h3 className="text-zinc-100 font-semibold">
                {payload.should_compress ? 'Compression Required' : 'Compression Not Required'}
              </h3>
              <p className="text-zinc-400 text-sm">
                Current state of memory compression
              </p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-zinc-800/50 rounded-xl p-4">
              <p className="text-zinc-400 text-sm mb-1">Compression Epoch</p>
              <p className="text-zinc-100 font-bold text-xl">{payload.compression_epoch}</p>
            </div>
            <div className="bg-zinc-800/50 rounded-xl p-4">
              <p className="text-zinc-400 text-sm mb-1">Compression Chunk Count</p>
              <p className="text-zinc-100 font-bold text-xl">{getArrayLength(payload.compression_chunk)}</p>
            </div>
          </div>
          <div className="bg-zinc-800/50 rounded-xl p-4">
            <div className="flex justify-between items-center mb-2">
              <span className="text-zinc-400 text-sm">Compression Progress</span>
              <span className="text-zinc-100 font-medium">
                {getArrayLength(payload.compression_chunk)} chunks
              </span>
            </div>
            <div className="h-2 bg-zinc-700 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-blue-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${Math.min(getArrayLength(payload.compression_chunk) * 10, 100)}%` }}
                transition={{ duration: 1 }}
              />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Memory Health Analysis */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={itemVariants}
        className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur mb-8"
      >
        <h2 className="text-xl font-bold text-zinc-100 mb-4 flex items-center gap-2">
          <Activity className="text-green-400" />
          Memory Health Analysis
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="flex flex-col items-center">
            <div className="relative w-32 h-32 mb-4">
              <svg className="w-full h-full" viewBox="0 0 100 100">
                <circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="none"
                  stroke="#3f3f46"
                  strokeWidth="8"
                />
                <motion.circle
                  cx="50"
                  cy="50"
                  r="45"
                  fill="none"
                  stroke={memoryUtilization < 50 ? '#22c55e' : memoryUtilization < 90 ? '#f59e0b' : '#ef4444'}
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray="283"
                  strokeDashoffset={283 - (283 * memoryUtilization) / 100}
                  initial={{ strokeDashoffset: 283 }}
                  animate={{ strokeDashoffset: 283 - (283 * memoryUtilization) / 100 }}
                  transition={{ duration: 1 }}
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-2xl font-bold text-zinc-100">{memoryUtilization}%</span>
              </div>
            </div>
            <p className={`font-medium ${healthStatus.color}`}>{healthStatus.label}</p>
          </div>
          <div className="bg-zinc-800/50 rounded-xl p-4 text-center">
            <p className="text-zinc-400 text-sm mb-1">Messages Remaining Before Compression</p>
            <p className="text-zinc-100 font-bold text-3xl">{messagesRemaining}</p>
          </div>
          <div className="bg-zinc-800/50 rounded-xl p-4">
            <p className="text-zinc-400 text-sm mb-2">Health Indicators</p>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${memoryUtilization < 50 ? 'bg-green-500' : 'bg-zinc-600'}`} />
                <span className="text-zinc-300 text-sm">Buffer: {payload.memory_raw_buffer} messages</span>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${memoryUtilization < 90 ? 'bg-green-500' : 'bg-zinc-600'}`} />
                <span className="text-zinc-300 text-sm">Threshold: {payload.memory_trigger_threshold} messages</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500" />
                <span className="text-zinc-300 text-sm">Grounding: Every {payload.memory_grounding_interval} messages</span>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Conversation Timeline */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={itemVariants}
        className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur mb-8"
      >
        <h2 className="text-xl font-bold text-zinc-100 mb-4 flex items-center gap-2">
          <MessageSquare className="text-cyan-400" />
          Conversation Timeline
        </h2>
        {messageCount === 0 ? (
          <div className="text-center py-12">
            <FileSearch className="w-12 h-12 text-zinc-500 mx-auto mb-4" />
            <p className="text-zinc-400">No messages in conversation</p>
          </div>
        ) : (
          <div className="max-h-[600px] overflow-y-auto space-y-4 pr-2">
            {payload.messages?.map((msg, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                className={`flex gap-3 p-4 rounded-xl ${
                  msg.role === 'user'
                    ? 'bg-blue-500/5 border border-blue-500/10 ml-auto max-w-[80%]'
                    : 'bg-zinc-800/50 border border-zinc-700 mr-auto max-w-[80%]'
                }`}
              >
                <div className="flex flex-col items-center">
                  <div className={`p-2 rounded-full ${
                    msg.role === 'user'
                      ? 'bg-blue-500/10 text-blue-400'
                      : 'bg-zinc-700 text-zinc-300'
                  }`}>
                    {msg.role === 'user' ? <User className="w-5 h-5" /> : <Bot className="w-5 h-5" />}
                  </div>
                  <span className="text-zinc-400 text-xs mt-1">{index + 1}</span>
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      msg.role === 'user'
                        ? 'bg-blue-500/10 text-blue-400'
                        : 'bg-zinc-700 text-zinc-300'
                    }`}>
                      {msg.role.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-zinc-100 whitespace-pre-wrap">{msg.content || '[Empty message]'}</p>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Summary History */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={itemVariants}
        className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur mb-8"
      >
        <h2 className="text-xl font-bold text-zinc-100 mb-4 flex items-center gap-2">
          <FileText className="text-purple-400" />
          Summary History
        </h2>
        {getArrayLength(payload.summary_history) === 0 ? (
          <div className="text-center py-12">
            <FileSearch className="w-12 h-12 text-zinc-500 mx-auto mb-4" />
            <p className="text-zinc-400">No summary history available</p>
          </div>
        ) : (
          <div className="space-y-3">
            {payload.summary_history?.map((summary, index) => (
              <motion.div
                key={index}
                initial="hidden"
                animate="visible"
                variants={itemVariants}
                className="bg-zinc-800/50 rounded-xl border border-zinc-700 overflow-hidden"
              >
                <button
                  onClick={() => toggleSummary(index)}
                  className="w-full p-4 text-left flex items-center justify-between hover:bg-zinc-700/50 transition-colors"
                >
                  <span className="text-zinc-100 font-medium">Summary #{index + 1}</span>
                  {expandedSummaries[index] ? (
                    <ChevronUp className="w-5 h-5 text-zinc-400" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-zinc-400" />
                  )}
                </button>
                {expandedSummaries[index] && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    transition={{ duration: 0.3 }}
                    className="p-4 pt-0 text-zinc-300 whitespace-pre-wrap"
                  >
                    {summary || '[Empty summary]'}
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Compression Chunks */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={itemVariants}
        className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur mb-8"
      >
        <h2 className="text-xl font-bold text-zinc-100 mb-4 flex items-center gap-2">
          <Layers className="text-orange-400" />
          Compression Chunks
        </h2>
        {getArrayLength(payload.compression_chunk) === 0 ? (
          <div className="text-center py-12">
            <FileSearch className="w-12 h-12 text-zinc-500 mx-auto mb-4" />
            <p className="text-zinc-400">No compression chunks generated</p>
          </div>
        ) : (
          <div className="space-y-3">
            {payload.compression_chunk?.map((chunk, index) => (
              <motion.div
                key={index}
                initial="hidden"
                animate="visible"
                variants={itemVariants}
                className="bg-zinc-800/50 rounded-xl border border-zinc-700 overflow-hidden"
              >
                <div className="p-4 flex items-center justify-between bg-zinc-700/30">
                  <span className="text-zinc-100 font-medium">Chunk #{index + 1}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => copyToClipboard(JSON.stringify(chunk))}
                      className="p-1.5 rounded hover:bg-zinc-600 transition-colors"
                      title="Copy"
                    >
                      <Copy className="w-4 h-4 text-zinc-400" />
                    </button>
                    <button
                      onClick={() => toggleChunk(index)}
                      className="p-1.5 rounded hover:bg-zinc-600 transition-colors"
                      title="Expand"
                    >
                      {expandedChunks[index] ? (
                        <ChevronUp className="w-4 h-4 text-zinc-400" />
                      ) : (
                        <ChevronDown className="w-4 h-4 text-zinc-400" />
                      )}
                    </button>
                  </div>
                </div>
                {expandedChunks[index] && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    transition={{ duration: 0.3 }}
                    className="p-4 overflow-x-auto"
                  >
                    <pre className="text-sm text-zinc-300 font-mono whitespace-pre-wrap">
                      {JSON.stringify(chunk, null, 2)}
                    </pre>
                  </motion.div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>

      {/* Raw Payload Inspector */}
      <motion.div
        initial="hidden"
        animate="visible"
        variants={itemVariants}
        className="bg-zinc-900 rounded-2xl p-6 border border-zinc-800 shadow-xl backdrop-blur"
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-zinc-100 flex items-center gap-2">
            <Database className="text-red-400" />
            Raw Memory Payload
          </h2>
          <button
            onClick={() => setIsPayloadExpanded(!isPayloadExpanded)}
            className="p-2 rounded-xl hover:bg-zinc-800 transition-colors"
          >
            {isPayloadExpanded ? (
              <ChevronUp className="w-5 h-5 text-zinc-400" />
            ) : (
              <ChevronDown className="w-5 h-5 text-zinc-400" />
            )}
          </button>
        </div>
        {isPayloadExpanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            transition={{ duration: 0.3 }}
            className="border-t border-zinc-800 pt-4"
          >
            <div className="flex gap-2 mb-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-400" />
                <input
                  type="text"
                  placeholder="Search payload..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-zinc-800/50 border border-zinc-700 rounded-xl pl-10 pr-4 py-2 text-zinc-100 focus:outline-none focus:border-blue-500"
                />
              </div>
              <button
                onClick={() => copyToClipboard(JSON.stringify(payload, null, 2))}
                className="px-4 py-2 bg-zinc-800/50 border border-zinc-700 rounded-xl hover:bg-zinc-700/50 transition-colors flex items-center gap-2"
              >
                <Copy className="w-4 h-4 text-zinc-400" />
                <span className="text-zinc-300 text-sm">Copy JSON</span>
              </button>
            </div>
            <div className="max-h-[400px] overflow-y-auto bg-zinc-800/30 rounded-xl p-4 font-mono text-sm">
              <pre className="text-zinc-300 whitespace-pre-wrap">
                {searchQuery
                  ? JSON.stringify(payload, null, 2).replace(
                      new RegExp(searchQuery, 'gi'),
                      match => `<mark class="bg-yellow-500/20 text-yellow-300">${match}</mark>`
                    )
                  : JSON.stringify(payload, null, 2)
                }
              </pre>
            </div>
          </motion.div>
        )}
      </motion.div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1 }}
        className="text-center text-zinc-500 text-sm mt-8"
      >
        Memory Monitor Dashboard | Real-time Observability | Auto-Updating
      </motion.p>
    </div>
  );
};

export default MemoryMonitorPage;
