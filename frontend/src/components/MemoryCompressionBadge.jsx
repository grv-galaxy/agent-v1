function BrainIcon() {
  return (
    <svg viewBox="0 0 16 16" className="h-3 w-3 text-[#6366F1]" aria-hidden="true">
      <path
        d="M6 3.5a2.2 2.2 0 0 0-2.1 2.8 2.3 2.3 0 0 0 .2 4.3A2.2 2.2 0 0 0 8 12V4.2a2 2 0 0 0-2-0.7Zm4 0a2 2 0 0 0-2 0.7V12a2.2 2.2 0 0 0 3.9-1.4 2.3 2.3 0 0 0 .2-4.3A2.2 2.2 0 0 0 10 3.5Z"
        fill="none"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.6"
      />
    </svg>
  );
}

export default function MemoryCompressionBadge({ visible }) {
  if (!visible) {
    return null;
  }

  return (
    <div className="memory-compression-badge mt-3 inline-flex items-center gap-1.5 rounded-full border border-[#2A2A2A] bg-[#1A1A1A] px-[10px] py-1 text-[12px] text-[#A0A0A0]">
      <BrainIcon />
      <span>Memory compressed</span>
    </div>
  );
}

