import { Component, memo, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import CodeBlock from './formatter/CodeBlock.jsx';
import MathBlock from './formatter/MathBlock.jsx';
import ThinkBlock from './formatter/ThinkBlock.jsx';

const safeSchema = {
  ...defaultSchema,
  tagNames: [
    ...new Set([
      ...(defaultSchema.tagNames || []),
      'a',
      'b',
      'blockquote',
      'br',
      'code',
      'div',
      'em',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'i',
      'input',
      'li',
      'ol',
      'p',
      'pre',
      'span',
      'strong',
      'table',
      'tbody',
      'td',
      'th',
      'thead',
      'tr',
      'ul',
    ]),
  ],
  attributes: {
    ...defaultSchema.attributes,
    a: [
      ...(defaultSchema.attributes?.a || []),
      'href',
      'title',
      'target',
      'rel',
    ],
    code: [...(defaultSchema.attributes?.code || []), 'className'],
    div: [
      ...(defaultSchema.attributes?.div || []),
      'className',
      'dataMathDisplay',
      'dataMathId',
      'data-math-display',
      'data-math-id',
    ],
    input: ['checked', 'disabled', 'type'],
    span: [
      ...(defaultSchema.attributes?.span || []),
      'className',
      'dataMathDisplay',
      'dataMathId',
      'data-math-display',
      'data-math-id',
    ],
    td: [...(defaultSchema.attributes?.td || []), 'align'],
    th: [...(defaultSchema.attributes?.th || []), 'align'],
  },
  protocols: {
    ...defaultSchema.protocols,
    href: ['http', 'https', 'mailto'],
  },
};

class FormatterBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidUpdate(previousProps) {
    if (previousProps.content !== this.props.content && this.state.hasError) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <pre className="my-4 w-full whitespace-pre-wrap rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-4 font-mono text-[13px] leading-6 text-[#E8E8E8]">
          {this.props.content}
        </pre>
      );
    }

    return this.props.children;
  }
}

function extractThinkBlocks(value) {
  const reasoning = [];
  let main = value.replace(/<think>([\s\S]*?)<\/think>/gi, (_match, content) => {
    reasoning.push(content.trim());
    return '';
  });

  main = main.replace(/<think>([\s\S]*)$/i, (_match, content) => {
    reasoning.push(content.trim());
    return '';
  });

  return {
    main,
    reasoning: reasoning.filter(Boolean),
  };
}

function hasClearLatexMarker(value) {
  return (
    /\\(?:frac|times|approx|text|sqrt|sum|int|left|right)\b/.test(value) ||
    /[A-Za-z0-9)}\]]\s*[\^_]\s*(?:\{[^}]+\}|[A-Za-z0-9]+)/.test(value)
  );
}

function isMarkdownLinkTarget(source, indexAfterBracket) {
  return source[indexAfterBracket] === '(';
}

function transformMath(value) {
  const mathItems = [];
  const protectedSegments = [];

  function protectMarkdownCode(source) {
    return source.replace(/```[\s\S]*?(?:```|$)|`[^`\n]*`/g, (segment) => {
      const id = protectedSegments.push(segment) - 1;
      return `@@__FORMATTER_PROTECTED_${id}__@@`;
    });
  }

  function restoreProtectedSegments(source) {
    return source.replace(/@@__FORMATTER_PROTECTED_(\d+)__@@/g, (_match, id) => {
      return protectedSegments[Number(id)] || '';
    });
  }

  function createPlaceholder(math, displayMode) {
    const id = mathItems.push({ math: math.trim(), displayMode }) - 1;
    if (displayMode) {
      return `<div data-math-id="${id}" data-math-display="block"></div>`;
    }

    return `<span data-math-id="${id}" data-math-display="inline"></span>`;
  }

  let transformed = protectMarkdownCode(value).replace(/\$\$([\s\S]+?)\$\$/g, (_match, math) => {
    return createPlaceholder(math, true);
  });

  transformed = transformed.replace(/\\\[([\s\S]+?)\\\]/g, (_match, math) => {
    return createPlaceholder(math, true);
  });

  transformed = transformed.replace(/\\\(([\s\S]+?)\\\)/g, (_match, math) => {
    return createPlaceholder(math, false);
  });

  transformed = transformed.replace(/(^|[^\\$])\$([^\n$]+?)\$/g, (_match, prefix, math) => {
    return `${prefix}${createPlaceholder(math, false)}`;
  });

  transformed = transformed.replace(/(^|[^\\\]])\[([\s\S]+?)\]/g, (match, prefix, math, offset, source) => {
    const indexAfterBracket = offset + match.length;

    if (isMarkdownLinkTarget(source, indexAfterBracket) || !hasClearLatexMarker(math)) {
      return match;
    }

    return `${prefix}${createPlaceholder(math, true)}`;
  });

  return {
    markdown: restoreProtectedSegments(transformed),
    mathItems,
  };
}

function getMathProps(node) {
  const props = node?.properties || {};
  const id = props.dataMathId ?? props['data-math-id'];
  const display = props.dataMathDisplay ?? props['data-math-display'];

  return {
    id: typeof id === 'string' ? Number(id) : id,
    displayMode: display === 'block',
  };
}

function getLanguage(className) {
  const match = /language-([\w-]+)/.exec(className || '');
  return match?.[1] || 'text';
}

function getStructuredBlock(value) {
  const text = value.trim();

  if (!text) {
    return null;
  }

  if (/^[{[]/.test(text)) {
    try {
      JSON.parse(text);
      return { language: 'json', code: text };
    } catch {
      // Incomplete streamed JSON should continue rendering as regular markdown.
    }
  }

  if (/^(?:<!doctype\s+html|<\?xml|<[\w:-]+(?:\s[^>]*)?>[\s\S]*<\/[\w:-]+>)\s*$/i.test(text)) {
    return {
      language: text.toLowerCase().startsWith('<?xml') ? 'xml' : 'html',
      code: text,
    };
  }

  return null;
}

async function openExternalLink(href) {
  try {
    const parsedUrl = new URL(href, window.location.href);

    if (!['http:', 'https:', 'mailto:'].includes(parsedUrl.protocol)) {
      return;
    }

    if (parsedUrl.protocol !== 'mailto:' && window.desktop?.openExternal) {
      const opened = await window.desktop.openExternal(parsedUrl.toString());
      if (opened) {
        return;
      }
    }

    window.open(parsedUrl.toString(), '_blank', 'noopener,noreferrer');
  } catch {
    // Ignore malformed or unsupported links.
  }
}

function StreamingCursor() {
  return (
    <span className="ml-1 inline-block h-4 w-[2px] animate-pulse bg-[#E8E8E8] align-middle" />
  );
}

function MessageFormatter({ content = '', isStreaming = false }) {
  const trimmedContent = content.trim();

  const parsed = useMemo(() => {
    const { main, reasoning } = extractThinkBlocks(content);
    const { markdown, mathItems } = transformMath(main);

    return {
      markdown,
      mathItems,
      reasoning,
    };
  }, [content]);
  const structuredBlock = getStructuredBlock(parsed.markdown);

  if (!trimmedContent) {
    return isStreaming ? <StreamingCursor /> : null;
  }

  return (
    <FormatterBoundary content={content}>
      <div className="message-formatter text-[15px] leading-[1.7] text-[#E8E8E8]">
        {parsed.reasoning.map((reasoning, index) => (
          <ThinkBlock key={`${index}-${reasoning.slice(0, 16)}`}>{reasoning}</ThinkBlock>
        ))}

        {structuredBlock ? (
          <CodeBlock code={structuredBlock.code} language={structuredBlock.language} />
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw, [rehypeSanitize, safeSchema]]}
            components={{
            a({ href, children }) {
              return (
                <a
                  href={href}
                  onClick={(event) => {
                    event.preventDefault();
                    openExternalLink(href);
                  }}
                  className="text-[#4B8BF5] underline decoration-[#4B8BF5]/40 underline-offset-4 transition duration-150 hover:text-[#8AB4FF]"
                >
                  {children}
                </a>
              );
            },
            blockquote({ children }) {
              return (
                <blockquote className="my-4 border-l-2 border-[#2A2A2A] pl-4 text-[#A0A0A0]">
                  {children}
                </blockquote>
              );
            },
            code({ inline, className, children }) {
              const text = String(children).replace(/\n$/, '');
              const isBlock = !inline && (className || text.includes('\n'));

              if (isBlock) {
                return <CodeBlock code={text} language={getLanguage(className)} />;
              }

              return (
                <code className="rounded bg-[#1A1A1A] px-1 py-0.5 font-mono text-[0.92em] text-[#E8E8E8]">
                  {children}
                </code>
              );
            },
            div({ node, children, ...props }) {
              const math = getMathProps(node);
              if (Number.isInteger(math.id) && parsed.mathItems[math.id]) {
                return (
                  <MathBlock
                    math={parsed.mathItems[math.id].math}
                    displayMode={parsed.mathItems[math.id].displayMode}
                  />
                );
              }

              return <div {...props}>{children}</div>;
            },
            h1({ children }) {
              return <h1 className="mb-4 mt-1 text-[24px] font-semibold leading-tight text-[#E8E8E8]">{children}</h1>;
            },
            h2({ children }) {
              return <h2 className="mb-3 mt-5 text-[21px] font-semibold leading-tight text-[#E8E8E8]">{children}</h2>;
            },
            h3({ children }) {
              return <h3 className="mb-2 mt-5 text-[18px] font-semibold leading-snug text-[#E8E8E8]">{children}</h3>;
            },
            h4({ children }) {
              return <h4 className="mb-2 mt-4 text-[16px] font-semibold leading-snug text-[#E8E8E8]">{children}</h4>;
            },
            h5({ children }) {
              return <h5 className="mb-2 mt-4 text-[14px] font-semibold leading-snug text-[#E8E8E8]">{children}</h5>;
            },
            h6({ children }) {
              return (
                <h6 className="mb-2 mt-3 text-xs font-semibold uppercase tracking-wide text-[#A0A0A0]">
                  {children}
                </h6>
              );
            },
            hr() {
              return <hr className="my-5 border-[#2A2A2A]" />;
            },
            input(props) {
              return (
                <input
                  {...props}
                  disabled
                  className="mr-2 h-3.5 w-3.5 rounded border-[#2A2A2A] bg-[#12141C] align-middle"
                />
              );
            },
            li({ children }) {
              return <li className="my-1 pl-1">{children}</li>;
            },
            ol({ children }) {
              return <ol className="my-4 list-decimal space-y-1 pl-5">{children}</ol>;
            },
            p({ children }) {
              return <p className="my-4 first:mt-0 last:mb-0">{children}</p>;
            },
            pre({ children }) {
              return <>{children}</>;
            },
            span({ node, children, ...props }) {
              const math = getMathProps(node);
              if (Number.isInteger(math.id) && parsed.mathItems[math.id]) {
                return (
                  <MathBlock
                    math={parsed.mathItems[math.id].math}
                    displayMode={parsed.mathItems[math.id].displayMode}
                  />
                );
              }

              return <span {...props}>{children}</span>;
            },
            table({ children }) {
              return (
                <div className="my-4 w-full overflow-x-auto rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] p-4">
                  <table className="w-full border-collapse text-left text-sm">{children}</table>
                </div>
              );
            },
            tbody({ children }) {
              return <tbody className="[&_tr:nth-child(even)]:bg-[#12141C] [&_tr:nth-child(odd)]:bg-[#0D0D0D]">{children}</tbody>;
            },
            td({ children }) {
              return <td className="border border-[#2A2A2A] p-3 align-top text-[#D6D6D6]">{children}</td>;
            },
            th({ children }) {
              return (
                <th className="border border-[#2A2A2A] bg-[#1A1D27] p-3 text-left font-semibold text-[#6366F1]">
                  {children}
                </th>
              );
            },
            ul({ children }) {
              return <ul className="my-4 list-disc space-y-1 pl-5">{children}</ul>;
            },
            }}
          >
            {parsed.markdown}
          </ReactMarkdown>
        )}

        {isStreaming ? <StreamingCursor /> : null}
      </div>
    </FormatterBoundary>
  );
}

export default memo(MessageFormatter);
