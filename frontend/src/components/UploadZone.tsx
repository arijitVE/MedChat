import React, { useRef, useState } from 'react';
import { api } from '../api';
import { Case, CaseDocument } from '../types';

interface UploadZoneProps {
  activeCase: Case;
  onUpdateCaseDocuments: (docs: CaseDocument[]) => void;
  onStartProcessing: (jobId: string) => void;
}

export default function UploadZone({
  activeCase,
  onUpdateCaseDocuments,
  onStartProcessing
}: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  // Stats calculation
  const totalWeight = activeCase.documents.reduce((acc, d) => {
    // Basic weight parsing helper 
    const num = parseFloat(d.size) || 0;
    return acc + num;
  }, 0).toFixed(1);

  const processedCount = activeCase.documents.filter(d => d.status === 'PROCESSED').length;
  const totalCount = activeCase.documents.length;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      await handleRealUpload(e.dataTransfer.files[0]);
    }
  };

  const handleRealUpload = async (file: File) => {
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are supported at this time.');
      return;
    }
    try {
      const res = await api.uploadDocument(activeCase.id, file);
      const newDoc: CaseDocument = {
        id: res.id,
        name: res.file_name,
        uuid: res.id.substring(0, 8),
        size: 'Unknown',
        uploadedAt: new Date(res.uploaded_at).toLocaleDateString('en-US', {
          year: 'numeric', month: 'short', day: 'numeric'
        }),
        status: res.status
      };
      onUpdateCaseDocuments([...activeCase.documents, newDoc]);
    } catch (err) {
      alert('Failed to upload file');
      console.error(err);
    }
  };

  const addSimulatedFile = (name: string, size: string) => {
    const randomId = 'doc-' + Math.floor(Math.random() * 1000000);
    const newDoc: CaseDocument = {
      id: randomId,
      name: name,
      uuid: `${activeCase.id}-${name.slice(0, 3).toUpperCase()}-${Math.floor(100 + Math.random() * 899)}`,
      size: size,
      uploadedAt: new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      }),
      status: 'UPLOADED'
    };

    onUpdateCaseDocuments([...activeCase.documents, newDoc]);
  };

  const handleSelectFilesClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      await handleRealUpload(e.target.files[0]);
    }
    // reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleDeleteFile = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = activeCase.documents.filter(d => d.id !== id);
    onUpdateCaseDocuments(updated);
  };

  const handleRefreshFile = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const updated = activeCase.documents.map(d => {
      if (d.id === id) {
        return { ...d, status: 'UPLOADED' as const };
      }
      return d;
    });
    onUpdateCaseDocuments(updated);
  };

  const handleStartProcessingClick = async () => {
    try {
      const res = await api.processCase(activeCase.id);
      onStartProcessing(res.id);
    } catch (err) {
      alert('Failed to start processing');
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Start Processing button */}
      <div className="flex justify-between items-end border-b border-gray-200 pb-4 select-none">
        <div>
          <h3 className="font-sans text-xl font-semibold text-black leading-tight">
            Document Workspace
          </h3>
          <p className="text-gray-500 text-xs mt-1">
            Manage and process clinical records for Case #{activeCase.id}.
          </p>
        </div>

        <button
          onClick={handleStartProcessingClick}
          className="bg-black hover:bg-gray-800 text-white text-xs font-semibold px-5 py-2.5 rounded-lg flex items-center gap-2 cursor-pointer shadow-sm hover:scale-[1.01] transition-transform"
        >
          <span className="material-symbols-outlined text-[18px]">play_arrow</span>
          <span>Start Processing</span>
        </button>
      </div>

      {/* Drag & Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleSelectFilesClick}
        className={`border-2 border-dashed rounded-xl p-8 text-center bg-white cursor-pointer select-none transition-all group relative overflow-hidden ${
          isDragging ? 'border-black bg-gray-50' : 'border-gray-250 hover:border-black'
        }`}
      >
        <input
          type="file"
          ref={fileInputRef}
          className="hidden"
          accept=".pdf,application/pdf"
          onChange={handleFileChange}
        />
        <div className="absolute inset-0 opacity-0 group-hover:opacity-[0.02] pointer-events-none bg-black"></div>
        <div className="relative z-10 flex flex-col items-center gap-2">
          <div className="w-14 h-14 bg-gray-50 rounded-full flex items-center justify-center text-gray-500 group-hover:text-black transition-colors mb-2">
            <span className="material-symbols-outlined text-[32px]">upload_file</span>
          </div>
          <h4 className="font-sans text-sm font-semibold text-black">
            Drop medical files or legal briefs here
          </h4>
          <p className="text-gray-500 text-xs max-w-sm">
            Maximum file size: 500MB per document. Supported: PDF, DOCX, DICOM, ZIP.
          </p>
          <button
            type="button"
            className="mt-3 px-4 py-1.5 border border-gray-300 rounded-lg font-semibold text-xs text-gray-700 bg-white hover:bg-gray-50 cursor-pointer"
          >
            Select Files
          </button>
        </div>
      </div>

      {/* File List Section */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
        {/* Header section of catalog */}
        <div className="bg-gray-50 px-5 py-3 border-b border-gray-200 flex justify-between items-center select-none">
          <h5 className="font-sans font-bold text-[10px] text-gray-500 uppercase tracking-wider">
            Queue: {activeCase.documents.length} Documents
          </h5>
          <div className="flex gap-4">
            <button className="text-gray-500 hover:text-black transition-colors flex items-center gap-1.5 cursor-pointer text-xs">
              <span className="material-symbols-outlined text-[16px]">filter_list</span>
              <span>Filter</span>
            </button>
            <button className="text-gray-500 hover:text-black transition-colors flex items-center gap-1.5 cursor-pointer text-xs">
              <span className="material-symbols-outlined text-[16px]">sort</span>
              <span>Sort</span>
            </button>
          </div>
        </div>

        {/* List of files with Grid matching layout perfectly */}
        <div className="divide-y divide-gray-100">
          {activeCase.documents.length === 0 ? (
            <div className="text-center text-gray-400 text-xs py-8 italic font-sans">
              No files currently uploaded for this case. Drop files or click "Select Files" above to get started.
            </div>
          ) : (
            activeCase.documents.map((doc) => {
              const isPdf = doc.name.toLowerCase().endsWith('.pdf');
              return (
                <div
                  key={doc.id}
                  className="flex flex-col sm:grid sm:grid-cols-12 gap-3 sm:gap-4 items-start sm:items-center px-5 py-4 hover:bg-gray-50 transition-colors group"
                >
                  {/* File ID / Indicator */}
                  <div className="col-span-12 sm:col-span-6 flex items-center gap-4">
                    <span className="material-symbols-outlined text-gray-400">
                      {isPdf ? 'picture_as_pdf' : 'description'}
                    </span>
                    <div className="overflow-hidden">
                      <p className="font-semibold text-black text-xs truncate">
                        {doc.name}
                      </p>
                      <p className="font-mono text-[10px] text-gray-500 mt-0.5">
                        UUID: {doc.uuid}
                      </p>
                    </div>
                  </div>

                  {/* Size and upload date */}
                  <div className="col-span-6 sm:col-span-3 text-xs text-gray-500">
                    {doc.size} &bull; {doc.uploadedAt}
                  </div>

                  {/* Status chip */}
                  <div className="col-span-3 sm:col-span-2">
                    {doc.status === 'PROCESSED' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-green-50 text-green-700 text-[10px] font-bold rounded border border-green-200 uppercase tracking-wide">
                        <span className="w-1.5 h-1.5 bg-green-600 rounded-full"></span>
                        PROCESSED
                      </span>
                    )}

                    {doc.status === 'PROCESSING' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-[10px] font-bold rounded animate-pulse border border-blue-200 uppercase tracking-wide">
                        <span className="w-1.5 h-1.5 bg-blue-600 rounded-full animate-ping"></span>
                        PROCESSING
                      </span>
                    )}

                    {doc.status === 'UPLOADED' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-gray-50 text-gray-700 text-[10px] font-bold rounded border border-gray-200 uppercase tracking-wide">
                        <span className="w-1.5 h-1.5 bg-gray-600 rounded-full"></span>
                        UPLOADED
                      </span>
                    )}

                    {doc.status === 'FAILED' && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-50 text-red-700 text-[10px] font-bold rounded border border-red-200 uppercase tracking-wide">
                        <span className="w-1.5 h-1.5 bg-red-600 rounded-full"></span>
                        FAILED
                      </span>
                    )}
                  </div>

                  {/* Action Buttons on hover */}
                  <div className="col-span-3 sm:col-span-1 flex justify-end gap-2 shrink-0 select-none">
                    {doc.status === 'FAILED' ? (
                      <button
                        onClick={(e) => handleRefreshFile(doc.id, e)}
                        className="text-gray-400 hover:text-black p-0.5 hover:bg-gray-100 rounded transition-colors cursor-pointer"
                        title="Retry upload / processing"
                      >
                        <span className="material-symbols-outlined text-[18px]">refresh</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => alert(`Reviewing static preview for document "${doc.name}"...`)}
                        className="text-gray-400 hover:text-black p-0.5 hover:bg-gray-100 rounded transition-colors cursor-pointer"
                        title="View Document Details"
                      >
                        <span className="material-symbols-outlined text-[18px]">visibility</span>
                      </button>
                    )}
                    <button
                      onClick={(e) => handleDeleteFile(doc.id, e)}
                      className="text-gray-400 hover:text-red-700 p-0.5 hover:bg-gray-100 rounded transition-colors cursor-pointer"
                      title="Remove file"
                    >
                      <span className="material-symbols-outlined text-[18px]">delete</span>
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Storage Information Bento Blocks */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 select-none">
        <div className="bg-white border border-gray-200 p-4 rounded-xl flex items-center gap-4 shadow-[0px_4px_12px_rgba(0,0,0,0.03)]">
          <div className="w-11 h-11 bg-gray-50 rounded-lg flex items-center justify-center text-black">
            <span className="material-symbols-outlined">storage</span>
          </div>
          <div>
            <p className="text-[10px] font-sans font-bold text-gray-500 uppercase tracking-wider">
              Storage Used
            </p>
            <p className="font-sans text-lg font-semibold text-black mt-0.5">
              {totalWeight} MB
            </p>
          </div>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-xl flex items-center gap-4 shadow-[0px_4px_12px_rgba(0,0,0,0.03)]">
          <div className="w-11 h-11 bg-gray-50 rounded-lg flex items-center justify-center text-black">
            <span className="material-symbols-outlined">check_circle</span>
          </div>
          <div>
            <p className="text-[10px] font-sans font-bold text-gray-500 uppercase tracking-wider">
              Processed
            </p>
            <p className="font-sans text-lg font-semibold text-black mt-0.5">
              {processedCount} / {totalCount} Files
            </p>
          </div>
        </div>

        <div className="bg-white border border-gray-200 p-4 rounded-xl flex items-center gap-4 shadow-[0px_4px_12px_rgba(0,0,0,0.03)]">
          <div className="w-11 h-11 bg-gray-50 rounded-lg flex items-center justify-center text-black">
            <span className="material-symbols-outlined">history</span>
          </div>
          <div>
            <p className="text-[10px] font-sans font-bold text-gray-500 uppercase tracking-wider">
              Last Update
            </p>
            <p className="font-sans text-lg font-semibold text-black mt-0.5">
              Just now
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
