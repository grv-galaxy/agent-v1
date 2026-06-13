// Memory & Pruning Telemetry Type Definitions
// Structured contract for logging elements in the agent-v1 platform

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
}

export interface MemoryLogEntry {
  epoch: number; // Sequential iteration index (matches payload's compression_epoch)
  timestamp: string; // ISO 8601 localized time string
  status: 'SUCCESS' | 'ERROR'; // Operational state
  latency_ms: number; // Backend processing time
  tokens_before: number; // Inbound pruned context token count
  tokens_after: number; // Resultant rolling summary token count
  tokens_saved: number; // Absolute token reduction (tokens_before - tokens_after)
  compression_ratio: number; // Ratio: tokens_saved / tokens_before (0.0 to 1.0)
  grounding_applied: boolean; // Whether memory anchoring was triggered
  
  // Sourced Arrays and Context Dumps
  raw_input_chunk: ChatMessage[]; // Array of message objects sliced out for compression
  raw_prior_summary: string; // Previous summary state (rolling_summary)
  raw_output_summary: string; // Updated summary state or error trace logs
  summary_history: string[]; // Accumulated history array of extracted facts summaries

  // --- NEW: Statically Available Configuration Metadata ---
  memory_provider: string; // LLM Provider backend engine (e.g., "groq")
  memory_model: string; // Target compaction model name (e.g., "llama-3.1-8b-instant")
  model_name: string; // Main streaming chat model name (e.g., "openai/gpt-oss-120b")
  provider: string; // Main streaming chat provider engine (e.g., "groq")
  memory_preset: 'precise' | 'balanced' | 'turbo' | string; // Configured strategy preset
  memory_raw_buffer: number; // Configured message allocation limit count before compaction
  memory_trigger_threshold: number; // Threshold metric setting that forces compression gates
  memory_summary_cap_tokens: number; // Max targeted output token allocations for summaries
  memory_grounding_interval: number; // Interval value set between anchoring sync checks
  session_id: string; // Unique string identifying the active tracking chat session identifier
  use_memory: boolean; // Boolean flag checking if conversational long-term memory is active
  should_compress: boolean; // Flag evaluating if evaluation thresholds are crossed
}

export interface MemoryMonitorState {
  isTracking: boolean; // Master toggle for polling
  logs: MemoryLogEntry[]; // Historical log entries
  selectedLog: MemoryLogEntry | null; // Currently inspected entry
  isLoading: boolean; // Async fetch state
  error: string | null; // Error message
  
  // --- NEW: Globally Available Engine Metrics ---
  activePreset: string | null;
  activeMemoryModel: string | null;
  activeChatModel: string | null;
  rawBufferLimit: number | null;
  summaryCapTokens: number | null;
}

export interface TokenTrendData {
  epoch: number;
  tokens_before: number;
  tokens_after: number;
}

export interface EfficiencyData {
  epoch: number;
  latency_ms: number;
  compression_ratio: number;
}

export type MemoryTab = 'diff' | 'pruned' | 'diagnostics';