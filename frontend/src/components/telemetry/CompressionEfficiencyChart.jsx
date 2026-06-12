import React from 'react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ReferenceLine } from 'recharts';
import { motion } from 'framer-motion';

const CompressionEfficiencyChart = ({ data }) => {
  const { timestamps, compression_ratios, grounding_epoch_markers } = data.timeline;

  const formatTime = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const chartData = timestamps.map((ts, i) => ({
    time: formatTime(ts),
    ratio: compression_ratios[i],
    epoch: i + 1, // Assuming epochs are 1-indexed
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 border border-white/10 rounded-lg p-3 backdrop-blur-md">
          <p className="text-white font-medium">{label}</p>
          <p className="text-emerald-400">Compression Ratio: <span className="font-bold">{(payload[0].value * 100).toFixed(1)}%</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
      className="w-full h-64 bg-slate-900/30 rounded-xl border border-white/10 p-4"
    >
      <h3 className="text-white font-semibold mb-4">Compression Efficiency</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
            domain={[0, 1]}
            tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          {grounding_epoch_markers.map((marker, index) => (
            <ReferenceLine
              key={index}
              x={marker}
              stroke="#f59e0b"
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{ value: `Epoch ${marker}`, fill: '#f59e0b', fontSize: 10 }}
            />
          ))}
          <Line
            type="monotone"
            dataKey="ratio"
            stroke="#10b981"
            strokeWidth={2}
            dot={{ fill: '#10b981', r: 4 }}
            activeDot={{ r: 6, fill: '#10b981' }}
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

export default CompressionEfficiencyChart;