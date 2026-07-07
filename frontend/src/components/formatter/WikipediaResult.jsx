import React from 'react';
import { ExternalLink, BookOpen } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

const WikipediaResult = ({ result }) => {
  if (!result) return null;
  
  if (result.error) {
    return (
      <div className="my-4 border-l-2 border-red-500 pl-4 text-red-400">
        {result.error}
      </div>
    );
  }

  const { title, url, image_url, facts, points, synthesis } = result;

  return (
    <div className="my-6 font-sans text-[#E8E8E8]">
      {/* Header - styled like a native h2 */}
      <div className="flex flex-wrap items-baseline gap-3 mb-4 mt-5">
        <h2 className="text-[21px] font-semibold leading-tight flex items-center gap-2 m-0">
          <BookOpen className="w-5 h-5 text-[#A0A0A0]" />
          {title}
        </h2>
        {url && (
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-[13px] text-[#4B8BF5] hover:text-[#8AB4FF] underline decoration-[#4B8BF5]/40 underline-offset-4 transition duration-150"
            title="Read on Wikipedia"
          >
            Read on Wikipedia
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
        )}
      </div>

      <div className="flex flex-col-reverse md:flex-row gap-6 items-start">
        {/* Left Column: Summary and Facts */}
        <div className="flex-1 min-w-0 space-y-6">
          
          {/* Summary or Synthesis - Native markdown flow */}
          {synthesis ? (
            <div className="text-[15px] leading-[1.7]">
              <ReactMarkdown
                components={{
                  p({ children }) {
                    return <p className="my-3 last:mb-0 first:mt-0">{children}</p>;
                  },
                  ul({ children }) {
                    return <ul className="my-3 list-disc pl-5 space-y-1">{children}</ul>;
                  },
                  li({ children }) {
                    return <li className="pl-1">{children}</li>;
                  },
                  strong({ children }) {
                    return <strong className="font-semibold text-[#FFFFFF]">{children}</strong>;
                  }
                }}
              >
                {synthesis}
              </ReactMarkdown>
            </div>
          ) : points && points.length > 0 ? (
            <div className="space-y-4 text-[15px] leading-[1.7]">
              {points.map((point, idx) => (
                <p key={idx} className="my-2">{point}</p>
              ))}
            </div>
          ) : null}
        </div>

        {/* Right Column: Image */}
        {image_url && (
          <div className="w-full md:w-1/3 lg:w-1/4 flex-shrink-0 flex justify-center md:justify-end mb-2 md:mb-0">
            <div className="rounded-[8px] border border-[#2A2A2A] bg-[#1A1A1A] overflow-hidden inline-block shadow-sm">
              <img 
                src={image_url} 
                alt={title} 
                className="max-w-full max-h-[280px] object-contain"
                onError={(e) => { e.target.style.display = 'none'; }}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default WikipediaResult;
