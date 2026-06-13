// import { useState, useEffect, useCallback } from 'react';

// /**
//  * Custom hook for managing memory telemetry state and polling.
//  * Implements a 2500ms polling loop with conditional gating based on isTracking.
//  * Integrates global configuration metadata from runtime chat payloads and synchronizes cross-tab states.
//  */
// export const useMemoryMonitor = () => {
//   const [state, setState] = useState(() => {
//     let persistedTracking = false;
//     try {
//       // Initialize straight from the target persistence key
//       const savedState = localStorage.getItem('agent.memoryMonitoringEnabled');
//       if (savedState !== null) {
//         persistedTracking = savedState === 'true' || savedState === true;
//       }
//     } catch (e) {
//       console.error("Failed to read tracking state from localStorage:", e);
//     }

//     return {
//       isTracking: persistedTracking,
//       logs: [],
//       selectedLog: null,
//       isLoading: false,
//       error: null,
      
//       // Config and Engine variables sourced directly from the chat payload structure
//       activePreset: null,
//       activeMemoryModel: null,
//       activeChatModel: null,
//       rawBufferLimit: null,
//       summaryCapTokens: null,
//       triggerThreshold: null,
//       groundingInterval: null,
//     };
//   });

//   // Fetch logs from the backend telemetry endpoint
//   const fetchLogs = useCallback(async () => {
//     try {
//       setState((prev) => ({ ...prev, isLoading: true, error: null }));
      
//       // Target router endpoint designed to yield both state configuration matrices and ring-buffer logs
//       const response = await fetch('/api/memory-monitor/logs');
      
//       if (!response.ok) {
//         throw new Error(`HTTP error! status: ${response.status}`);
//       }
      
//       const data = await response.json();
      
//       // 1. Map static structural configuration layers from the payload frame if present
//       const configUpdate = data.config_snapshot ? {
//         activePreset: data.config_snapshot.memory_preset || 'balanced',
//         activeMemoryModel: data.config_snapshot.memory_model || 'llama-3.1-8b-instant',
//         activeChatModel: data.config_snapshot.model_name || 'openai/gpt-oss-120b',
//         rawBufferLimit: Number(data.config_snapshot.memory_raw_buffer) || 10,
//         summaryCapTokens: Number(data.config_snapshot.memory_summary_cap_tokens) || 800,
//         triggerThreshold: Number(data.config_snapshot.memory_trigger_threshold) || 30,
//         groundingInterval: Number(data.config_snapshot.memory_grounding_interval) || 5,
//       } : {};

//       // 2. Transform the backend volatile ring buffer array logs into standard UI format
//       const transformedLogs = Array.isArray(data.logs) 
//         ? data.logs.map((log) => ({
//             epoch: log.epoch ?? log.compression_epoch ?? 0,
//             timestamp: log.timestamp || new Date().toISOString(),
//             status: log.status || 'SUCCESS',
//             latency_ms: Number(log.latency_ms) || 0,
//             tokens_before: Number(log.tokens_before) || 0,
//             tokens_after: Number(log.tokens_after) || 0,
//             tokens_saved: Number(log.tokens_saved) || (Number(log.tokens_before) - Number(log.tokens_after)) || 0,
//             compression_ratio: Number(log.compression_ratio) || 0,
//             grounding_applied: Boolean(log.grounding_applied),
            
//             // Dynamic text structures and array transcript objects
//             raw_input_chunk: Array.isArray(log.raw_input_chunk) ? log.raw_input_chunk : [],
//             raw_prior_summary: log.raw_prior_summary || '',
//             raw_output_summary: log.raw_output_summary || '',
//             summary_history: Array.isArray(log.summary_history) ? log.summary_history : [],
            
//             // Context metadata passthrough properties
//             memory_provider: log.memory_provider || data.config_snapshot?.memory_provider || '',
//             memory_model: log.memory_model || data.config_snapshot?.memory_model || '',
//             session_id: log.session_id || data.config_snapshot?.session_id || ''
//           }))
//         : [];

//       setState((prev) => {
//         // Retain selection stability across polling cycles if matching item persists
//         const currentSelection = prev.selectedLog 
//           ? transformedLogs.find(l => l.epoch === prev.selectedLog.epoch) || transformedLogs[0] || null
//           : transformedLogs[0] || null;

//         return {
//           ...prev,
//           ...configUpdate,
//           logs: transformedLogs,
//           selectedLog: currentSelection,
//           isLoading: false,
//         };
//       });
//     } catch (err) {
//       setState((prev) => ({
//         ...prev,
//         error: err.message || 'Failed to fetch memory telemetry matrix arrays',
//         isLoading: false,
//       }));
//     }
//   }, []);

//   // Toggle tracking state control plane adapter
//   const toggleTracking = useCallback(async (nextState) => {
//     try {
//       localStorage.setItem('agent.memoryMonitoringEnabled', String(nextState));
//       setState((prev) => ({ ...prev, isTracking: nextState, isLoading: true }));
      
//       const response = await fetch('/api/memory-monitor/toggle', {
//         method: 'POST',
//         headers: { 'Content-Type': 'application/json' },
//         body: JSON.stringify({ active: nextState }),
//       });

//       if (!response.ok) {
//         throw new Error(`Failed to change hardware tracking operational mode state: ${response.status}`);
//       }

//       const confirmation = await response.json();
//       const updatedTrackingFlag = confirmation.isTracking ?? nextState;

//       localStorage.setItem('agent.memoryMonitoringEnabled', String(updatedTrackingFlag));

//       setState((prev) => ({ 
//         ...prev, 
//         isTracking: updatedTrackingFlag,
//         isLoading: false 
//       }));

//       // Immediately execute initial loop pull if activated
//       if (updatedTrackingFlag) {
//         fetchLogs();
//       }
//     } catch (err) {
//       localStorage.setItem('agent.memoryMonitoringEnabled', String(!nextState));
//       setState((prev) => ({
//         ...prev,
//         error: `Control plane boundary failure: ${err.message}`,
//         isTracking: !nextState, // Revert state safely on connection failure
//         isLoading: false
//       }));
//     }
//   }, [fetchLogs]);

//   // Sync state cleanly across decoupled windows or navigation panels
//   useEffect(() => {
//     const handleStorageChange = (event) => {
//       if (event.key === 'agent.memoryMonitoringEnabled') {
//         const newValue = event.newValue === 'true';
//         setState((prev) => ({ ...prev, isTracking: newValue }));
        
//         if (newValue) {
//           fetchLogs();
//         }
//       }
//     };

//     window.addEventListener('storage', handleStorageChange);
//     return () => {
//       window.removeEventListener('storage', handleStorageChange);
//     };
//   }, [fetchLogs]);

//   // Clear volatile storage arrays across UI states
//   const clearLogs = useCallback(() => {
//     setState((prev) => ({ 
//       ...prev, 
//       logs: [], 
//       selectedLog: null 
//     }));
//   }, []);

//   // Select localized item event sequence metrics row
//   const selectLog = useCallback((log) => {
//     setState((prev) => ({ ...prev, selectedLog: log }));
//   }, []);

//   // Polling management loop gate logic
//   useEffect(() => {
//     let intervalId = null;
    
//     if (state.isTracking) {
//       fetchLogs(); // Initial immediate pull
//       intervalId = setInterval(fetchLogs, 2500);
//     }

//     return () => {
//       if (intervalId) {
//         clearInterval(intervalId);
//       }
//     };
//   }, [state.isTracking, fetchLogs]);

//   // Pause background processing queries when standard browser window state drops visibility profiles
//   useEffect(() => {
//     const handleVisibilityChange = () => {
//       if (document.visibilityState === 'visible' && state.isTracking) {
//         fetchLogs();
//       }
//     };

//     document.addEventListener('visibilitychange', handleVisibilityChange);
//     return () => {
//       document.removeEventListener('visibilitychange', handleVisibilityChange);
//     };
//   }, [state.isTracking, fetchLogs]);

//   return {
//     ...state,
//     toggleTracking,
//     clearLogs,
//     selectLog,
//     refresh: fetchLogs,
//   };
// };

// export default useMemoryMonitor;








































































import { useState, useEffect, useCallback } from 'react';

/**
 * Session-Scoped Frontend Telemetry Hook
 * Reads live configuration snapshots and builds historical tracking logs directly 
 * from the frontend chat payload stream stored in sessionStorage.
 */
export const useMemoryMonitor = () => {
  const [state, setState] = useState({
    isTracking: true,
    logs: [],
    selectedLog: null,
    isLoading: false,
    error: null,
    
    // Default config values matching ChatPage configurations
    activePreset: 'balanced',
    activeMemoryModel: 'llama-3.1-8b-instant',
    activeChatModel: 'openai/gpt-oss-120b',
    rawBufferLimit: 10,
    summaryCapTokens: 800,
    triggerThreshold: 30,
    groundingInterval: 5,
  });

  // Pulls tracking coordinate snapshots out of the active browser sessionStorage
  const readSessionPayload = useCallback(() => {
    try {
      const rawSessionData = sessionStorage.getItem('agent.live_payload_stream');
      if (!rawSessionData) return;

      const payload = JSON.parse(rawSessionData);

      setState((prev) => {
        // Explicitly convert numeric properties
        const rawBuffer = Number(payload.memory_raw_buffer);
        const tokenCap = Number(payload.memory_summary_cap_tokens);
        const threshold = Number(payload.memory_trigger_threshold);
        const grounding = Number(payload.memory_grounding_interval);

        // Build a visual log card frame using active stream metrics
        const dynamicLog = {
          epoch: payload.compression_epoch ?? 0,
          timestamp: new Date().toISOString(),
          status: payload.should_compress ? 'COMPRESSING' : 'SUCCESS',
          latency_ms: 0,
          tokens_before: 0,
          tokens_after: 0,
          tokens_saved: 0,
          compression_ratio: 1.0,
          grounding_applied: false,
          
          // Data contexts passed safely via payload tracking structure
          raw_input_chunk: Array.isArray(payload.messages) ? payload.messages : [],
          raw_prior_summary: payload.rolling_summary || 'No summary context active.',
          raw_output_summary: payload.rolling_summary || '',
          summary_history: Array.isArray(payload.summary_history) ? payload.summary_history : [],
          
          memory_provider: payload.memory_provider || payload.provider || '',
          memory_model: payload.memory_model || 'llama-3.1-8b-instant',
          session_id: payload.session_id || ''
        };

        // Avoid adding exact duplicate tracking log items within the same execution epoch context
        const isDuplicate = prev.logs.length > 0 && 
                            prev.logs[0].epoch === dynamicLog.epoch && 
                            prev.logs[0].raw_prior_summary === dynamicLog.raw_prior_summary;
                            
        const updatedLogs = isDuplicate ? prev.logs : [dynamicLog, ...prev.logs].slice(0, 30);

        return {
          ...prev,
          activePreset: payload.memory_preset || prev.activePreset,
          activeMemoryModel: payload.memory_model || prev.activeMemoryModel,
          activeChatModel: payload.model_name || prev.activeChatModel,
          // Use isNaN check validation to ensure 0 value bounds don't get overwritten by defaults
          rawBufferLimit: isNaN(rawBuffer) ? prev.rawBufferLimit : rawBuffer,
          summaryCapTokens: isNaN(tokenCap) ? prev.summaryCapTokens : tokenCap,
          triggerThreshold: isNaN(threshold) ? prev.triggerThreshold : threshold,
          groundingInterval: isNaN(grounding) ? prev.groundingInterval : grounding,
          logs: updatedLogs,
          selectedLog: prev.selectedLog || dynamicLog
        };
      });
    } catch (err) {
      console.error("Failed parsing session stream frame:", err);
    }
  }, []);

  // Set up listeners for the live custom tab event updates
  useEffect(() => {
    // Read historical settings context frame instantly on component mounting
    readSessionPayload();

    // Catch updates immediately on the same page workspace
    window.addEventListener('storage_update', readSessionPayload);
    // Cross-tab fallback event bridge handler
    window.addEventListener('storage', readSessionPayload);

    return () => {
      window.removeEventListener('storage_update', readSessionPayload);
      window.removeEventListener('storage', readSessionPayload);
    };
  }, [readSessionPayload]);

  // Clear volatile UI arrays across state layouts
  const clearLogs = useCallback(() => {
    setState((prev) => ({ 
      ...prev, 
      logs: [], 
      selectedLog: null 
    }));
  }, []);

  // Update specific timeline log selection indexes
  const selectLog = useCallback((log) => {
    setState((prev) => ({ ...prev, selectedLog: log }));
  }, []);

  return {
    ...state,
    toggleTracking: (nextState) => {
      setState(prev => ({ ...prev, isTracking: nextState }));
    },
    clearLogs,
    selectLog,
    refresh: readSessionPayload, // Manual update sync trigger pass
  };
};

export default useMemoryMonitor;