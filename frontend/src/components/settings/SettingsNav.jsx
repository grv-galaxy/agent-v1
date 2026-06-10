const PERSONAL_ITEMS = [
  { id: 'general', label: 'General', icon: 'gear' },
  { id: 'profile', label: 'Profile', icon: 'person' },
  { id: 'appearance', label: 'Appearance', icon: 'sun' },
  { id: 'configuration', label: 'Configuration', icon: 'sliders' },
  { id: 'personalization', label: 'Personalization', icon: 'sparkle' },
  { id: 'keyboard', label: 'Keyboard shortcuts', icon: 'keyboard' },
  { id: 'billing', label: 'Usage and billing', icon: 'card' },
];

const INTEGRATION_ITEMS = [
  { id: 'mcp', label: 'MCP servers', icon: 'plug' },
  { id: 'browser', label: 'Browser', icon: 'globe' },
  { id: 'computer', label: 'Computer use', icon: 'monitor' },
];

const TOOL_ITEMS = [
  { id: 'search-tool', label: 'Search tool', icon: 'search', disabled: true },
  { id: 'code-executor', label: 'Code executor', icon: 'terminal', disabled: true },
  { id: 'memory', label: 'Memory', icon: 'brain' },
];

function SettingsIcon({ name, className = 'h-4 w-4' }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    strokeWidth: '1.6',
  };

  const paths = {
    arrowLeft: <path d="M10 4 6 8l4 4M6.5 8H14" {...common} />,
    search: (
      <>
        <circle cx="7" cy="7" r="3.8" {...common} />
        <path d="m10 10 2.8 2.8" {...common} />
      </>
    ),
    gear: (
      <>
        <circle cx="8" cy="8" r="2.1" {...common} />
        <path d="M8 1.8v1.5M8 12.7v1.5M2.6 4.9l1.3.8M12.1 10.3l1.3.8M2.6 11.1l1.3-.8M12.1 5.7l1.3-.8" {...common} />
      </>
    ),
    person: (
      <>
        <circle cx="8" cy="5.4" r="2.2" {...common} />
        <path d="M3.8 13.4c.7-2.1 2.2-3.1 4.2-3.1s3.5 1 4.2 3.1" {...common} />
      </>
    ),
    sun: (
      <>
        <circle cx="8" cy="8" r="2.5" {...common} />
        <path d="M8 1.8v1.2M8 13v1.2M1.8 8h1.2M13 8h1.2M3.6 3.6l.9.9M11.5 11.5l.9.9M12.4 3.6l-.9.9M4.5 11.5l-.9.9" {...common} />
      </>
    ),
    sliders: (
      <>
        <path d="M3 4.5h5M11 4.5h2M3 8h2M8 8h5M3 11.5h6M12 11.5h1" {...common} />
        <circle cx="9.5" cy="4.5" r="1.2" {...common} />
        <circle cx="6.5" cy="8" r="1.2" {...common} />
        <circle cx="10.5" cy="11.5" r="1.2" {...common} />
      </>
    ),
    sparkle: (
      <>
        <path d="M8 2.5 9.2 6 12.5 8 9.2 10 8 13.5 6.8 10 3.5 8 6.8 6 8 2.5Z" {...common} />
        <path d="M12.5 2.5v2M11.5 3.5h2" {...common} />
      </>
    ),
    keyboard: (
      <>
        <rect x="2.5" y="4.2" width="11" height="7.6" rx="1.4" {...common} />
        <path d="M4.5 6.5h.1M6.8 6.5h.1M9.1 6.5h.1M11.4 6.5h.1M4.5 9h.1M6.8 9h2.8M11.4 9h.1" {...common} />
      </>
    ),
    card: (
      <>
        <rect x="2.5" y="4" width="11" height="8" rx="1.4" {...common} />
        <path d="M2.5 6.5h11M4.5 9.5h2.5" {...common} />
      </>
    ),
    plug: (
      <path d="M6 2.8v3.1M10 2.8v3.1M4.5 6h7v2.5a3.5 3.5 0 0 1-7 0V6Zm3.5 6v1.7" {...common} />
    ),
    globe: (
      <>
        <circle cx="8" cy="8" r="5.3" {...common} />
        <path d="M2.9 8h10.2M8 2.7c1.4 1.4 2.1 3.2 2.1 5.3S9.4 11.9 8 13.3M8 2.7C6.6 4.1 5.9 5.9 5.9 8s.7 3.9 2.1 5.3" {...common} />
      </>
    ),
    monitor: (
      <>
        <rect x="2.5" y="3.8" width="11" height="7.5" rx="1.2" {...common} />
        <path d="M6 13.2h4M8 11.3v1.9" {...common} />
      </>
    ),
    terminal: (
      <>
        <path d="m4.2 5.5 2.1 2.1-2.1 2.1M7.8 10.2h3.8" {...common} />
        <rect x="2.5" y="3.5" width="11" height="9" rx="1.4" {...common} />
      </>
    ),
    brain: (
      <path d="M6 3.5a2.2 2.2 0 0 0-2.1 2.8 2.3 2.3 0 0 0 .2 4.3A2.2 2.2 0 0 0 8 12V4.2a2 2 0 0 0-2-0.7Zm4 0a2 2 0 0 0-2 0.7V12a2.2 2.2 0 0 0 3.9-1.4 2.3 2.3 0 0 0 .2-4.3A2.2 2.2 0 0 0 10 3.5Z" {...common} />
    ),
  };

  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function SectionLabel({ children }) {
  return (
    <p className="px-4 pb-2 pt-4 text-[11px] font-medium uppercase tracking-wide text-[#555555]">
      {children}
    </p>
  );
}

function NavItem({ item, active, onSelect }) {
  return (
    <button
      type="button"
      disabled={item.disabled}
      onClick={() => !item.disabled && onSelect(item.id)}
      className={`mx-3 flex h-9 w-[calc(100%-24px)] items-center gap-2.5 rounded-[6px] px-3 text-left text-[14px] transition duration-150 ${
        item.disabled
          ? 'cursor-not-allowed text-[#444444]'
          : active
            ? 'bg-[#1A1A1A] text-[#E8E8E8]'
            : 'text-[#888888] hover:bg-[#141414] hover:text-[#E8E8E8]'
      }`}
    >
      <SettingsIcon name={item.icon} className="h-4 w-4 shrink-0" />
      <span className="truncate">{item.label}</span>
    </button>
  );
}

export default function SettingsNav({ activeSection, onSectionChange, onBack }) {
  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-[#1F1F1F] bg-[#080808]">
      <button
        type="button"
        onClick={onBack}
        className="mx-3 mt-3 flex h-9 items-center gap-2 rounded-[6px] px-2 text-[14px] text-[#A0A0A0] transition duration-150 hover:bg-[#141414] hover:text-[#E8E8E8]"
      >
        <SettingsIcon name="arrowLeft" className="h-4 w-4" />
        Back to app
      </button>

      <div className="relative m-3">
        <SettingsIcon
          name="search"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[#555555]"
        />
        <input
          type="search"
          placeholder="Search settings..."
          className="h-8 w-full rounded-[6px] border border-[#1F1F1F] bg-[#111111] pl-9 pr-3 text-[13px] text-[#E8E8E8] outline-none placeholder:text-[#555555] focus:border-[#2A2A2A]"
        />
      </div>

      <nav className="min-h-0 flex-1 overflow-y-auto pb-4">
        <SectionLabel>Personal</SectionLabel>
        <div className="space-y-1">
          {PERSONAL_ITEMS.map((item) => (
            <NavItem
              key={item.id}
              item={item}
              active={activeSection === item.id}
              onSelect={onSectionChange}
            />
          ))}
        </div>

        <SectionLabel>Integrations</SectionLabel>
        <div className="space-y-1">
          {INTEGRATION_ITEMS.map((item) => (
            <NavItem
              key={item.id}
              item={item}
              active={activeSection === item.id}
              onSelect={onSectionChange}
            />
          ))}
        </div>

        <SectionLabel>Agent Tools</SectionLabel>
        <div className="space-y-1">
          {TOOL_ITEMS.map((item) => (
            <NavItem
              key={item.id}
              item={item}
              active={activeSection === item.id}
              onSelect={onSectionChange}
            />
          ))}
        </div>
      </nav>
    </aside>
  );
}
