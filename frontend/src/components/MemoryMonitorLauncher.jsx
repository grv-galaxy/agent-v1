import React, { useState, useEffect } from 'react';

// --- ToggleSwitch Component (Fixed) ---
function ToggleSwitch({ checked, disabled = false, onChange }) {
  function handleToggle(e) {
    e.stopPropagation(); // Prevents event from bubbling to ToggleRow
    if (!disabled) {
      onChange(!checked);
    }
  }

  return (
    <span
      aria-hidden="true"
      className={`relative block h-6 w-11 rounded-[12px] transition-[background-color] duration-200
        ${checked ? 'bg-[#6366F1]' : 'bg-[#2A2A2A]'}
        ${disabled ? 'opacity-40' : ''}`}
      onClick={handleToggle}
    >
      <span
        className={`absolute top-[3px] h-[18px] w-[18px] rounded-full bg-white transition-transform duration-200 ease-[cubic-bezier(0.4,0,0.2,1)]
          ${checked ? 'translate-x-[23px]' : 'translate-x-[3px]'}`}
      />
    </span>
  );
}

// --- ToggleRow Component (Fixed) ---
function ToggleRow({ checked, disabled = false, label, description, onChange }) {
  return (
    <div
      role="switch"
      aria-checked={checked}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      onClick={() => !disabled && onChange(!checked)} // Only this fires for row clicks
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          !disabled && onChange(!checked);
        }
      }}
      className={`flex w-full cursor-pointer flex-row items-start justify-between gap-4
        ${disabled ? 'cursor-not-allowed opacity-40' : ''}`}
    >
      <div className="flex flex-1 flex-col gap-1">
        <p className="text-[15px] font-medium text-[#E8E8E8]">{label}</p>
        {description ? (
          <p className="max-w-[480px] text-[13px] leading-[1.5] text-[#666666]">
            {description}
          </p>
        ) : null}
      </div>
      <span className="mt-0.5 shrink-0 self-start">
        <ToggleSwitch checked={checked} disabled={disabled} onChange={onChange} />
      </span>
    </div>
  );
}

// --- Main Launcher Component (Fixed with Persistence) ---
const MemoryMonitorLauncher = () => {
  // 1. Initialize state by pulling from the exact same key as your hook
  const [isTracking, setIsTracking] = useState(() => {
    try {
      const savedState = localStorage.getItem('agent.memoryMonitoringEnabled');
      return savedState === 'true'; // Strictly matches the string 'true'
    } catch (e) {
      return false;
    }
  });

  // 2. Keep the local state and localStorage in perfect sync when toggled
  const handleToggleChange = (nextState) => {
    try {
      localStorage.setItem('agent.memoryMonitoringEnabled', String(nextState));
    } catch (e) {
      console.error(e);
    }
    setIsTracking(nextState);
  };

  const handleLaunch = () => {
    const url = new URL(window.location.href);
    url.searchParams.set('dashboard', 'pruning');

    window.open(
      url.toString(),
      '_blank',
      'noopener,noreferrer'
    );
  };

  const statusLabel = isTracking ? 'Active' : 'Telemetry Offline';
  const statusDot = isTracking ? 'bg-[#22C55E]' : 'bg-[#EF4444]';

  return (
    <div className="w-full space-y-3">
      <p className="text-sm font-medium text-[#E8E8E8]">Live Context Telemetry</p>
      <p className="max-w-[560px] text-xs leading-[1.4] text-[#666666]">
        Monitor how the memory LLM condenses history and summarizes system states over background optimization epochs.
      </p>

      <div className="rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6">
        <div className="flex flex-col gap-4">
          <ToggleRow
            checked={isTracking}
            disabled={false}
            label="Enable real-time compression tracking"
            description="Hooks diagnostic handlers directly into the pruning engine to observe token reductions and context mutations instantly."
            onChange={handleToggleChange} // 3. Use our sync wrapper function here
          />

          <div className="mt-2 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className={`h-2 w-2 rounded-full ${statusDot}`} />
              <span className="text-xs text-[#E8E8E8]">STATUS: {statusLabel}</span>
            </div>
            <div className="text-xs text-[#666666]">
              Data Stream: {isTracking ? 'Normal' : 'Offline'}
            </div>
          </div>

          {isTracking ? (
            <div className="mt-3 rounded-[8px] border border-[#1F1F1F] bg-[#0D0D0D] p-3 text-xs text-[#666666]">
              <div className="mb-2 text-[13px] text-[#E8E8E8]">
                ⚡ Stream active: Monitoring LLM context compaction & pruning cycles...
              </div>
            </div>
          ) : (
            <div className="mt-3 rounded-[8px] border border-[#1F1F1F] bg-[#0D0D0D] p-3 text-xs text-[#666666]">
              Telemetry Offline
            </div>
          )}

          <button
            type="button"
            onClick={handleLaunch}
            disabled={!isTracking}
            className={`px-4 py-2 text-xs font-medium rounded transition-all
              ${isTracking
                ? 'bg-[#E8E8E8] text-black hover:bg-white cursor-pointer'
                : 'bg-[#222222] text-[#555555] cursor-not-allowed'}`}
          >
            Launch Telemetry Dashboard ↗
          </button>
        </div>
      </div>
    </div>
  );
};

export default MemoryMonitorLauncher;