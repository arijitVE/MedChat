export interface CaseDocument {
  id: string;
  name: string;
  uuid: string;
  size: string;
  uploadedAt: string;
  status: 'PROCESSED' | 'PROCESSING' | 'UPLOADED' | 'FAILED';
}

export interface Case {
  id: string;
  title: string;
  ref: string;
  clientName: string;
  clientAgeSex: string;
  primaryDiagnosis: string[];
  status: 'CREATED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  dateCreated: string;
  documents: CaseDocument[];
  summary?: CaseSummary;
  opinion?: OpinionDraft;
  chatHistory: Message[];
  chatThreads?: ChatThread[];
  activeThreadId?: string;
}

export interface ChatThread {
  id: string;
  title: string;
  date: string;
  messages: Message[];
}

export interface CaseSummary {
  updatedAt: string;
  version: string;
  patientName: string;
  patientAgeSex: string;
  diagnoses: string[];
  insights: string[];
  narrative: string;
  medications: string[];
}

export interface OpinionDraft {
  version: string;
  lastAnalyzed: string;
  executiveSummary: string;
  standardsOfCare: string[];
  chronology: string;
  causation: string;
  furtherInquiry: string[];
  confidenceScore: number;
  sourceCitations: number;
  legalPrecedents: number;
}

export interface Message {
  id: string;
  sender: 'ai' | 'user';
  time: string;
  content: string;
  citation?: {
    text: string;
    source: string;
    page: number;
  };
}

export interface User {
  fullName: string;
  email: string;
  isLoggedIn: boolean;
  role?: 'admin' | 'user';
}
