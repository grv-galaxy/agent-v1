import { useEffect, useRef, useState } from 'react';
import LLMConfigCard from '../components/settings/LLMConfigCard.jsx';
import MemorySettingsCard from '../components/settings/MemorySettingsCard.jsx';
import SettingsNav from '../components/settings/SettingsNav.jsx';
import Configuration from '../components/settings/Configuration.jsx';

const PREFERENCES = [
  {
    label: 'Theme',
    description: 'Switch between dark and light mode',
  },
  {
    label: 'Font size',
    description: 'Adjust chat text size',
  },
  {
    label: 'Language',
    description: 'Change display language',
  },
];

function SectionTitle({ children }) {
  return (
    <h2 className="mb-6 border-b border-[#1F1F1F] pb-3 text-[16px] font-medium text-[#E8E8E8]">
      {children}
    </h2>
  );
}

function ComingSoonBadge() {
  return (
    <span className="shrink-0 rounded-[4px] border border-[#2A2A2A] bg-[#1A1A1A] px-2 py-0.5 text-[11px] text-[#555555]">
      Coming soon
    </span>
  );
}

function PreferencesCard() {
  return (
    <div className="rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6">
      <div className="divide-y divide-[#1F1F1F]">
        {PREFERENCES.map((item) => (
          <div key={item.label} className="flex items-center justify-between gap-4 py-4 first:pt-0 last:pb-0">
            <div className="min-w-0">
              <p className="text-[14px] font-medium text-[#E8E8E8]">{item.label}</p>
              <p className="mt-1 text-[13px] text-[#666666]">{item.description}</p>
            </div>
            <ComingSoonBadge />
          </div>
        ))}
      </div>
    </div>
  );
}

function PlaceholderSection({ title }) {
  return (
    <div>
      <h1 className="mb-8 text-[24px] font-semibold text-[#E8E8E8]">{title}</h1>
      <div className="rounded-[10px] border border-[#1F1F1F] bg-[#111111] p-6">
        <p className="text-[14px] text-[#666666]">Coming soon</p>
      </div>
    </div>
  );
}

function SettingsIcon({ name, className = 'h-4 w-4' }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    strokeWidth: '1.6',
  };

  const paths = {
    minimize: <path d="M4 8h8" {...common} />,
    maximize: <path d="M4.3 4.3h7.4v7.4H4.3z" {...common} />,
    close: (
      <>
        <path d="m4.6 4.6 6.8 6.8" {...common} />
        <path d="m11.4 4.6-6.8 6.8" {...common} />
      </>
    ),
  };

  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function callDesktopHandler(...handlerNames) {
  const desktop = window.desktop;
  const handlerName = handlerNames.find((name) => typeof desktop?.[name] === 'function');
  desktop?.[handlerName]?.();
}

function WindowControlButton({ label, icon, onClick, danger = false }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className={`no-drag grid h-7 w-7 place-items-center rounded-[6px] text-[#666666] transition duration-150 hover:text-[#E8E8E8] ${
        danger ? 'hover:bg-[#FF4444] hover:text-white' : 'hover:bg-[#1A1A1A]'
      }`}
    >
      <SettingsIcon name={icon} />
    </button>
  );
}

export default function SettingsPage({
  onBack,
  onConfigSaved,
  onMemoryConfigSaved,
  isOnline = true,
  onBackendConnectionLost,
}) {
  const [activeSection, setActiveSection] = useState('general');
  const llmConfigFetchedRef = useRef(false);
  const memoryConfigFetchedRef = useRef(false);
  const memoryStatsFetchedRef = useRef(false);

  useEffect(() => {
    llmConfigFetchedRef.current = false;
    memoryConfigFetchedRef.current = false;
    memoryStatsFetchedRef.current = false;
  }, []);

  const activeTitle =
    {
      profile: 'Profile',
      appearance: 'Appearance',
      configuration: 'Configuration',
      personalization: 'Personalization',
      keyboard: 'Keyboard shortcuts',
      billing: 'Usage and billing',
      mcp: 'MCP servers',
      browser: 'Browser',
      computer: 'Computer use',
      memory: 'Memory',
    }[activeSection] || 'General';

  return (
    <div className="flex h-full min-h-0 animate-[settingsSlideIn_200ms_ease-out] bg-[#0D0D0D]">
      <SettingsNav
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        onBack={onBack}
      />

      <section className="flex min-w-0 flex-1 flex-col bg-[#0D0D0D]">
        <header className="drag-region flex h-12 shrink-0 items-center justify-between border-b border-[#1F1F1F] bg-[#111111] px-4">
          <p className="truncate text-[14px] text-[#E8E8E8]">Settings</p>
          <div className="flex shrink-0 items-center gap-1">
            <WindowControlButton
              label="Minimize"
              icon="minimize"
              onClick={() => callDesktopHandler('minimizeWindow', 'minimize')}
            />
            <WindowControlButton
              label="Maximize"
              icon="maximize"
              onClick={() => callDesktopHandler('toggleMaximizeWindow', 'maximize')}
            />
            <WindowControlButton
              label="Close"
              icon="close"
              danger
              onClick={() => callDesktopHandler('closeWindow', 'close')}
            />
          </div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-16 py-12 max-[900px]:px-8 max-[640px]:px-5">
          {activeSection === 'general' ? (
            <div className="max-w-[860px]">
              <h1 className="mb-8 text-[24px] font-semibold text-[#E8E8E8]">General</h1>

              <section>
                <SectionTitle>LLM Configuration</SectionTitle>
                <LLMConfigCard
                  onConfigSaved={onConfigSaved}
                  isOnline={isOnline}
                  onBackendConnectionLost={onBackendConnectionLost}
                  configFetchGuardRef={llmConfigFetchedRef}
                />
              </section>

              <section className="mt-10">
                <SectionTitle>Preferences</SectionTitle>
                <PreferencesCard />
              </section>
            </div>
          ) : activeSection === 'memory' ? (
            <MemorySettingsCard
              isOnline={isOnline}
              onBackendConnectionLost={onBackendConnectionLost}
              onMemoryConfigSaved={onMemoryConfigSaved}
              configFetchGuardRef={memoryConfigFetchedRef}
              statsFetchGuardRef={memoryStatsFetchedRef}
            />
          ) : activeSection === 'configuration' ? (
            <Configuration /> // 🧠 Intercepts 'configuration' view to load your slider panel
          ) : (
            <PlaceholderSection title={activeTitle} />
          )}
        </div>
      </section>
    </div>
  );
}
