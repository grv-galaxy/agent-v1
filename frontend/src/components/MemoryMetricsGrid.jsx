import React from 'react';
import { motion } from 'framer-motion';
import { 
  RefreshCw, 
  AlertTriangle, 
  TrendingDown,
  CheckCircle,
  Info,
  Cpu,
  Sliders,
  Layers
} from 'lucide-react';

/**
 * 4-column responsive grid of metric visualization blocks with an integrated 
 * static configuration banner showing model, preset, and threshold boundaries.
 */
const MemoryMetricsGrid = ({ 
  logs = [], 
  isLoading,
  activePreset,
  activeMemoryModel,
  activeChatModel,
  rawBufferLimit,
  summaryCapTokens,
  triggerThreshold,
  groundingInterval
}) => {
  // Calculate metrics from logs array safely
  const totalIterations = logs.length;
  const totalErrors = logs.filter(log => log.status === 'ERROR').length;
  const totalTokensSaved = logs.reduce((sum, log) => sum + (log.tokens_saved || 0), 0);
  const avgCompressionRatio = totalIterations > 0 
    ? (logs.reduce((sum, log) => sum + (log.compression_ratio || 0), 0) / totalIterations * 100).toFixed(1)
    : 0;

  const safeAvgRatio = totalIterations > 0 ? avgCompressionRatio : 0;

  const metrics = [
    {
      title: 'Compactor Iterations',
      value: totalIterations,
      icon: RefreshCw,
      color: 'text-indigo-400',
      bgColor: 'bg-indigo-500/10',
      borderColor: 'border-indigo-500/20',
      tooltip: 'Measures total background compilation epochs executed by the memory provider model when message thresholds are crossed.',
      unit: 'cycles',
    },
    {
      title: 'Total Tokens Saved',
      value: totalTokensSaved,
      icon: TrendingDown,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
      tooltip: 'Cumulative token reduction across all compaction cycles. Higher values indicate more efficient memory optimization.',
      unit: 'tokens',
    },
    {
      title: 'Avg Compression Ratio',
      value: `${safeAvgRatio}%`,
      icon: CheckCircle,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
      borderColor: 'border-emerald-500/20',
      tooltip: 'Average compression efficiency as a percentage. Values closer to 100% indicate optimal memory retention.',
      unit: '',
    },
    {
      title: 'System Stability',
      value: totalErrors,
      icon: AlertTriangle,
      color: totalErrors > 0 ? 'text-amber-400' : 'text-emerald-400',
      bgColor: totalErrors > 0 ? 'bg-amber-500/10' : 'bg-emerald-500/10',
      borderColor: totalErrors > 0 ? 'border-amber-500/20' : 'border-emerald-500/20',
      tooltip: 'Tracks context construction failures or timeouts from the background provider service. Blinks amber if non-zero to signal potential token overflow leaks.',
      unit: 'errors',
      hasAlert: totalErrors > 0,
    },
  ];

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.08,
        delayChildren: 0.1,
      },
    },
  };

  const itemVariants = {
    hidden: { y: 15, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: {
        duration: 0.4,
        ease: [0.16, 1, 0.3, 1],
      },
    },
  };

  const formatValue = (value) => {
    if (typeof value === 'number') {
      return value.toLocaleString();
    }
    return value;
  };

  if (isLoading) {
    return (
      <div className="flex flex-col gap-6 w-full">
        {/* Shimmer for Configuration Strip */}
        <div className="h-12 bg-slate-800/40 rounded-xl border border-white/5 animate-pulse" />
        {/* Shimmer for Metrics Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 w-full">
          {[...Array(4)].map((_, i) => (
            <motion.div
              key={i}
              className="h-28 bg-slate-800/50 rounded-xl border border-white/10 p-6"
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 w-full">
      
      {/* 1. Static Configuration Info Strip */}
      {activeMemoryModel && (
        <motion.div 
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-center justify-between gap-4 p-3 px-5 rounded-xl border border-slate-800 bg-slate-950/40 backdrop-blur-sm text-xs text-slate-400"
        >
          <div className="flex items-center gap-6 flex-wrap">
            <div className="flex items-center gap-2">
              <Cpu className="w-3.5 h-3.5 text-indigo-400" />
              <span>Compactor Model: <strong className="text-slate-200">{activeMemoryModel}</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-emerald-400" />
              <span>Preset Strategy: <strong className="text-slate-200 uppercase tracking-wider">{activePreset}</strong></span>
            </div>
            <div className="flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-amber-400" />
              <span>Buffer Limit: <strong className="text-slate-200">{rawBufferLimit} msgs</strong></span>
            </div>
          </div>
          <div className="text-slate-500 hidden sm:inline-block">
            Cap: {summaryCapTokens}t | Threshold: {triggerThreshold}% | Grounding Every {groundingInterval}e
          </div>
        </motion.div>
      )}

      {/* 2. Runtime Metrics Grid */}
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
              border ${metric.borderColor} shadow-lg
              hover:bg-slate-800/50 transition-all duration-300
            `}
          >
            {metric.hasAlert && (
              <div className="absolute top-3 right-3 w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
            )}
            
            <div className="flex items-start gap-4">
              <div className={`p-3 rounded-lg shrink-0 ${metric.bgColor}`}>
                <metric.icon className={`w-5 h-5 ${metric.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-1">
                  <p className="text-xs font-medium text-slate-400 truncate">{metric.title}</p>
                  <TooltipComponent content={metric.tooltip}>
                    <Info className="w-3.5 h-3.5 text-slate-500 hover:text-slate-400 cursor-help transition-colors" />
                  </TooltipComponent>
                </div>
                <motion.p
                  initial={{ scale: 0.95 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.2 + index * 0.05, type: 'spring', stiffness: 260 }}
                  className={`text-2xl font-bold tracking-tight ${metric.color}`}
                >
                  {formatValue(metric.value)}
                  {metric.unit && (
                    <span className="text-xs font-normal text-slate-500 ml-1 tracking-normal">{metric.unit}</span>
                  )}
                </motion.p>
              </div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </div>
  );
};

// Custom Tooltip component for hover explanations
export const TooltipComponent = ({ content, children }) => {
  const [isVisible, setIsVisible] = React.useState(false);

  return (
    <div className="relative inline-block">
      <div
        onMouseEnter={() => setIsVisible(true)}
        onMouseLeave={() => setIsVisible(false)}
        onFocus={() => setIsVisible(true)}
        onBlur={() => setIsVisible(false)}
        className="cursor-help flex items-center"
      >
        {children}
      </div>
      {isVisible && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-60 p-2.5 text-xs text-slate-300 bg-slate-950 border border-slate-800 rounded-lg shadow-2xl backdrop-blur-md leading-relaxed">
          {content}
          {/* Decorative tail arrow pointing down to icon */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-px w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-slate-950" />
        </div>
      )}
    </div>
  );
};

export { TooltipComponent as Tooltip };
export default MemoryMetricsGrid;