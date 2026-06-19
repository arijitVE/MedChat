import { useState, useEffect } from 'react';
import { Hourglass, Info } from 'lucide-react';
import { api } from '../api';
import { Case } from '../types';

interface ProcessingStateProps {
  activeCase: Case;
  activeJobId: string;
  onCancel: () => void;
  onCompleteAnalysis: () => void;
}

const LOG_TRANSCRIPTS = [
  "SYSTEM_LOG: CROSS_REFERENCING_MED_REC_08821_PART_A...",
  "SYSTEM_LOG: INDEXING_LEGAL_PRECEDENTS_NY_DISTRICT...",
  "SYSTEM_LOG: EXTRACTING_METADATA_FROM_MRI_SCANS...",
  "SYSTEM_LOG: VERIFYING_CLAIM_DATES_AGAINST_POST_OP_RECORDS...",
  "SYSTEM_LOG: BUILDING_NEURAL_RELATIONSHIP_MAP...",
  "SYSTEM_LOG: PARSING_PHYSICAL_THERAPY_GOAL_METRICS...",
  "SYSTEM_LOG: RESOLVING_BILLING_DESCRIPTORS_AND_CODES...",
  "SYSTEM_LOG: MERGING_DR_ARIS_OPERATIVE_CHRONOLOGIES..."
];

export default function ProcessingState({
  activeCase,
  activeJobId,
  onCancel,
  onCompleteAnalysis
}: ProcessingStateProps) {
  const [currentLogIdx, setCurrentLogIdx] = useState(0);
  const [analysingProgress, setAnalysingProgress] = useState(65);
  const [activeStep, setActiveStep] = useState<1 | 2 | 3 | 4>(2);
  const [showToast, setShowToast] = useState(true);

  // Rotate logs
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentLogIdx(prev => (prev + 1) % LOG_TRANSCRIPTS.length);
    }, 2500);
    return () => clearInterval(timer);
  }, []);

  // Real polling mechanism
  useEffect(() => {
    let isSubscribed = true;
    
    const checkStatus = async () => {
      try {
        const job = await api.getJobStatus(activeCase.id, activeJobId);
        if (!isSubscribed) return;
        
        // Map backend progress (0-100) and status to our visual steps
        setAnalysingProgress(job.progress || 10);
        
        if (job.status === 'COMPLETED') {
          setActiveStep(4);
          setAnalysingProgress(100);
          setTimeout(() => {
            if (isSubscribed) onCompleteAnalysis();
          }, 1000);
        } else if (job.status === 'FAILED') {
          alert('Processing failed: ' + (job.error_message || 'Unknown error'));
          onCancel();
        } else if (job.status === 'PROCESSING') {
          // If progress is > 50, jump to step 3 visually
          if (job.progress > 50) {
            setActiveStep(3);
          } else {
            setActiveStep(2);
          }
        }
      } catch (err) {
        console.error('Failed to poll job status', err);
      }
    };
    
    // Check immediately, then every 10 seconds
    checkStatus();
    const timer = setInterval(checkStatus, 10000);
    
    return () => {
      isSubscribed = false;
      clearInterval(timer);
    };
  }, [activeCase.id, activeJobId, onCompleteAnalysis, onCancel]);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 h-full flex flex-col justify-between overflow-y-auto">
      {/* Central Hourglass / Header section */}
      <div className="text-center mb-8 select-none">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-[#dec29a] mb-4 shadow-xs">
          <Hourglass className="w-8 h-8 text-[#271901] animate-spin" style={{ animationDuration: '4s' }} />
        </div>
        <h1 className="font-sans text-3xl font-semibold tracking-tight text-black leading-tight mb-2">
          Processing Workspace
        </h1>
        <p className="text-gray-500 text-sm max-w-lg mx-auto">
          Analyzing clinical data for <span className="font-semibold text-black">Case #{activeCase.id}</span>. This process typically takes <span className="font-semibold text-black">2-5 minutes</span> depending on document volume.
        </p>
      </div>

      {/* Bento Progress Steps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 select-none mb-8">
        
        {/* Step 1: Completed Text Extraction */}
        <div className="bg-white border border-gray-200 p-4 rounded-xl flex items-start gap-4">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-green-50 flex items-center justify-center border border-green-200 text-green-700">
            <span className="material-symbols-outlined text-[20px] font-bold">check_circle</span>
          </div>
          <div className="flex-1">
            <div className="flex justify-between items-center mb-1">
              <h3 className="font-sans font-semibold text-xs text-black">Extracting text</h3>
              <span className="text-[9px] font-bold text-green-700 bg-green-50 px-1.5 py-0.5 rounded border border-green-100 uppercase tracking-wider">
                Completed
              </span>
            </div>
            <p className="text-[11px] text-gray-500 leading-snug">
              Successfully parsed 1,420 pages of clinical records and legal filings.
            </p>
            <div className="mt-2.5 h-1.5 w-full bg-green-100 rounded-full overflow-hidden">
              <div className="h-full w-full bg-green-600"></div>
            </div>
          </div>
        </div>

        {/* Step 2: Content Analysis (Active or Completed) */}
        <div className={`bg-white p-4 rounded-xl flex items-start gap-4 transition-all relative overflow-hidden ${
          activeStep === 2
            ? 'border-2 border-[#F59E0B] shadow-sm'
            : 'border border-gray-200'
        }`}>
          {activeStep === 2 && (
            <div className="absolute top-0 right-0 w-24 h-24 opacity-[0.03] pointer-events-none text-[#F59E0B] rotate-12">
              <span className="material-symbols-outlined text-[96px]">data_exploration</span>
            </div>
          )}
          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border text-xs font-bold font-mono ${
            activeStep > 2
              ? 'bg-green-50 border-green-200 text-green-700'
              : 'bg-amber-50 border-[#dec29a] text-amber-700 animate-pulse'
          }`}>
            {activeStep > 2 ? (
              <span className="material-symbols-outlined text-[20px] font-bold">check_circle</span>
            ) : (
              <span className="material-symbols-outlined text-[20px]">psychology</span>
            )}
          </div>
          <div className="flex-1 z-10">
            <div className="flex justify-between items-center mb-1">
              <h3 className="font-sans font-semibold text-xs text-black">Analyzing content</h3>
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                activeStep > 2
                  ? 'text-green-700 bg-green-50 border border-green-100'
                  : 'text-amber-700 bg-amber-50 border border-[#dec29a]'
              }`}>
                {activeStep > 2 ? 'Completed' : 'Processing'}
              </span>
            </div>
            <p className="text-[11px] text-gray-500 leading-snug">
              Cross-referencing medical chronologies with legal prerequisites and discovery dates.
            </p>
            <div className="mt-2.5 h-1.5 w-full bg-amber-50 rounded-full overflow-hidden relative">
              <div
                className={`h-full bg-[#f59e0b] rounded-full transition-all duration-300 ${
                  activeStep > 2 ? 'w-full bg-green-600' : ''
                }`}
                style={{ width: activeStep > 2 ? '100%' : `${analysingProgress}%` }}
              ></div>
            </div>
          </div>
        </div>

        {/* Step 3: Building Summary (Pending or Active) */}
        <div className={`p-4 rounded-xl flex items-start gap-4 transition-all ${
          activeStep === 3
            ? 'bg-white border-2 border-amber-500'
            : activeStep > 3
            ? 'bg-white border border-gray-200'
            : 'bg-gray-100 border border-dashed border-gray-300 opacity-60'
        }`}>
          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border ${
            activeStep > 3
              ? 'bg-green-50 border-green-200 text-green-700'
              : activeStep === 3
              ? 'bg-amber-50 border-amber-200 text-amber-700 animate-pulse'
              : 'bg-gray-200 border-gray-300 text-gray-500'
          }`}>
            {activeStep > 3 ? (
              <span className="material-symbols-outlined text-[20px] font-bold">check_circle</span>
            ) : (
              <span className="material-symbols-outlined text-[20px]">auto_stories</span>
            )}
          </div>
          <div className="flex-1">
            <div className="flex justify-between items-center mb-1">
              <h3 className={`font-sans font-semibold text-xs ${
                activeStep >= 3 ? 'text-black' : 'text-gray-500'
              }`}>Building summary</h3>
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                activeStep > 3
                  ? 'text-green-700 bg-green-50 border border-green-100'
                  : activeStep === 3
                  ? 'text-amber-700 bg-amber-50 border border-[#dec29a]'
                  : 'text-gray-400 border border-gray-200'
              }`}>
                {activeStep > 3 ? 'Completed' : activeStep === 3 ? 'Processing' : 'Pending'}
              </span>
            </div>
            <p className="text-[11px] text-gray-500 leading-snug">
              Consolidating findings into a high-level executive medical-legal overview.
            </p>
            <div className="mt-2.5 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-300 ${
                  activeStep > 3 ? 'bg-green-600 w-full' : activeStep === 3 ? 'bg-[#f59e0b]' : 'w-0'
                }`}
                style={{ width: activeStep > 3 ? '100%' : activeStep === 3 ? `${analysingProgress}%` : '0%' }}
              ></div>
            </div>
          </div>
        </div>

        {/* Step 4: Drafting Opinion (Pending or Active) */}
        <div className={`p-4 rounded-xl flex items-start gap-4 transition-all ${
          activeStep === 4
            ? 'bg-white border-2 border-amber-600'
            : 'bg-gray-100 border border-dashed border-gray-300 opacity-60'
        }`}>
          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border ${
            activeStep === 4
              ? 'bg-amber-50 border-amber-200 text-amber-700 animate-pulse'
              : 'bg-gray-200 border-gray-300 text-gray-500'
          }`}>
            <span className="material-symbols-outlined text-[20px]">edit_note</span>
          </div>
          <div className="flex-1">
            <div className="flex justify-between items-center mb-1">
              <h3 className={`font-sans font-semibold text-xs ${
                activeStep === 4 ? 'text-black' : 'text-gray-500'
              }`}>Drafting opinion</h3>
              <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                activeStep === 4
                  ? 'text-amber-700 bg-amber-50 border border-[#dec29a]'
                  : 'text-gray-400 border border-gray-200'
              }`}>
                {activeStep === 4 ? 'Processing' : 'Pending'}
              </span>
            </div>
            <p className="text-[11px] text-gray-500 leading-snug">
              Synthesizing expert viewpoints based on specific case precedents and standards.
            </p>
            <div className="mt-2.5 h-1.5 w-full bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-[#f59e0b] rounded-full transition-all duration-300"
                style={{ width: activeStep === 4 ? `${analysingProgress}%` : '0%' }}
              ></div>
            </div>
          </div>
        </div>
      </div>

      {/* Logging Transcript Simulation Area */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 relative min-h-[180px] flex flex-col justify-between overflow-hidden shadow-xs">
        <div className="font-mono text-[11px] text-gray-450 uppercase tracking-widest border-b border-gray-100 pb-2 flex items-center justify-between select-none">
          <span>Live Clinical Analysis Feed</span>
          <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-450 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
        </div>

        <div className="my-3 text-center">
          <p className="font-mono text-[12px] text-gray-600 font-semibold mb-2 animate-pulse">
            {LOG_TRANSCRIPTS[currentLogIdx]}
          </p>
        </div>

        {/* Status diagnostic boxes matching visual items list perfectly */}
        <div className="bg-slate-50 p-3 rounded-lg border border-gray-200">
          <div className="flex items-center gap-2.5 mb-1.5">
            <span className="w-1.5 h-1.5 bg-[#f59e0b] rounded-full"></span>
            <span className="text-[11px] font-mono text-gray-850">
              Found: Dr. Smith Radiology Report (March 12, 2023)
            </span>
          </div>
          <div className="flex items-center gap-2.5 mb-1.5">
            <span className="w-1.5 h-1.5 bg-[#f59e0b] rounded-full"></span>
            <span className="text-[11px] font-mono text-gray-850">
              Matching: Billing Code 74176 (CT Scan Abdomen)
            </span>
          </div>
          <div className="flex items-center gap-2.5">
            <span className="w-1.5 h-1.5 bg-gray-300 rounded-full"></span>
            <span className="text-[11px] font-mono text-gray-400 italic animate-pulse">
              Parsing subsequent clinical records & medical-legal logs...
            </span>
          </div>
        </div>
      </div>

      {/* Footer HIPAA badge & cancel */}
      <footer className="mt-8 flex flex-col sm:flex-row justify-between items-center border-t border-gray-200 pt-4 gap-4 select-none">
        <div className="flex items-center gap-2 text-gray-500 text-xs">
          <Info className="w-4 h-4 text-gray-400 shrink-0" />
          <span>Your documents are encrypted and processed in a secure high-compliance HIPAA environment.</span>
        </div>
        <button
          onClick={onCancel}
          className="text-xs font-semibold text-[#ba1a1a] hover:underline cursor-pointer py-1 px-2 hover:bg-red-50 rounded"
        >
          Cancel Processing
        </button>
      </footer>

      {/* Contextual warning toast layout perfectly matched to bottom right */}
      {showToast && (
        <div className="fixed bottom-6 right-6 bg-[#2d3133] text-[#eff1f3] px-5 py-4 rounded-xl shadow-xl flex items-center gap-4 z-[99] border border-gray-700 max-w-sm animate-fade-in">
          <span className="material-symbols-outlined text-[#F59E0B] text-[24px]">warning</span>
          <div className="flex-1">
            <p className="font-sans font-bold text-xs">Analysis in progress</p>
            <p className="text-[10px] opacity-80 mt-0.5">Do not close this tab for optimal sequence performance.</p>
          </div>
          <button
            onClick={() => setShowToast(false)}
            className="hover:bg-white/10 p-1 rounded-full transition-colors cursor-pointer shrink-0"
          >
            <span className="material-symbols-outlined text-[16px] text-[#eff1f3]">close</span>
          </button>
        </div>
      )}
    </div>
  );
}
