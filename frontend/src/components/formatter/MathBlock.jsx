import { BlockMath, InlineMath } from 'react-katex';
import 'katex/dist/katex.min.css';

export default function MathBlock({ math, displayMode = false }) {
  if (!math) {
    return null;
  }

  const fallback = (
    <code className="rounded bg-[#1A1A1A] px-1 py-0.5 font-mono text-[0.92em] text-[#E8E8E8]">
      {displayMode ? `$$${math}$$` : `$${math}$`}
    </code>
  );

  if (displayMode) {
    return (
      <div className="my-4 w-full overflow-x-auto rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-4">
        <BlockMath math={math} errorColor="#fca5a5" renderError={() => fallback} />
      </div>
    );
  }

  return <InlineMath math={math} errorColor="#fca5a5" renderError={() => fallback} />;
}
