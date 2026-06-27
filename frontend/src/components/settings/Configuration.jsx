import React, { useState, useEffect } from 'react';

// Core Mathematical Configuration Definitions
const PRESETS = {
  precise:  { t: 40, r: 15, cap: 1200, interval: 3 },
  balanced: { t: 30, r: 10, cap: 800,  interval: 5 },
  turbo:    { t: 15, r: 4,  cap: 500,  interval: 7 }
};

const SLIDER_MAP = ['precise', 'balanced', 'turbo'];

// Info Icon SVG Component
const InfoIcon = () => (
  <svg
    className="w-3 h-3 text-[#6366F1] cursor-help"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M12 16v-4" />
    <path d="M12 8h.01" />
  </svg>
);

// Tooltip Component for Parameter Descriptions
const ParameterTooltip = ({ parameter, description }) => {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div className="relative inline-block">
      <div
        className="flex items-center gap-1 cursor-help"
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
      >
        <span className="text-[#94A3B8] text-[13px] capitalize">{parameter}</span>
        <InfoIcon />
      </div>
      {showTooltip && (
        <div className="absolute z-10 left-0 bottom-full mb-2 px-3 py-2 text-[11px] text-[#E8E8E8] bg-[#1A1A1A] border border-[#2A2A2A] rounded-[6px] shadow-lg whitespace-nowrap">
          {description}
        </div>
      )}
    </div>
  );
};

// Field Label Component
export function FieldLabel({ children }) {
  return <label className="mb-2 block text-[13px] text-[#94A3B8]">{children}</label>;
}

const CheckIcon = () => (
  <svg
    className="w-4 h-4"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="3"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20 6L9 17L4 12" />
  </svg>
); 

// Main Configuration Component
const Configuration = () => {
  // State for active preset
  const [activePreset, setActivePreset] = useState('balanced');
  
  // State for system configuration (committed state)
  const [customConfig, setCustomConfig] = useState({
    t: PRESETS.balanced.t,
    r: PRESETS.balanced.r,
    cap: PRESETS.balanced.cap,
    interval: PRESETS.balanced.interval
  });

  // Staging state for draft configuration (user input)
  const [draftConfig, setDraftConfig] = useState({
    t: PRESETS.balanced.t,
    r: PRESETS.balanced.r,
    cap: PRESETS.balanced.cap,
    interval: PRESETS.balanced.interval
  });

  // State for validation errors and success messages
  const [errorMessage, setErrorMessage] = useState('');
  const [applySaved, setApplySaved] = useState(false);
  const [resetSaved, setResetSaved] = useState(false);

  // Parameter descriptions
  const parameterDescriptions = {
    t: 'Trigger Threshold: Max messages before compression.',
    r: 'Raw Buffer: Recent messages preserved intact.',
    cap: 'Token Cap: Max tokens for summary.',
    interval: 'Grounding Interval: Epochs between grounding passes.'
  };

  // Load saved configuration from sessionStorage on mount
  useEffect(() => {
    const savedConfig = sessionStorage.getItem('agent_memory_config');
    if (savedConfig) {
      try {
        const parsedConfig = JSON.parse(savedConfig);
        if (parsedConfig.preset && PRESETS[parsedConfig.preset]) {
          setActivePreset(parsedConfig.preset);
          setCustomConfig(PRESETS[parsedConfig.preset]);
          setDraftConfig(PRESETS[parsedConfig.preset]);
        } else if (parsedConfig.preset === 'custom' && parsedConfig.config) {
          setActivePreset('custom');
          setCustomConfig(parsedConfig.config);
          setDraftConfig(parsedConfig.config);
        }
      } catch (error) {
        console.error('Failed to parse saved configuration:', error);
      }
    }
  }, []);

  // Save configuration to sessionStorage
  const saveConfigToSession = (preset, config) => {
    sessionStorage.setItem('agent_memory_config', JSON.stringify({ preset, config }));
  };

  // Handle preset selection
  const handlePresetChange = (preset) => {
    const newConfig = PRESETS[preset];
    setActivePreset(preset);
    setCustomConfig(newConfig);
    setDraftConfig(newConfig);
    saveConfigToSession(preset, newConfig);
    setErrorMessage('');
    setApplySaved(true);
    setTimeout(() => setApplySaved(false), 2000);
  };

  // Handle draft configuration changes (for sliders)
  const handleDraftChange = (key, value) => {
    setDraftConfig(prev => ({
      ...prev,
      [key]: Number(value)
    }));
  };

  // Validate custom configuration
  const validateCustomConfig = (config) => {
    const t = Number(config.t);
    const r = Number(config.r);
    
    // Type integrity check
    if (isNaN(t) || isNaN(r)) {
      setErrorMessage('All entries must be valid integers.');
      return false;
    }

    // Floor limits check
    if (t < 10) {
      setErrorMessage('Trigger Threshold (T) must be ≥ 10.');
      return false;
    }
    if (r < 2) {
      setErrorMessage('Raw Buffer (R) must be ≥ 2.');
      return false;
    }

    // Dominance rule check
    if (t <= r) {
      setErrorMessage('Trigger Threshold (T) must be strictly greater than Raw Buffer (R).');
      return false;
    }

    // Processing efficiency window check
    if ((t - r) < 5) {
      setErrorMessage('The difference (T - R) must be at least 5 messages.');
      return false;
    }

    return true;
  };

  // Apply custom configuration
  const handleApplyCustomConfig = () => {
    if (validateCustomConfig(draftConfig)) {
      setCustomConfig(draftConfig);
      setActivePreset('custom');
      saveConfigToSession('custom', draftConfig);
      setErrorMessage('');
      setApplySaved(true);
      setTimeout(() => setApplySaved(false), 2000);
    }
  };
 
  // Reset to active preset
  const handleResetToPreset = () => {
    const fallbackPreset = PRESETS[activePreset]
        ? activePreset
        : 'balanced';

    const presetConfig = PRESETS[fallbackPreset];

    setActivePreset(fallbackPreset);
    setDraftConfig(presetConfig);
    setCustomConfig(presetConfig);

    setErrorMessage('');

    setResetSaved(true);
    setTimeout(() => setResetSaved(false), 2000);
  };

  return (
    <div>
      {/* Header Outside the Box */}
      <div className="mb-4">
        <h1 className="text-[#E8E8E8] text-[20px] font-medium">Configuration</h1>
        <p className="text-[#94A3B8] text-[13px] mt-1">Adjust your mathematical parameters below</p>
      </div>

      {/* Main Card */}
      <div className="rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6">
        
        {/* Error and Success Messages */}
        {errorMessage && (
          <div className="mb-4 p-3 bg-[#FF4444] bg-opacity-20 border border-[#FF4444] rounded-[6px]">
            <p className="text-[#FF4444] text-[13px] font-medium">{errorMessage}</p>
          </div>
        )}
        


        {/* Presets Section */}
        <div className="mb-8">
          <FieldLabel>Presets</FieldLabel>
          <div className="flex gap-3">
            {SLIDER_MAP.map((preset) => (
              <button
                key={preset}
                onClick={() => handlePresetChange(preset)}
                className={`
                  flex h-9 items-center justify-center rounded-[8px] px-4 text-[13px] font-medium 
                  transition-all duration-200 ease-in-out
                  ${activePreset === preset 
                    ? 'border border-[#6366F1] bg-[#1A1A1A] text-[#E8E8E8] shadow-[0_0_8px_rgba(99,102,241,0.2)]' 
                    : 'border border-[#2A2A2A] bg-transparent text-[#94A3B8] hover:border-[#3A3A3A] hover:text-[#E8E8E8] hover:bg-[#141414]'
                  }
                `}
              >
                {preset.charAt(0).toUpperCase() + preset.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Configuration Section */}
        <div>
          <FieldLabel>Custom Configuration</FieldLabel>
          
          {/* Configuration Grid */}
          <div className="grid grid-cols-2 gap-5">
            {Object.entries(draftConfig).map(([key, value]) => (
              <div key={key} className="space-y-2">
                <div className="flex justify-between items-center">
                  <ParameterTooltip
                    parameter={key}
                    description={parameterDescriptions[key]}
                  />
                  <span className="text-[#E8E8E8] text-[13px] font-medium">{draftConfig[key]}</span>
                </div>
                <input
                  type="range"
                  min={key === 't' ? 10 : key === 'r' ? 2 : key === 'cap' ? 100 : 1}
                  max={key === 't' ? 50 : key === 'r' ? 20 : key === 'cap' ? 2000 : 10}
                  value={value}
                  onChange={(e) => handleDraftChange(key, e.target.value)}
                  className="w-full h-1.5 bg-[#2A2A2A] rounded-[6px] appearance-none cursor-pointer accent-[#6366F1] hover:accent-[#4F46E5] transition-all duration-200"
                />
              </div>
            ))}
          </div>

          {/* Apply and Reset Buttons */}
          <div className="flex gap-3 mt-4">
            <button
                onClick={handleApplyCustomConfig}
                className="flex-1 h-9 rounded-[8px] border border-[#6366F1] bg-[#1A1A1A] px-4 text-[13px] text-[#E8E8E8] transition-all duration-200 hover:bg-[#6366F1] hover:text-[#FFFFFF] flex items-center justify-center gap-2"
                >
                {applySaved ? (
                    <>
                    <CheckIcon />
                    Saved
                    </>
                ) : (
                    'Apply Custom Config'
                )}
                </button>
            <button
              onClick={handleResetToPreset}
              className="flex-1 h-9 rounded-[8px] border border-[#2A2A2A] bg-transparent px-4 text-[13px] text-[#94A3B8] transition-all duration-200 hover:border-[#6366F1] hover:text-[#E8E8E8] hover:bg-[#141414] flex items-center justify-center gap-2"
            >
              {resetSaved ? (
                <>
                <CheckIcon />
                Reset
                </>
              ) : (
                <>Reset to {activePreset} Preset</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Configuration;