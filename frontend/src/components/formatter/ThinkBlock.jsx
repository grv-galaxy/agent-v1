import { useState } from 'react';

function Chevron({ open }) {
  return (
    <svg
      viewBox="0 0 16 16"
      className={`h-3.5 w-3.5 transition duration-150 ${open ? 'rotate-90' : ''}`}
      aria-hidden="true"
    >
      <path
        d="m6 4 4 4-4 4"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
    </svg>
  );
}

export default function ThinkBlock({ children }) {
  const [open, setOpen] = useState(false);
  const content = String(children || '').trim();

  if (!content) {
    return null;
  }

  return (
    <section className="mb-4 w-full rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-4">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="flex w-full items-center gap-2 text-left text-[11px] font-medium uppercase tracking-widest text-[#555555] transition duration-150 hover:text-[#8A8A8A]"
      >
        <Chevron open={open} />
        Reasoning
      </button>
      {open ? (
        <div className="mt-3 border-t border-[#2A2A2A] pt-3 text-[13px] italic leading-6 text-[#666666]">
          <pre className="whitespace-pre-wrap font-sans">{content}</pre>
        </div>
      ) : null}
    </section>
  );
}
