import { useEffect, useRef, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import ArtifactCard, { detectArtifact } from './ArtifactCard.jsx';

function CopyButton({ value }) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef(null);

  useEffect(
    () => () => {
      if (timeoutRef.current) {
        window.clearTimeout(timeoutRef.current);
      }
    },
    [],
  );

  async function copyValue() {
    await navigator.clipboard?.writeText(value);
    setCopied(true);
    if (timeoutRef.current) {
      window.clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = window.setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      type="button"
      onClick={copyValue}
      className="rounded-[6px] px-2 py-1 text-xs text-[#A0A0A0] transition duration-150 hover:bg-[#242424] hover:text-[#E8E8E8]"
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  );
}

export default function CodeBlock({ code, language = 'text' }) {
  const normalizedCode = String(code || '').replace(/\n$/, '');
  const artifact = detectArtifact(normalizedCode);

  if (artifact) {
    return <ArtifactCard artifact={artifact} language={language} />;
  }

  return (
    <section className="my-4 w-full overflow-hidden rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-4">
      <header className="mb-3 flex items-center justify-between">
        <span className="text-[11px] font-medium uppercase tracking-wide text-[#6366F1]">
          {language || 'text'}
        </span>
        <CopyButton value={normalizedCode} />
      </header>
      <div className="overflow-x-auto rounded-[6px] bg-[#101010]">
        <SyntaxHighlighter
          language={language || 'text'}
          style={oneDark}
          showLineNumbers
          wrapLongLines={false}
          customStyle={{
            margin: 0,
            borderRadius: 0,
            background: '#101010',
            fontSize: '13px',
          }}
          lineNumberStyle={{ color: '#666666', minWidth: '2.5em' }}
        >
          {normalizedCode}
        </SyntaxHighlighter>
      </div>
    </section>
  );
}
