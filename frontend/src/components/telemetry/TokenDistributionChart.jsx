import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { motion } from 'framer-motion';

const TokenDistributionChart = ({ data }) => {
  const { timestamps, prompt_tokens, completion_tokens } = data.timeline;

  const formatTime = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  const chartData = timestamps.map((ts, i) => ({
    time: formatTime(ts),
    prompt: prompt_tokens[i],
    completion: completion_tokens[i],
  }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 border border-white/10 rounded-lg p-3 backdrop-blur-md">
          <p className="text-white font-medium">{label}</p>
          <p className="text-indigo-400">Prompt Tokens: <span className="font-bold">{payload[0].value.toLocaleString()}</span></p>
          <p className="text-cyan-400">Completion Tokens: <span className="font-bold">{payload[1].value.toLocaleString()}</span></p>
        </div>
      );
    }
    return null;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1], delay: 0.1 }}
      className="w-full h-64 bg-slate-900/30 rounded-xl border border-white/10 p-4"
    >
      <h3 className="text-white font-semibold mb-4">Token Distribution</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
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
            tickFormatter={(value) => value.toLocaleString()}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ color: '#ffffff80' }}
            formatter={(value) => <span className="text-white/80">{value}</span>}
          />
          <Bar
            dataKey="prompt"
            stackId="a"
            fill="#6366f1"
            animationDuration={500}
          />
          <Bar
            dataKey="completion"
            stackId="a"
            fill="#06b6d4"
            animationDuration={500}
          />
        </BarChart>
      </ResponsiveContainer>
    </motion.div>
  );
};

export default TokenDistributionChart;