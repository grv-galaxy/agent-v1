import React from 'react';
import { motion } from 'framer-motion';
import { Users, MessageSquare, Cpu, Gauge } from 'lucide-react';

const MetricCards = ({ data }) => {
  const { active_sessions, total_messages, estimated_tokens_saved, current_epoch } = data;

  const metrics = [
    {
      title: 'Active Sessions',
      value: active_sessions,
      icon: Users,
      color: 'text-green-400',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/20',
      glowColor: 'shadow-green-500/20',
      unit: '',
      hasRing: true,
    },
    {
      title: 'Total Messages',
      value: total_messages,
      icon: MessageSquare,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/20',
      glowColor: 'shadow-blue-500/20',
      unit: '',
      hasRing: false,
    },
    {
      title: 'Tokens Saved',
      value: estimated_tokens_saved,
      icon: Cpu,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
      borderColor: 'border-purple-500/20',
      glowColor: 'shadow-purple-500/20',
      unit: '',
      hasRing: false,
    },
    {
      title: 'Compaction Depth',
      value: current_epoch,
      icon: Gauge,
      color: 'text-orange-400',
      bgColor: 'bg-orange-500/10',
      borderColor: 'border-orange-500/20',
      glowColor: 'shadow-orange-500/20',
      unit: '',
      hasRing: false,
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.5,
        ease: [0.16, 1, 0.3, 1],
      },
    },
  };

  const formatValue = (value) => {
    if (value >= 1000) {
      return (value / 1000).toFixed(1) + 'k';
    }
    return value.toLocaleString();
  };

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 w-full"
    >
      {metrics.map((metric, index) => (
        <motion.div
          key={index}
          variants={itemVariants}
          className={`
            relative p-6 rounded-xl backdrop-blur-md bg-slate-900/30
            border ${metric.borderColor} ${metric.glowColor}
            hover:bg-slate-800/50 transition-all duration-300
          `}
        >
          {metric.hasRing && (
            <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-green-500 animate-pulse" />
          )}
          <div className="flex items-center gap-4">
            <div className={`p-3 rounded-lg ${metric.bgColor}`}>
              <metric.icon className={`w-6 h-6 ${metric.color}`} />
            </div>
            <div className="flex-1">
              <p className="text-sm text-slate-400 mb-1">{metric.title}</p>
              <motion.p
                initial={{ scale: 0.9 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3 + index * 0.1, type: 'spring', stiffness: 300 }}
                className={`text-2xl font-bold ${metric.color}`}
              >
                {formatValue(metric.value)}
              </motion.p>
            </div>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
};

export default MetricCards;