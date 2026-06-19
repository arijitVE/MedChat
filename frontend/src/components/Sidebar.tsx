import { Plus } from 'lucide-react';
import { Case } from '../types';

interface SidebarProps {
  activeCase: Case | null;
  activeTab: 'documents' | 'summary' | 'opinion' | 'chat';
  onTabChange: (tab: 'documents' | 'summary' | 'opinion' | 'chat') => void;
  onNewDocumentClick: () => void;
  onNavigateHome: () => void;
}

export default function Sidebar({
  activeCase,
  activeTab,
  onTabChange,
  onNewDocumentClick,
  onNavigateHome
}: SidebarProps) {
  const isCaseSelected = !!activeCase;

  return (
    <aside className="w-64 bg-slate-50 border-r border-gray-200 flex flex-col p-4 gap-2 shrink-0 h-full select-none">
      {/* Brand / Case Header Context */}
      <div className="mb-6 px-1">
        {isCaseSelected ? (
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div
                className="w-9 h-9 bg-black rounded flex items-center justify-center text-white text-md font-bold cursor-pointer hover:opacity-90 transition-opacity"
                onClick={onNavigateHome}
                title="Go back to Case List"
              >
                {activeCase.id.slice(0, 2)}
              </div>
              <div className="overflow-hidden">
                <h2
                  className="font-sans text-md font-bold text-black leading-tight cursor-pointer hover:underline truncate"
                  onClick={onNavigateHome}
                  title="Go back to Case List"
                >
                  Case #{activeCase.id}
                </h2>
                <p className="text-[11px] text-gray-500 truncate w-36">
                  {activeCase.title}
                </p>
              </div>
            </div>

            {/* CTA button inside Case Workspace */}
            <button
              onClick={onNewDocumentClick}
              className="w-full mt-4 bg-black text-white py-2 px-3 rounded-lg font-semibold flex items-center justify-center gap-2 hover:opacity-95 transition-opacity text-xs cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>New Document</span>
            </button>
          </div>
        ) : (
          <div>
            <div className="flex items-center gap-3 mb-1">
              <div className="w-10 h-10 bg-black rounded flex items-center justify-center text-white text-lg font-bold">
                M
              </div>
              <div>
                <h2 className="font-sans text-md font-bold text-black leading-tight">
                  MedLegal Review
                </h2>
                <p className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">
                  Administrator Portal
                </p>
              </div>
            </div>
            
            <button
              onClick={() => alert("Please select or build a Case first to add new documents.")}
              className="w-full mt-4 bg-gray-300 text-gray-600 cursor-not-allowed py-2 px-3 rounded-lg font-semibold flex items-center justify-center gap-2 text-xs"
              disabled
            >
              <Plus className="w-4 h-4" />
              <span>New Document</span>
            </button>
          </div>
        )}
      </div>

      {/* Primary Navigation */}
      {isCaseSelected ? (
        <nav className="flex-1 flex flex-col gap-1">
          <button
            onClick={() => onTabChange('documents')}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg font-sans text-xs transition-all cursor-pointer ${
              activeTab === 'documents'
                ? 'bg-[#d0e1fb] text-[#131b2e] font-semibold'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">description</span>
            <span>Documents</span>
          </button>

          <button
            onClick={() => onTabChange('summary')}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg font-sans text-xs transition-all cursor-pointer ${
              activeTab === 'summary'
                ? 'bg-[#d0e1fb] text-[#131b2e] font-semibold'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">analytics</span>
            <span>Summary</span>
          </button>

          <button
            onClick={() => onTabChange('opinion')}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg font-sans text-xs transition-all cursor-pointer ${
              activeTab === 'opinion'
                ? 'bg-[#d0e1fb] text-[#131b2e] font-semibold'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">gavel</span>
            <span>Opinion</span>
          </button>

          <button
            onClick={() => onTabChange('chat')}
            className={`flex items-center gap-3 px-3 py-2 rounded-lg font-sans text-xs transition-all cursor-pointer ${
              activeTab === 'chat'
                ? 'bg-[#d0e1fb] text-[#131b2e] font-semibold'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <span className="material-symbols-outlined text-[18px]">chat</span>
            <span>Chat</span>
          </button>
        </nav>
      ) : (
        <div className="flex-1 text-xs text-gray-400 italic p-2">
          Select an active case below to unlock clinical document insights.
        </div>
      )}

      {/* Footer Navigation */}
      <div className="mt-auto border-t border-gray-200 pt-3 flex flex-col gap-1">
        <button
          onClick={() => alert("Archive is stored in encrypted deep glacier directories complying with HIPAA.")}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 text-xs hover:bg-gray-100 transition-all cursor-pointer text-left w-full"
        >
          <span className="material-symbols-outlined text-[18px]">archive</span>
          <span>Archive</span>
        </button>
        <button
          onClick={() => alert("Welcome to MedLegal MedCare Support. Please contact support@medlegalreview.com.")}
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-gray-600 text-xs hover:bg-gray-100 transition-all cursor-pointer text-left w-full"
        >
          <span className="material-symbols-outlined text-[18px]">help</span>
          <span>Support</span>
        </button>
      </div>
    </aside>
  );
}
