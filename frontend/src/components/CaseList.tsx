import React, { useState } from 'react';
import { Plus, ChevronLeft, ChevronRight, MoreVertical, Search } from 'lucide-react';
import { Case } from '../types';

interface CaseListProps {
  cases: Case[];
  onSelectCase: (caseId: string) => void;
  onAddCase: (newCase: Case) => void;
  onDeleteCase: (caseId: string) => void;
  searchTerm: string;
  statusFilter: 'ALL' | 'PROCESSING' | 'COMPLETED';
}

export default function CaseList({
  cases,
  onSelectCase,
  onAddCase,
  onDeleteCase,
  searchTerm,
  statusFilter
}: CaseListProps) {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newClientName, setNewClientName] = useState('');
  const [newAgeSex, setNewAgeSex] = useState('58-year-old male');
  const [newDiagnosis, setNewDiagnosis] = useState('');
  
  // Local state for table pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 6;

  // Filter cases based on global searchTerm and statusFilter
  const filteredCases = cases.filter(c => {
    if (statusFilter === 'PROCESSING') {
      if (c.status !== 'PROCESSING') return false;
    } else if (statusFilter === 'COMPLETED') {
      if (c.status !== 'COMPLETED') return false;
    }

    const s = searchTerm.toLowerCase();
    return (
      c.title.toLowerCase().includes(s) ||
      (c.ref && c.ref.toLowerCase().includes(s)) ||
      (c.clientName && c.clientName.toLowerCase().includes(s))
    );
  });

  // Pages calc
  const totalItems = filteredCases.length;
  const totalPages = Math.ceil(filteredCases.length / itemsPerPage) || 1;
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = Math.min(startIndex + itemsPerPage, totalItems);
  const currentCases = filteredCases.slice(startIndex, endIndex);

  // Stats calc
  const activeCount = cases.length;
  const processingCount = cases.filter(c => c.status === 'PROCESSING' || c.documents.some(d => d.status === 'PROCESSING')).length;
  const completedCount = cases.filter(c => c.status === 'COMPLETED').length;
  const failedCount = cases.filter(c => c.status === 'FAILED' || c.documents.some(d => d.status === 'FAILED')).length;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle || !newClientName) return;

    const randomRefNum = Math.floor(1000 + Math.random() * 9000);
    const newCaseItem: Case = {
      id: String(randomRefNum),
      title: newTitle,
      ref: `${randomRefNum}-XP`,
      clientName: newClientName,
      clientAgeSex: newAgeSex,
      primaryDiagnosis: newDiagnosis ? newDiagnosis.split(',').map(s => s.trim()) : ['General Evaluation'],
      status: 'CREATED',
      dateCreated: new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      }),
      documents: [],
      chatHistory: []
    };

    onAddCase(newCaseItem);
    setIsModalOpen(false);

    // Reset fields
    setNewTitle('');
    setNewClientName('');
    setNewAgeSex('58-year-old male');
    setNewDiagnosis('');
  };

  return (
    <div className="flex-1 flex flex-col overflow-y-auto bg-[#f7f9fb] p-8">
      {/* Title / Action Header */}
      <div className="flex justify-between items-end mb-6">
        <div>
          <h1 className="font-sans text-3xl font-semibold text-black tracking-tight leading-tight">
            Active Cases
          </h1>
          <p className="text-gray-500 text-xs mt-1">
            Manage and monitor medical-legal document reviews.
          </p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="bg-black hover:opacity-90 active:scale-[0.98] text-white text-xs font-semibold px-5 py-2.5 rounded-lg flex items-center gap-2 transition-all cursor-pointer shadow-sm"
        >
          <Plus className="w-4 h-4" />
          <span>New Case</span>
        </button>
      </div>

      {/* Bento Style Statistics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6 select-none">
        <div className="bg-white border border-gray-200 p-4 rounded-xl shadow-[0px_4px_12px_rgba(0,0,0,0.03)] flex flex-col justify-between">
          <p className="text-[11px] font-sans font-bold text-gray-500 uppercase tracking-wider">
            Total Active
          </p>
          <p className="text-3xl font-semibold text-black mt-2">
            {activeCount}
          </p>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-xl shadow-[0px_4px_12px_rgba(0,0,0,0.03)] flex flex-col justify-between">
          <p className="text-[11px] font-sans font-bold text-gray-500 uppercase tracking-wider">
            Processing
          </p>
          <div className="flex items-center gap-2 mt-2">
            <p className="text-3xl font-semibold text-black">
              {processingCount}
            </p>
            <span className="bg-[#fcdeb5] text-[#574425] text-[10px] px-1.5 py-0.5 rounded font-bold uppercase tracking-wider">
              LIVE
            </span>
          </div>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-xl shadow-[0px_4px_12px_rgba(0,0,0,0.03)] flex flex-col justify-between">
          <p className="text-[11px] font-sans font-bold text-gray-500 uppercase tracking-wider">
            Completed Today
          </p>
          <p className="text-3xl font-semibold text-black mt-2">
            {completedCount}
          </p>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-xl shadow-[0px_4px_12px_rgba(0,0,0,0.03)] flex flex-col justify-between">
          <p className="text-[11px] font-sans font-bold text-gray-500 uppercase tracking-wider">
            Failed Alerts
          </p>
          <p className="text-3xl font-semibold text-[#ba1a1a] mt-2">
            {failedCount}
          </p>
        </div>
      </div>

      {/* Data Table Area */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-[0px_4px_12px_rgba(0,0,0,0.03)] flex-grow flex flex-col justify-between overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 text-gray-500 text-[10px] uppercase tracking-wider font-semibold select-none">
                <th className="px-6 py-3">Case Title</th>
                <th className="px-6 py-3">Ref</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Date Created</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs">
              {currentCases.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-gray-400 font-sans italic">
                    No active medical cases found matching your search term.
                  </td>
                </tr>
              ) : (
                currentCases.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => onSelectCase(item.id)}
                    className="hover:bg-gray-50 transition-colors group cursor-pointer"
                  >
                    {/* Title & Client details */}
                    <td className="px-6 py-3.5">
                      <div className="flex items-center gap-3">
                        <span className="material-symbols-outlined text-gray-400">description</span>
                        <div>
                          <p className="font-semibold text-black group-hover:underline">
                            {item.title}
                          </p>
                          <p className="text-[10px] text-gray-500 mt-0.5">
                            Client: {item.clientName} &bull; {item.clientAgeSex}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* Reference ID */}
                    <td className="px-6 py-3.5 font-mono text-[11px] text-gray-600">
                      Ref: #{item.ref}
                    </td>

                    {/* Status badge */}
                    <td className="px-6 py-3.5">
                      {item.status === 'CREATED' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-gray-100 text-gray-800 uppercase border border-gray-200">
                          CREATED
                        </span>
                      )}
                      {item.status === 'PROCESSING' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-[#fcdeb5] text-[#574425] uppercase animate-pulse border border-[#dec29a]">
                          PROCESSING
                        </span>
                      )}
                      {item.status === 'COMPLETED' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-[#d0e1fb] text-[#131b2e] uppercase border border-blue-200">
                          COMPLETED
                        </span>
                      )}
                      {item.status === 'FAILED' && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-[#ffdad6] text-[#ba1a1a] uppercase border border-red-200">
                          FAILED
                        </span>
                      )}
                    </td>

                    {/* Date Created */}
                    <td className="px-6 py-3.5 font-mono text-[11px] text-gray-500">
                      {item.dateCreated}
                    </td>

                    {/* Actions dropdown button */}
                    <td className="px-6 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                      <div className="relative inline-block text-left">
                        <button
                          onClick={() => {
                            if (confirm(`Do you really want to archive/delete Case #${item.id}?`)) {
                              onDeleteCase(item.id);
                            }
                          }}
                          className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-red-700 transition-colors cursor-pointer"
                          title="Delete Case Log"
                        >
                          <span className="material-symbols-outlined">delete</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Table Footer with Pagination controls */}
        <div className="p-4 border-t border-gray-200 flex items-center justify-between bg-gray-50 select-none">
          <span className="text-[11px] text-gray-500">
            Showing {totalItems === 0 ? 0 : startIndex + 1} to {endIndex} of {totalItems} cases
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage(p => Math.max(p - 1, 1))}
              disabled={currentPage === 1}
              className={`p-1 rounded border border-gray-200 hover:bg-white transition-colors cursor-pointer ${
                currentPage === 1 ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <ChevronLeft className="w-3.5 h-3.5 text-gray-600" />
            </button>
            
            {Array.from({ length: totalPages }, (_, idx) => idx + 1).map(num => (
              <button
                key={num}
                onClick={() => setCurrentPage(num)}
                className={`px-2.5 py-0.5 rounded text-[11px] font-bold transition-all cursor-pointer ${
                  currentPage === num
                    ? 'bg-black text-white'
                    : 'text-gray-600 hover:bg-gray-200'
                }`}
              >
                {num}
              </button>
            ))}

            <button
              onClick={() => setCurrentPage(p => Math.min(p + 1, totalPages))}
              disabled={currentPage === totalPages}
              className={`p-1 rounded border border-gray-200 hover:bg-white transition-colors cursor-pointer ${
                currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              <ChevronRight className="w-3.5 h-3.5 text-gray-600" />
            </button>
          </div>
        </div>
      </div>

      {/* NEW CASE MODAL */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-[100] flex items-center justify-center p-4 backdrop-blur-xs">
          <div className="bg-white rounded-xl border border-gray-300 p-6 w-full max-w-md shadow-xl">
            <h2 className="text-lg font-bold text-black mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-black">add_circle</span>
              <span>Register New Legal-Medical Case</span>
            </h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                  Case Folder Title
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Smith Neurological Malpractice Case"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-black"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                  Client Full Name
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Dr. Julian Pierce or Mrs. Clara Smith"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-black"
                  value={newClientName}
                  onChange={(e) => setNewClientName(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                    Age / Sex
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 52-year-old male"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-black"
                    value={newAgeSex}
                    onChange={(e) => setNewAgeSex(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1">
                    Primary Diagnosis
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Hypertension, Diabetes"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:outline-none focus:border-black"
                    value={newDiagnosis}
                    onChange={(e) => setNewDiagnosis(e.target.value)}
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-gray-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 border border-gray-300 hover:bg-gray-50 font-semibold text-xs text-gray-600 rounded-lg cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-black hover:opacity-90 font-semibold text-xs text-white rounded-lg cursor-pointer"
                >
                  Create Folder
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
