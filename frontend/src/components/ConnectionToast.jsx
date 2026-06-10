export default function ConnectionToast({ state }) {
  if (!state || state === 'connected') {
    return null;
  }

  const isReconnected = state === 'reconnected';

  return (
    <div className="pointer-events-none absolute left-1/2 top-4 z-50 -translate-x-1/2 connection-toast-fade">
      <div
        className={`flex items-center gap-2 rounded-[8px] border bg-[#1A1A1A] px-4 py-2.5 shadow-[0_12px_28px_rgba(0,0,0,0.28)] ${
          isReconnected ? 'border-[#22C55E]' : 'border-[#EF4444]'
        }`}
      >
        <span
          className={`h-2 w-2 rounded-full ${
            isReconnected ? 'bg-[#22C55E]' : 'bg-[#EF4444] connection-dot-pulse'
          }`}
        />
        <span className={`whitespace-nowrap text-[13px] ${isReconnected ? 'text-[#22C55E]' : 'text-[#E8E8E8]'}`}>
          {isReconnected ? 'Reconnected' : 'Backend connection lost. Retrying...'}
        </span>
      </div>
    </div>
  );
}
