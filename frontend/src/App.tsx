import { useState, useEffect } from 'react';
import { api, onUnauthorized, setAuthToken } from './api';
import { Case, CaseDocument, CaseSummary, OpinionDraft, Message, User } from './types';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import CaseList from './components/CaseList';
import UploadZone from './components/UploadZone';
import ProcessingState from './components/ProcessingState';
import SummaryDetail from './components/SummaryDetail';
import OpinionDraftView from './components/OpinionDraftView';
import CaseIntelligenceChat from './components/CaseIntelligenceChat';
import AuthScreens from './components/AuthScreens';

export default function App() {
  // Authentication status
  const [currentUser, setCurrentUser] = useState<User>({
    fullName: '',
    email: '',
    isLoggedIn: false
  });

  // Main global database state
  const [cases, setCases] = useState<Case[]>([]);
  const [isLoadingCases, setIsLoadingCases] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    onUnauthorized(() => {
      handleLogout();
    });

    const initAuth = async () => {
      const token = localStorage.getItem('token');
      if (token) {
        try {
          const userData = await api.getMe();
          setCurrentUser({
            fullName: userData.full_name,
            email: userData.email,
            isLoggedIn: true
          });
        } catch (err) {
          console.error("Failed to restore session:", err);
          handleLogout();
        }
      }
      setIsInitializing(false);
    };

    initAuth();
  }, []);

  const loadCases = async () => {
    setIsLoadingCases(true);
    try {
      const data = await api.listCases();
      // Map API data to our frontend Case interface
      const mapped = data.map((c: any) => ({
        id: c.id,
        title: c.title || 'Untitled Case',
        ref: c.id.substring(0, 8),
        clientName: c.description || 'Unknown Client',
        clientAgeSex: 'N/A',
        primaryDiagnosis: ['General Evaluation'],
        status: c.status,
        dateCreated: new Date(c.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
        documents: [], // To be fetched fully when opened, or map from c.documents if we add it to list endpoint
        chatHistory: []
      }));
      setCases(mapped);
    } catch (err) {
      console.error('Failed to load cases:', err);
    } finally {
      setIsLoadingCases(false);
    }
  };

  useEffect(() => {
    if (currentUser.isLoggedIn) {
      loadCases();
    }
  }, [currentUser.isLoggedIn]);
  
  // Dashboard search filter term
  const [searchTerm, setSearchTerm] = useState('');

  // Dashboard navigation status filter
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'PROCESSING' | 'COMPLETED'>('ALL');

  // Active workspace states
  const [activeCaseId, setActiveCaseId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'documents' | 'summary' | 'opinion' | 'chat'>('documents');
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Authentication callbacks
  const handleLoginSuccess = (name: string, mail: string) => {
    setCurrentUser({
      fullName: name,
      email: mail,
      isLoggedIn: true
    });
  };

  const handleLogout = () => {
    setAuthToken(null);
    setCurrentUser(prev => ({ ...prev, isLoggedIn: false }));
    setActiveCaseId(null);
  };

  // Case CRUD actions
  const handleSelectCase = async (caseId: string) => {
    setActiveCaseId(caseId);
    setActiveTab('documents');
    setIsProcessing(false);
    
    // Fetch full case details including documents
    try {
      const fullCase = await api.getCase(caseId);
      setCases(prev => prev.map(c => {
        if (c.id === caseId) {
          return {
            ...c,
            documents: (fullCase.documents || []).map((d: any) => ({
              id: d.id,
              name: d.file_name,
              uuid: d.id.substring(0, 8),
              size: 'N/A', // Assuming not tracked by backend POC
              uploadedAt: new Date(d.uploaded_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
              status: d.status
            }))
          };
        }
        return c;
      }));
    } catch (err) {
      console.error('Failed to fetch full case details:', err);
    }
  };

  const handleNavigateHome = () => {
    setActiveCaseId(null);
    setIsProcessing(false);
  };

  const handleAddCase = async (newCase: Case) => {
    try {
      const res = await api.createCase({
        title: newCase.title,
        description: newCase.clientName
      });
      // Add the new case from backend, mixed with the mock data properties the frontend uses
      setCases([{
        ...newCase,
        id: res.id,
        ref: res.id.substring(0, 8),
        status: res.status,
        dateCreated: new Date(res.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
      }, ...cases]);
    } catch (err) {
      console.error('Failed to create case:', err);
    }
  };

  const handleDeleteCase = (caseId: string) => {
    setCases(cases.filter(c => c.id !== caseId));
    if (activeCaseId === caseId) {
      setActiveCaseId(null);
    }
  };

  // Active Case Helper
  const activeCase = cases.find(c => c.id === activeCaseId) || null;

  // Document/Summary/Opinion update synchronizers
  const handleUpdateCaseDocuments = (updatedDocs: CaseDocument[]) => {
    if (!activeCaseId) return;
    setCases(cases.map(c => {
      if (c.id === activeCaseId) {
        return { ...c, documents: updatedDocs };
      }
      return c;
    }));
  };

  const handleUpdateOpinion = (updatedOpinion: OpinionDraft) => {
    if (!activeCaseId) return;
    setCases(cases.map(c => {
      if (c.id === activeCaseId) {
        return { ...c, opinion: updatedOpinion };
      }
      return c;
    }));
  };

  const handleSendMessage = (msg: Message) => {
    if (!activeCaseId || !activeCase) return;
    handleUpdateChatHistory([...activeCase.chatHistory, msg]);
  };

  const handleUpdateChatHistory = (msgs: Message[]) => {
    if (!activeCaseId) return;
    setCases(cases.map(c => {
      if (c.id === activeCaseId) {
        return { ...c, chatHistory: msgs };
      }
      return c;
    }));
  };

  // Complete processing simulation callbacks
  const handleCompleteAnalysis = () => {
    if (!activeCaseId || !activeCase) return;
    
    // Create rich clinical contents if none exists on processed completion 
    const finalSummary: CaseSummary = activeCase.summary || {
      updatedAt: new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
      version: 'V2.4 GENERATED',
      patientName: activeCase.clientName,
      patientAgeSex: activeCase.clientAgeSex,
      diagnoses: activeCase.primaryDiagnosis,
      insights: [
        'Dynamic spinal cord edema compression observed in late-surgical telemetry log readings.',
        'Document-to-log discrepancies confirm a 12.5 hour acute pager delay warning response wait.',
        'Neurology follow-up assessments missed during late shift transfers.'
      ],
      narrative: `Pursuant to the orthopedic file review from Oct 24, ${activeCase.clientName} underwent a spinal operation. Post-surgical nursing chart logs indicate hypoesthesia recorded on shift transition, with subsequent motor grade loss. Staff communication delayed escalated pager requests. Re-operation was delayed past critical sensory rescue windows.`,
      medications: ['Lisinopril', 'Gabapentin', 'Metformin']
    };

    const finalOpinion: OpinionDraft = activeCase.opinion || {
      version: '1.4',
      lastAnalyzed: new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
      executiveSummary: `Following exhaustive indexing of the medical records in the case files of ${activeCase.title}, this draft reviews nursing and surgical action protocols.`,
      standardsOfCare: [
        'Neurological vital chart tracking intervals every 2-4 hours following thoracotomy fusion.',
        'Immediate warning pager notice to neurosurgery if motor grade declines by >1 MMT.',
        'Intermittent sensory assessment mapping following anesthesia transition.'
      ],
      chronology: 'Nurse R. noted progressive hypoesthesia on March 14 at 14:30. Neurosurgical escalation did not occur until the morning shift call at 03:00 on March 15, showing standard deviation.',
      causation: 'Delayed escalation of post-surgical hematoma decompression led to irreversible secondary neurological compromises.',
      furtherInquiry: [
        'Electronic Health Record activity trail audits.',
        'On-call nursing schedule reports for the night of March 14.',
        'Consent documentation and vital signs telemetry extracts.'
      ],
      confidenceScore: 94,
      sourceCitations: 12,
      legalPrecedents: 4
    };

    const finalDocs = activeCase.documents.map(d => ({
      ...d,
      status: 'PROCESSED' as const
    }));

    const finalChat: Message[] = activeCase.chatHistory.length > 0 ? activeCase.chatHistory : [
      {
        id: 'init-msg',
        sender: 'ai',
        time: 'Just now',
        content: `I have compiled and structured dynamic medical-legal insights for **Case #${activeCase.id}**! All documents are processed.\n\nYou can now browse the **Summary**, evaluate the **Preliminary Opinion**, or ask me anything.`
      }
    ];

    setCases(cases.map(c => {
      if (c.id === activeCaseId) {
        return {
          ...c,
          status: 'COMPLETED',
          documents: finalDocs,
          summary: finalSummary,
          opinion: finalOpinion,
          chatHistory: finalChat
        };
      }
      return c;
    }));

    setIsProcessing(false);
    setActiveTab('summary'); // Direct them nicely to summary to see the beautiful results!
  };

  // Auth Guard
  if (isInitializing) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="animate-pulse flex flex-col items-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-gray-500 font-medium">Restoring session...</p>
      </div>
    </div>;
  }

  if (!currentUser.isLoggedIn) {
    return <AuthScreens onLoginSuccess={handleLoginSuccess} />;
  }

  // Dynamic counts for status filter tabs
  const processingCount = cases.filter(c => c.status === 'PROCESSING').length;
  const completedCount = cases.filter(c => c.status === 'COMPLETED').length;

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-white text-gray-900">
      
      {/* Top Header Navigation */}
      <Header
        currentTab={activeTab}
        activeCaseId={activeCaseId}
        caseName={activeCase?.title}
        onNavigateHome={handleNavigateHome}
        currentUser={currentUser}
        onLogout={handleLogout}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        processingCount={processingCount}
        completedCount={completedCount}
      />

      <div className="flex flex-1 overflow-hidden">
        
        {/* Dynamic Sidebar Navigation */}
        <Sidebar
          activeCase={activeCase}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onNavigateHome={handleNavigateHome}
          onNewDocumentClick={() => {
            if (activeCaseId) {
              setActiveTab('documents');
              setIsProcessing(false);
            }
          }}
        />

        {/* Primary Content Hub area */}
        <main className="flex-1 flex flex-col overflow-hidden h-full">
          {activeCaseId === null ? (
            <CaseList
              cases={cases}
              onSelectCase={handleSelectCase}
              onAddCase={handleAddCase}
              onDeleteCase={handleDeleteCase}
              searchTerm={searchTerm}
              statusFilter={statusFilter}
            />
          ) : (
            <div className="flex-1 overflow-hidden h-full flex flex-col bg-[#f7f9fb]">
              {isProcessing && activeJobId ? (
                <ProcessingState
                  activeCase={activeCase!}
                  activeJobId={activeJobId}
                  onCancel={() => setIsProcessing(false)}
                  onCompleteAnalysis={handleCompleteAnalysis}
                />
              ) : (
                <div className="flex-1 overflow-hidden p-6">
                  {activeTab === 'documents' && (
                    <div className="h-full overflow-y-auto">
                      <UploadZone
                        activeCase={activeCase!}
                        onUpdateCaseDocuments={handleUpdateCaseDocuments}
                        onStartProcessing={(jobId) => {
                          setActiveJobId(jobId);
                          setIsProcessing(true);
                          // Temporarily mark documents inside processing view to PROCESSING status
                          const processingDocs = activeCase!.documents.map(d => ({
                            ...d,
                            status: d.status === 'UPLOADED' ? ('PROCESSING' as const) : d.status
                          }));
                          handleUpdateCaseDocuments(processingDocs);
                        }}
                      />
                    </div>
                  )}

                  {activeTab === 'summary' && (
                    <div className="h-full overflow-y-auto">
                      <SummaryDetail
                        activeCase={activeCase!}
                        onViewOpinion={() => setActiveTab('opinion')}
                      />
                    </div>
                  )}

                  {activeTab === 'opinion' && (
                    <div className="h-full overflow-y-auto">
                      <OpinionDraftView
                        activeCase={activeCase!}
                      />
                    </div>
                  )}

                  {activeTab === 'chat' && (
                    <CaseIntelligenceChat
                      activeCase={activeCase!}
                      onSendMessage={handleSendMessage}
                      onUpdateChatHistory={handleUpdateChatHistory}
                    />
                  )}
                </div>
              )}
            </div>
          )}
        </main>

      </div>
    </div>
  );
}
