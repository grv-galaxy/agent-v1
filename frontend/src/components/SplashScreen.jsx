function SplashIcon({ type = 'spark', className = 'h-7 w-7' }) {
  const common = {
    fill: 'none',
    stroke: 'currentColor',
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    strokeWidth: '1.8',
  };

  const paths = {
    spark: (
      <>
        <path d="M12 3.5 13.8 9 19 11l-5.2 2L12 18.5 10.2 13 5 11l5.2-2Z" {...common} />
        <path d="M5.5 4.8v3M4 6.3h3M18.5 15.5v2.4M17.3 16.7h2.4" {...common} />
      </>
    ),
    check: <path d="m5 12 4 4 10-10" {...common} />,
    warning: (
      <>
        <path d="M12 4 3.5 18h17Z" {...common} />
        <path d="M12 9v4" {...common} />
        <path d="M12 16h.01" {...common} />
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
      {paths[type]}
    </svg>
  );
}

function ConnectingDots() {
  return (
    <span className="inline-flex items-center gap-1">
      <span>Connecting</span>
      <span className="splash-dot">.</span>
      <span className="splash-dot splash-dot-delay-1">.</span>
      <span className="splash-dot splash-dot-delay-2">.</span>
    </span>
  );
}

function SplashButton({ children, variant = 'primary', onClick }) {
  const className =
    variant === 'primary'
      ? 'bg-[#6366F1] text-white hover:bg-[#4F46E5]'
      : 'border border-[#2A2A2A] bg-transparent text-[#E8E8E8] hover:border-[#3A3A3A]';

  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-9 rounded-[8px] px-5 text-[13px] transition duration-150 ${className}`}
    >
      {children}
    </button>
  );
}

export default function SplashScreen({ state, exiting = false, onRetry, onEnterManually }) {
  const isBackendError = state === 'backend-error';
  const isOffline = state === 'offline';
  const isSuccess = state === 'success';
  const isRedirecting = state === 'redirecting';
  const isChecking = state === 'checking';

  const statusText = isChecking
    ? 'Loading your configuration'
    : isSuccess
      ? 'Ready'
      : isRedirecting
        ? 'Setting up for first time'
        : '';

  if (isBackendError || isOffline) {
    return (
      <main
        className={`grid min-h-screen place-items-center bg-[#0D0D0D] px-5 transition-opacity duration-200 ${
          exiting ? 'opacity-0' : 'opacity-100'
        }`}
      >
        <section className="flex max-w-[420px] flex-col items-center text-center">
          <div className="grid h-14 w-14 place-items-center rounded-[14px] text-[#EF4444]">
            <SplashIcon type={isOffline ? 'wifiOff' : 'warning'} className={isOffline ? 'h-8 w-8' : 'h-9 w-9'} />
          </div>
          <h1 className="mt-4 text-[16px] font-semibold text-[#E8E8E8]">
            {isOffline ? 'No internet connection' : 'Cannot reach backend'}
          </h1>
          <p className="mt-2 text-[13px] leading-5 text-[#666666]">
            {isOffline
              ? 'Connect to the internet to continue'
              : 'Make sure the backend server is running on port 8000'}
          </p>
          <div className="mt-6 flex flex-wrap justify-center gap-3">
            <SplashButton onClick={onRetry}>Retry</SplashButton>
            {isBackendError ? (
              <SplashButton variant="secondary" onClick={onEnterManually}>
                Enter manually
              </SplashButton>
            ) : null}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main
      className={`grid min-h-screen place-items-center bg-[#0D0D0D] px-5 transition-opacity duration-200 ${
        exiting ? 'opacity-0' : 'opacity-100'
      }`}
    >
      <section className="flex flex-col items-center text-center">
        <div className="grid h-14 w-14 place-items-center rounded-[14px] bg-[#6366F1] text-white shadow-[0_0_36px_rgba(99,102,241,0.22)] splash-logo-pulse">
          <SplashIcon type="spark" />
        </div>
        <h1 className="mt-4 text-[18px] font-semibold text-[#E8E8E8]">Agent</h1>
        <div
          className={`mt-2 flex h-5 items-center gap-1 text-[13px] transition-opacity duration-300 ${
            isSuccess ? 'text-[#22C55E]' : 'text-[#666666]'
          }`}
        >
          {state === 'connecting' ? <ConnectingDots /> : <span>{statusText}</span>}
          {isSuccess ? (
            <SplashIcon type="check" className="splash-check-scale h-4 w-4 text-[#22C55E]" />
          ) : null}
        </div>
      </section>
    </main>
  );
}
