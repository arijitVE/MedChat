import React, { useState, useEffect } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import { ArrowRight } from 'lucide-react';
import { api } from '../api';
import { Case } from '../types';

interface SummaryDetailProps {
  activeCase: Case;
  onViewOpinion: () => void;
}

export default function SummaryDetail({
  activeCase,
  onViewOpinion
}: SummaryDetailProps) {
  const [summaryText, setSummaryText] = useState<string>('Loading summary...');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isSubscribed = true;
    const fetchSummary = async () => {
      try {
        const res = await api.getSummary(activeCase.id);
        if (isSubscribed) {
          setSummaryText(res.summary);
        }
      } catch (err) {
        if (isSubscribed) {
          setSummaryText('Failed to load summary. It may still be processing.');
        }
      } finally {
        if (isSubscribed) {
          setIsLoading(false);
        }
      }
    };
    fetchSummary();
    return () => { isSubscribed = false; };
  }, [activeCase.id]);

  return (
    <div className="max-w-3xl mx-auto bg-white rounded-xl border border-gray-200 p-8 shadow-[0px_4px_12px_rgba(0,0,0,0.04)] select-none">
      {/* Header section with automated generating badges */}
      <header className="flex flex-col sm:flex-row justify-between items-start mb-6 border-b border-gray-200 pb-5 gap-4">
        <div>
          <h2 className="font-sans text-2xl font-semibold text-black mb-1.5 tracking-tight">
            Case #{activeCase.id} - Summary
          </h2>
          <div className="flex items-center gap-3">
            <span className="px-2 py-0.5 bg-[#d0e1fb] text-[#131b2e] text-[10px] font-bold rounded border border-blue-200 uppercase tracking-wide">
              GENERATED
            </span>
          </div>
        </div>
      </header>

      {/* Structured Body (The Readable Intake Page) */}
      <article className="space-y-6">
        
        {/* Patient overview card */}
        <section>
          <h3 className="font-sans font-bold text-[10px] text-gray-500 uppercase tracking-wider mb-2 select-none">
            Patient Overview
          </h3>
          <div className="grid grid-cols-2 gap-4 bg-gray-50 p-4 rounded border border-gray-200">
            <div>
              <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Client Name / Description</p>
              <p className="font-sans text-base font-bold text-black mt-0.5">
                {activeCase.clientName}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-gray-500 font-semibold uppercase tracking-wider">Date Created</p>
              <p className="font-sans text-base font-bold text-black mt-0.5">
                {activeCase.dateCreated}
              </p>
            </div>
          </div>
        </section>

        {/* Event Narrative & Chronology */}
        <section>
          <h3 className="font-sans font-bold text-[10px] text-gray-500 uppercase tracking-wider mb-2 select-none">
            Case Summary & Narrative
          </h3>
          <div className="border-l-4 border-black pl-5 py-0.5">
            {isLoading ? (
              <p className="text-xs italic leading-relaxed text-gray-400 font-sans animate-pulse">
                Loading summary...
              </p>
            ) : (
              <MarkdownRenderer content={summaryText} />
            )}
          </div>
        </section>

        {/* Footer info & view full opinion trigger */}
        <footer className="pt-6 border-t border-gray-200 flex flex-col items-center gap-4 text-center">
          <p className="text-[10px] text-gray-400 font-mono">
            Generated from {activeCase.documents.length} processed case files
          </p>
          <button
            onClick={onViewOpinion}
            className="group flex items-center gap-1 text-black font-bold hover:underline underline-offset-4 text-xs cursor-pointer"
          >
            <span>View full clinical opinion</span>
            <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
          </button>
        </footer>
      </article>
    </div>
  );
}
