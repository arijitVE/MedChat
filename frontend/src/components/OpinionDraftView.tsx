import { useState, useEffect } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import { api } from '../api';
import { Case } from '../types';

interface OpinionDraftViewProps {
  activeCase: Case;
}

export default function OpinionDraftView({
  activeCase
}: OpinionDraftViewProps) {
  const [showBanner, setShowBanner] = useState(true);
  const [opinionText, setOpinionText] = useState<string>('Loading opinion...');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isSubscribed = true;
    const fetchOpinion = async () => {
      try {
        const res = await api.getOpinion(activeCase.id);
        if (isSubscribed) {
          setOpinionText(res.opinion);
        }
      } catch (err) {
        if (isSubscribed) {
          setOpinionText('Failed to load opinion. It may still be processing.');
        }
      } finally {
        if (isSubscribed) {
          setIsLoading(false);
        }
      }
    };
    fetchOpinion();
    return () => { isSubscribed = false; };
  }, [activeCase.id]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden select-none">
      {/* Persistent safety Warning Banner at the top of the details view */}
      {showBanner && (
        <div className="bg-[#131b2e] text-[#dae2fd] px-6 py-2.5 flex items-center justify-between gap-4 border-b border-gray-800 shadow-sm z-30 select-none animate-fade-in shrink-0">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-[#fcdeb5] text-[20px]">warning</span>
            <span className="font-sans font-bold text-[10px] tracking-wider uppercase">
              AI-generated draft. Review carefully before using for legal or insurance purposes.
            </span>
          </div>
          <button
            onClick={() => setShowBanner(false)}
            className="bg-white/10 hover:bg-white/20 text-white text-[10px] font-bold px-3 py-1 rounded border border-white/20 transition-colors uppercase cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main opinion viewer canvas elements */}
      <div className="flex-1 overflow-y-auto p-8 bg-gray-50">
        <div className="max-w-4xl mx-auto space-y-6">
          
          {/* Main heading detail */}
          <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
            <div>
              <span className="inline-block font-bold text-[10px] text-gray-500 uppercase tracking-widest px-2.5 py-1 bg-white border border-gray-200 rounded mb-2 shadow-xs">
                Draft Version 1.0
              </span>
              <h2 className="font-sans text-3xl font-semibold text-black leading-tight tracking-tight">
                Preliminary Medical-Legal Opinion
              </h2>
              <p className="text-gray-500 text-xs mt-1">
                Case Ref: #{activeCase.id}
              </p>
            </div>
          </div>

          {/* Interactive Document Page Container resembling physical folder */}
          <div className="bg-white border border-gray-250 p-8 shadow-sm rounded-xl relative overflow-hidden text-gray-800 leading-relaxed font-sans text-xs min-h-[400px]">
            
            {/* Watermark/Aesthetic Background Badge matching mock perfectly */}
            <div className="absolute top-4 right-4 text-gray-100/50 select-none pointer-events-none">
              <span className="material-symbols-outlined text-[112px] opacity-25">gavel</span>
            </div>

            {/* Opinion Body */}
            <div className="space-y-4 relative z-10">
              <div>
                <h1 className="text-sm font-bold text-black border-b border-gray-200 pb-2 mb-3">
                  Clinical Opinion Draft
                </h1>
                {isLoading ? (
                  <p className="text-gray-400 italic font-sans text-xs animate-pulse">
                    Loading opinion...
                  </p>
                ) : (
                  <MarkdownRenderer content={opinionText} />
                )}
              </div>

              <div className="mt-8 pt-4 border-t border-gray-150 select-none">
                <p className="font-mono text-[10px] text-gray-400 uppercase tracking-widest">
                  End of AI Generated Draft Section
                </p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
