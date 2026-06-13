import React from 'react';
import { motion } from 'framer-motion';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts';

/**
 * Engineering-grade visualization analytics suite for memory telemetry.
 * Contains 2 responsive charts: Area Overlay for Token Convergence and Line Multi-Y for Latency vs Efficiency.
 */
const MemoryVisualizerCharts = ({ logs = [], isLoading }) => {
  if (isLoading || logs.length === 0) {
    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
        {[...Array(2)].map((_, i) => (
          <motion.div
            key={i}
            className="w-full h-72 bg-slate-900/30 rounded-xl border border-white/10 p-6 flex flex-col justify-between"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: i * 0.1 }}
          >
            <div className="h-4 bg-slate-800/40 rounded w-1/3 animate-pulse" />
            <div className="w-full h-44 bg-slate-800/20 rounded border border-white/5 border-dashed animate-pulse flex items-center justify-center">
              <span className="text-[10px] uppercase font-mono tracking-widest text-slate-600">Awaiting telemetry pipeline...</span>
            </div>
          </motion.div>
        ))}
      </div>
    );
  }

  // Map and sanitize standard UI log metrics
  const chartData = logs.map((log) => ({
    epoch: log.epoch ?? 0,
    tokens_before: Number(log.tokens_before) || 0,
    tokens_after: Number(log.tokens_after) || 0,
    latency_ms: Number(log.latency_ms) || 0,
    compression_ratio: Number(log.compression_ratio) ? Number(log.compression_ratio) * 100 : 0,
    grounding_applied: Boolean(log.grounding_applied),
  }));

  // Identify all active grounding anchoring epochs to draw system reference markers
  const groundingEpochs = chartData.filter(d => d.grounding_applied);

  // Custom Tooltip for Token Convergence Chart View
  const TokenTrendTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const isAnchored = logs.find(l => l.epoch === label)?.grounding_applied;
      return (
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 shadow-2xl backdrop-blur-md max-w-xs border-t-indigo-500 border-t-2">
          <div className="flex items-center justify-between gap-4 mb-2">
            <p className="text-white font-mono font-bold text-xs">Epoch Sequence #{label}</p>
            {isAnchored && (
              <span className="text-[9px] bg-amber-500/10 border border-amber-500/30 text-amber-400 px-1 rounded uppercase tracking-wider font-extrabold">
                Anchored
              </span>
            )}
          </div>
          <div className="space-y-1 mb-2">
            <p className="text-indigo-400 text-xs flex justify-between gap-4">
              Inbound Pruned Context: <span className="font-mono font-bold text-slate-200">{payload[0].value.toLocaleString()} t</span>
            </p>
            <p className="text-emerald-400 text-xs flex justify-between gap-4">
              Resultant Summary Size: <span className="font-mono font-bold text-slate-200">{payload[1].value.toLocaleString()} t</span>
            </p>
          </div>
          <p className="text-slate-500 text-[10px] leading-relaxed border-t border-white/5 pt-2">
            <strong>Token Retainment Trend:</strong> Compares raw historical buffer sizes against compiled summaries. 
            An upward trending summary line that converges with inbound context signals formatting 
            bloat or a failure in recursive pruning rules.
          </p>
        </div>
      );
    }
    return null;
  };

  // Custom Tooltip for Latency vs. Efficiency Chart View
  const EfficiencyTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 shadow-2xl backdrop-blur-md max-w-xs border-t-emerald-500 border-t-2">
          <p className="text-white font-mono font-bold text-xs mb-2">Epoch Sequence #{label}</p>
          <div className="space-y-1 mb-2">
            <p className="text-amber-400 text-xs flex justify-between gap-4">
              Execution Latency: <span className="font-mono font-bold text-slate-200">{payload[0].value.toFixed(1)} ms</span>
            </p>
            <p className="text-emerald-400 text-xs flex justify-between gap-4">
              Compaction Ratio Yield: <span className="font-mono font-bold text-slate-200">{payload[1].value.toFixed(1)}%</span>
            </p>
          </div>
          <p className="text-slate-500 text-[10px] leading-relaxed border-t border-white/5 pt-2">
            <strong>Operational Efficiency Metrics:</strong> Displays backend processing time versus calculated 
            memory optimization yield. Spikes in execution time accompanied by drops in compression 
            ratios indicate service-side serialization delays or model constraint bottlenecks.
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 w-full">
      
      {/* 1. Token Convergence Area Chart */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="w-full h-72 bg-slate-900/30 rounded-xl border border-white/10 p-4 flex flex-col"
      >
        <div className="flex justify-between items-center mb-3 shrink-0">
          <h3 className="text-slate-200 text-sm font-semibold tracking-tight">Token Convergence Overlays</h3>
          <span className="text-[10px] font-mono font-semibold text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/10">
            Linear Convergence Space
          </span>
        </div>
        <div className="flex-1 min-h-0 text-[11px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="tokenGradientBefore" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                  <stop offset="95%" stopColor="#6366f1" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="tokenGradientAfter" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
              <XAxis
                dataKey="epoch"
                stroke="#ffffff30"
                tick={{ fill: '#ffffff50', fontMono: true }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                stroke="#ffffff30"
                tick={{ fill: '#ffffff50' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => val >= 1000 ? `${(val / 1000).toFixed(0)}k` : val}
              />
              <Tooltip content={<TokenTrendTooltip />} cursor={{ stroke: '#ffffff10', strokeWidth: 1 }} />
              <Legend 
                verticalAlign="top" 
                height={28}
                iconSize={8}
                formatter={(val) => <span className="text-slate-400 text-xs hover:text-slate-200 transition-colors">{val}</span>}
              />
              
              {/* Dynamic Grounding System Boundary Lines */}
              {groundingEpochs.map((d) => (
                <ReferenceLine
                  key={d.epoch}
                  x={d.epoch}
                  stroke="#f59e0b"
                  strokeDasharray="4 4"
                  strokeWidth={1.5}
                  opacity={0.6}
                />
              ))}

              <Area
                type="monotone"
                dataKey="tokens_before"
                name="Inbound Pruned Context"
                stroke="#6366f1"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#tokenGradientBefore)"
                dot={{ fill: '#6366f1', r: 2, strokeWidth: 0 }}
                activeDot={{ r: 4, strokeWidth: 0 }}
                animationDuration={400}
              />
              <Area
                type="monotone"
                dataKey="tokens_after"
                name="Resultant Rolling Summary"
                stroke="#10b981"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#tokenGradientAfter)"
                dot={{ fill: '#10b981', r: 2, strokeWidth: 0 }}
                activeDot={{ r: 4, strokeWidth: 0 }}
                animationDuration={400}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </motion.div>

      {/* 2. Latency vs. Efficiency Multi-Axis Line Chart */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
        className="w-full h-72 bg-slate-900/30 rounded-xl border border-white/10 p-4"
      >
        <div className="flex justify-between items-center mb-3 shrink-0">
          <h3 className="text-slate-200 text-sm font-semibold tracking-tight">Latency vs. Compression Yield</h3>
          <span className="text-[10px] font-mono font-semibold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/10">
            Multi-Axis Engine Trace
          </span>
        </div>
        <div className="flex-1 min-h-0 text-[11px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: -10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" vertical={false} />
              <XAxis
                dataKey="epoch"
                stroke="#ffffff30"
                tick={{ fill: '#ffffff50', fontMono: true }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                yAxisId="left"
                orientation="left"
                stroke="#fbbf24"
                tick={{ fill: '#fbbf24', opacity: 0.8 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}ms`}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                stroke="#10b981"
                tick={{ fill: '#10b981', opacity: 0.8 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(val) => `${val}%`}
              />
              <Tooltip content={<EfficiencyTooltip />} cursor={{ stroke: '#ffffff10', strokeWidth: 1 }} />
              <Legend 
                verticalAlign="top" 
                height={28}
                iconSize={8}
                formatter={(val) => <span className="text-slate-400 text-xs hover:text-slate-200 transition-colors">{val}</span>}
              />
              
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="latency_ms"
                name="Telemetry Latency (ms)"
                stroke="#fbbf24"
                strokeWidth={2}
                dot={{ fill: '#fbbf24', r: 2.5, strokeWidth: 0 }}
                activeDot={{ r: 4.5, strokeWidth: 0 }}
                animationDuration={450}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="compression_ratio"
                name="Compression Yield (%)"
                stroke="#10b981"
                strokeWidth={2}
                dot={{ fill: '#10b981', r: 2.5, strokeWidth: 0 }}
                activeDot={{ r: 4.5, strokeWidth: 0 }}
                animationDuration={450}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </motion.div>
    </div>
  );
};

export default MemoryVisualizerCharts;