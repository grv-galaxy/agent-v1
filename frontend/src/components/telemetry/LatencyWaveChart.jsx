import React from 'react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { motion } from 'framer-motion';

const LatencyWaveChart = ({ data }) => {
  const { timestamps, message_latencies_ms } = data.timeline;

  // Transform timestamps to local time strings
  const formatTime = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const chartData = timestamps.map((ts, i) => ({
    time: formatTime(ts),
    latency: message_latencies_ms[i],
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 border border-white/10 rounded-lg p-3 backdrop-blur-md">
          <p className="text-white font-medium">{label}</p>
          <p className="text-cyan-400">Latency: <span className="font-bold">{payload[0].value.toFixed(2)} ms</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="w-full h-64 bg-slate-900/30 rounded-xl border border-white/10 p-4"
    >
      <h3 className="text-white font-semibold mb-4">Message Latency Wave</h3>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
          <XAxis
            dataKey="time"
            stroke="#ffffff40"
            tick={{ fontSize: 12, fill: '#ffffff60' }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#ffffff40"
            tick={{ fontSize: 12, fill: '#ffffff60' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `${value} ms`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="latency"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#latencyGradient)"
            animationDuration={500}
          />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

export default LatencyWaveChart;