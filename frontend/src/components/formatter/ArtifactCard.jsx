import { useEffect, useMemo, useRef, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

const MIME_TYPES = {
  css: 'text/css',
  csv: 'text/csv',
  html: 'text/html',
  js: 'text/javascript',
  json: 'application/json',
  jsx: 'text/javascript',
  md: 'text/markdown',
  py: 'text/x-python',
  ts: 'text/typescript',
  tsx: 'text/typescript',
  txt: 'text/plain',
  xml: 'application/xml',
  yaml: 'application/yaml',
  yml: 'application/yaml',
};

function getExtension(filename) {
  const cleanName = filename.split(/[\\/]/).pop() || filename;
  const parts = cleanName.split('.');
  return parts.length > 1 ? parts.at(-1).toLowerCase() : 'txt';
}

function normalizeFilename(filename) {
  return (filename.split(/[\\/]/).pop() || filename).replace(/[^\w.\- ]/g, '_');
}

export function detectArtifact(code) {
  const lines = String(code || '').replace(/\r\n/g, '\n').split('\n');
  const firstContentIndex = lines.findIndex((line) => line.trim().length > 0);

  if (firstContentIndex === -1) {
    return null;
  }

  const firstLine = lines[firstContentIndex].trim();
  const filenameMatch =
    firstLine.match(/^(?:\/\/|#)\s*([\w./\\ -]+\.[A-Za-z0-9]+)\s*$/) ||
    firstLine.match(/^<!--\s*([\w./\\ -]+\.[A-Za-z0-9]+)\s*-->\s*$/);

  if (!filenameMatch) {
    return null;
  }

  const filename = normalizeFilename(filenameMatch[1]);
  const bodyLines = [...lines];
  bodyLines.splice(firstContentIndex, 1);

  return {
    filename,
    code: bodyLines.join('\n').replace(/^\n/, ''),
    extension: getExtension(filename),
  };
}

function CopyButton({ value, label = 'Copy' }) {
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
      {copied ? 'Copied' : label}
    </button>
  );
}

function FileIcon({ extension }) {
  return (
    <span className="grid h-7 w-7 place-items-center rounded-[6px] border border-[#2A2A2A] bg-[#12141C] text-[9px] font-semibold uppercase text-[#6366F1]">
      {extension.slice(0, 3)}
    </span>
  );
}

export default function ArtifactCard({ artifact, language }) {
  const mimeType = useMemo(
    () => MIME_TYPES[artifact.extension] || 'text/plain',
    [artifact.extension],
  );

  function saveFile() {
    const blob = new Blob([artifact.code], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = artifact.filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <section className="my-4 w-full overflow-hidden rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-4">
      <header className="mb-3 flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <FileIcon extension={artifact.extension} />
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-[#E8E8E8]">{artifact.filename}</p>
            <p className="text-[11px] uppercase tracking-wide text-[#666666]">
              {artifact.extension} artifact
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <CopyButton value={artifact.code} />
          <button
            type="button"
            onClick={saveFile}
            className="rounded-[6px] px-2 py-1 text-xs text-[#A0A0A0] transition duration-150 hover:bg-[#242424] hover:text-[#E8E8E8]"
          >
            Save File
          </button>
        </div>
      </header>
      <div className="overflow-x-auto rounded-[6px] bg-[#101010]">
        <SyntaxHighlighter
          language={language || artifact.extension}
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
          {artifact.code}
        </SyntaxHighlighter>
      </div>
    </section>
  );
}
