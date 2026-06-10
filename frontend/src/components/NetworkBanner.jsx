function NetworkIcon({ name, className = 'h-3.5 w-3.5' }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    strokeWidth: '1.8',
  };

  const paths = {
    wifi: (
      <>
        <path d="M2.5 8.5A15.6 15.6 0 0 1 12 5c3.6 0 6.9 1.2 9.5 3.5" {...common} />
        <path d="M6.3 12.2A9.2 9.2 0 0 1 12 10c2.1 0 4.1.8 5.7 2.2" {...common} />
        <path d="M9.9 16.2A3.6 3.6 0 0 1 12 15.5c.8 0 1.5.2 2.1.7" {...common} />
        <path d="M12 19h.01" {...common} />
      </>
    ),
    wifiOff: (
      <>
        <path d="m3 3 18 18" {...common} />
        <path d="M2.5 8.5A15.6 15.6 0 0 1 12 5c3.6 0 6.9 1.2 9.5 3.5" {...common} />
        <path d="M6.3 12.2A9.2 9.2 0 0 1 12 10c1 0 2 .2 2.9.5" {...common} />
        <path d="M9.9 16.2A3.6 3.6 0 0 1 12 15.5c.8 0 1.5.2 2.1.7" {...common} />
      </>
    ),
  };

  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      {paths[name]}
    </svg>
  );
}

function formatLostTime(value) {
  if (!value) {
    return '';
  }

  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value));
}

export default function NetworkBanner({ state = 'hidden', lostAt }) {
  if (state === 'hidden') {
    return null;
  }

  const isOnline = state === 'online';

  return (
    <div
      className={`network-banner fixed left-0 top-0 z-[1000] flex h-9 w-full items-center justify-center px-4 text-white ${
        isOnline ? 'bg-[#22C55E]' : 'bg-[#EF4444]'
      }`}
    >
      <div className="flex min-w-0 items-center gap-2">
        <NetworkIcon name={isOnline ? 'wifi' : 'wifiOff'} />
        <span className="text-[13px] font-medium">
          {isOnline ? 'Back online' : 'No internet connection'}
        </span>
      </div>
      {!isOnline ? (
        <span className="absolute right-4 text-[12px] text-white/70">
          Lost at {formatLostTime(lostAt)}
        </span>
      ) : null}
    </div>
  );
}
