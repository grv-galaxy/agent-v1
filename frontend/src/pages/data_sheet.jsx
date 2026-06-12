import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Power, Loader2 } from 'lucide-react';
import MetricCards from '../components/telemetry/MetricCards.jsx';
import LatencyWaveChart from '../components/telemetry/LatencyWaveChart.jsx';
import TokenDistributionChart from '../components/telemetry/TokenDistributionChart.jsx';
import CompressionEfficiencyChart from '../components/telemetry/CompressionEfficiencyChart.jsx';

// 🌟 CHANGED: Point explicitly to your Python backend API location
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const DataSheet = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isTelemetryEnabled, setIsTelemetryEnabled] = useState(true);

  const fetchData = async () => {
    try {
      // 🌟 CHANGED: Appended API_BASE_URL to hit port 8000 instead of 5173
      const response = await fetch(`${API_BASE_URL}/api/memory-stats`);
      if (!response.ok) throw new Error('Failed to fetch data');
      const result = await response.json();
      setData(result);
      setIsTelemetryEnabled(result.telemetry_enabled);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  };

  const toggleTelemetry = async () => {
    try {
      const newState = !isTelemetryEnabled;
      // 🌟 CHANGED: Appended API_BASE_URL here as well
      const response = await fetch(`${API_BASE_URL}/api/memory-stats/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telemetry_enabled: newState }),
      });
      if (!response.ok) throw new Error('Failed to toggle telemetry');
      setIsTelemetryEnabled(newState);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  // Pause fetching when tab is not active
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchData();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const SkeletonLoader = () => (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 w-full"
    >
      {[...Array(4)].map((_, i) => (
        <motion.div
          key={i}
          className="h-24 bg-slate-800/50 rounded-xl border border-white/10 p-6"
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
        />
      ))}
    </motion.div>
  );

  const TelemetryDisabledOverlay = () => (
    <AnimatePresence>
      {isTelemetryEnabled === false && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 bg-slate-900/80 backdrop-blur-md flex items-center justify-center z-50"
        >
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            className="bg-slate-800/90 border border-white/10 rounded-xl p-8 max-w-md text-center"
          >
            <Power className="w-12 h-12 text-orange-500 mx-auto mb-4 animate-pulse" />
            <h3 className="text-xl font-bold text-white mb-2">Telemetry Disabled</h3>
            <p className="text-slate-400 mb-6">Enable telemetry in your configuration to start tracking metrics.</p>
            <button
              onClick={toggleTelemetry}
              className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-all"
            >
              Enable Telemetry
            </button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );

  if (loading) return <SkeletonLoader />;
  if (error) return <p className="text-red-500">Error: {error}</p>;

  return (
    <div className="min-h-screen bg-slate-950 p-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center mb-8"
      >
        <h1 className="text-3xl font-bold text-white">Telemetry Dashboard</h1>
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 rounded-full text-sm ${isTelemetryEnabled ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
            {isTelemetryEnabled ? 'Live' : 'Paused'}
          </span>
          <button
            onClick={toggleTelemetry}
            className="p-2 rounded-lg bg-slate-800/50 border border-white/10 hover:bg-slate-700/50 transition-all"
          >
            <Power className={`w-5 h-5 ${isTelemetryEnabled ? 'text-green-400' : 'text-red-400'}`} />
          </button>
        </div>
      </motion.div>

      {/* Metric Cards */}
      <AnimatePresence mode="wait">
        {data && (
          <motion.div
            key="metrics"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
          >
            <MetricCards data={data} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Charts */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
        className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-8"
      >
        <LatencyWaveChart data={data} />
        <TokenDistributionChart data={data} />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="mt-6"
      >
        <CompressionEfficiencyChart data={data} />
      </motion.div>

      {/* Overlay */}
      <TelemetryDisabledOverlay />
    </div>
  );
};

export default DataSheet;