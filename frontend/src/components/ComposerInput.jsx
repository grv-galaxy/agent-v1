import { useEffect, useRef, useState } from 'react';

function Icon({ name, className = 'h-4 w-4' }) {
  const common = {
    className,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.8,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
  };

  const icons = {
    plus: (
      <svg {...common}>
        <path d="M12 5v14" />
        <path d="M5 12h14" />
      </svg>
    ),
    mic: (
      <svg {...common}>
        <path d="M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <path d="M12 19v3" />
      </svg>
    ),
    send: (
      <svg {...common}>
        <path d="m5 12 14-7-7 14-2-5-5-2Z" />
        <path d="m12 12 7-7" />
      </svg>
    ),
    monitor: (
      <svg {...common}>
        <rect width="18" height="12" x="3" y="4" rx="2" />
        <path d="M8 20h8" />
        <path d="M12 16v4" />
      </svg>
    ),
    git: (
      <svg {...common}>
        <path d="M6 3v12" />
        <circle cx="6" cy="5" r="2" />
        <circle cx="6" cy="17" r="2" />
        <path d="M6 7c5 0 4 5 9 5" />
        <circle cx="17" cy="12" r="2" />
      </svg>
    ),
  };

  return icons[name] || null;
}

function ContextPill({ label, icon }) {
  return (
    <span className="inline-flex h-7 items-center gap-1.5 rounded-full border border-[#1F1F1F] bg-[#111111] px-3 text-[12px] text-[#777777]">
      {icon ? <Icon name={icon} className="h-3.5 w-3.5 text-[#666666]" /> : null}
      <span className="max-w-[180px] truncate">{label}</span>
    </span>
  );
}

export default function ComposerInput({
  onSubmit,
  resetKey,
  disabled = false,
  disabledReason = '',
  contextPills = [],
  className = '',
}) {
  const [draft, setDraft] = useState('');
  const textareaRef = useRef(null);
  const canSend = draft.trim().length > 0 && !disabled;
  const showCharacterCount = draft.length > 1000;

  const resizeTextarea = () => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = '52px';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
  };

  useEffect(() => {
    resizeTextarea();
  }, [draft]);

  useEffect(() => {
    setDraft('');
  }, [resetKey]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!canSend) return;

    const trimmedDraft = draft.trim();
    const accepted = onSubmit?.(trimmedDraft);
    if (accepted === false) {
      return;
    }

    setDraft('');
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <form onSubmit={handleSubmit} className={`w-full max-w-[760px] ${className}`}>
      <div className="rounded-[12px] border border-[#2A2A2A] bg-[#1A1A1A] transition-colors duration-200 focus-within:border-[#3A3A3A]">
        <textarea
          ref={textareaRef}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onInput={resizeTextarea}
          onKeyDown={handleKeyDown}
          placeholder="Do anything"
          rows={1}
          className="block min-h-[52px] max-h-[200px] w-full resize-none overflow-hidden bg-transparent px-4 py-[14px] text-[15px] leading-6 text-[#E8E8E8] outline-none placeholder:text-[#666666]"
          style={{ height: 52 }}
        />

        <div className="flex h-11 items-center justify-between px-3 pb-3">
          <button
            type="button"
            aria-label="Attach file"
            className="grid h-8 w-8 place-items-center rounded-md text-[#777777] transition-colors duration-150 hover:bg-[#242424] hover:text-[#E8E8E8]"
          >
            <Icon name="plus" />
          </button>

          <div className="flex items-center gap-2">
            {showCharacterCount ? (
              <span className="text-[12px] tabular-nums text-[#666666]">{draft.length}</span>
            ) : null}
            <button
              type="button"
              aria-label="Voice input"
              className="grid h-8 w-8 place-items-center rounded-md text-[#777777] transition-colors duration-150 hover:bg-[#242424] hover:text-[#E8E8E8]"
            >
              <Icon name="mic" />
            </button>
            <button
              type="submit"
              aria-label="Send message"
              title={disabledReason}
              disabled={!canSend}
              className="grid h-8 w-8 place-items-center rounded-full bg-[#6366F1] text-white transition-opacity duration-150 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <Icon name="send" className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {contextPills.length > 0 ? (
        <div className="mx-auto mt-3 flex max-w-[760px] flex-wrap justify-center gap-2">
          {contextPills.map((pill) => (
            <ContextPill key={pill.label} {...pill} />
          ))}
        </div>
      ) : null}
    </form>
  );
}
