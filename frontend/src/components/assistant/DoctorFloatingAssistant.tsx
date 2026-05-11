import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bot,
  ChevronDown,
  Minimize2,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  X,
} from 'lucide-react';
import { Button } from '../ui/Button';
import { normalizeApiError } from '../../lib/apiError';
import { useDoctorQuery } from '../../hooks/useIntelligence';
import { usePatientSearch } from '../../hooks/useReports';
import type { PatientProfile } from '../../types/assignment';
import {
  isReasoningResult,
  isRetrievalResult,
  isTrendResult,
  type ChatMessage,
  type DoctorAssistantMode,
  type DoctorQueryResponse,
} from '../../types/intelligence';

type PanelState = 'closed' | 'minimized' | 'expanded';
type WorkflowMode = 'patient' | 'global' | 'report' | 'trend' | 'ocr' | 'abnormality';

interface WorkflowOption {
  id: WorkflowMode;
  label: string;
  description: string;
  requiresPatient: boolean;
  requestMode: DoctorAssistantMode;
}

interface SuggestedAction {
  label: string;
  prompt: string;
}

const workflowOptions: WorkflowOption[] = [
  {
    id: 'patient',
    label: 'Patient-Specific Analysis',
    description: 'Summaries, comparisons, and retrieval for one selected patient.',
    requiresPatient: true,
    requestMode: 'patient_specific',
  },
  {
    id: 'global',
    label: 'Global Analytics',
    description: 'Aggregated workflow and population-level insights.',
    requiresPatient: false,
    requestMode: 'global_analytics',
  },
  {
    id: 'report',
    label: 'Report Discussion',
    description: 'Discuss a selected patient report context without leaving your workflow.',
    requiresPatient: true,
    requestMode: 'report_discussion',
  },
  {
    id: 'trend',
    label: 'Trend Analysis',
    description: 'Review longitudinal changes and abnormal trends for a patient.',
    requiresPatient: true,
    requestMode: 'trend_analysis',
  },
  {
    id: 'ocr',
    label: 'OCR/Extraction Investigation',
    description: 'Analyze extraction quality, low confidence patterns, and failed processing.',
    requiresPatient: false,
    requestMode: 'ocr_investigation',
  },
  {
    id: 'abnormality',
    label: 'Abnormality Review',
    description: 'Prioritize abnormal fields, critical values, and review focus areas.',
    requiresPatient: true,
    requestMode: 'abnormality_review',
  },
];

const suggestionsByMode: Record<WorkflowMode, SuggestedAction[]> = {
  patient: [
    { label: 'Summarize Patient History', prompt: 'Summarize this patient history using only accessible stored reports.' },
    { label: 'Compare Recent Reports', prompt: 'Compare this patient recent reports and highlight clinically relevant changes.' },
    { label: 'Show Abnormal Trends', prompt: 'Show abnormal trends for this patient using exact stored values where available.' },
    { label: 'Explain Critical Values', prompt: 'Explain this patient critical or abnormal values in clinically safe language.' },
    { label: 'Ask Free Question', prompt: '' },
  ],
  global: [
    { label: 'Common Abnormalities', prompt: 'What are the most common abnormalities across my accessible patient records?' },
    { label: 'Workflow Summary', prompt: 'Summarize my current verification workload and report lifecycle distribution.' },
    { label: 'Reports Needing Review', prompt: 'Which categories of reports need doctor review most often?' },
    { label: 'OCR Failure Patterns', prompt: 'Which report types or statuses suggest OCR or extraction failure patterns?' },
    { label: 'Ask Free Question', prompt: '' },
  ],
  report: [
    { label: 'Summarize Latest Report', prompt: 'Summarize the latest accessible report for this patient.' },
    { label: 'Explain Abnormal Fields', prompt: 'Explain abnormal fields in this patient report context using stored values only.' },
    { label: 'Compare With Prior Reports', prompt: 'Compare this report context with the patient prior accessible reports.' },
    { label: 'Ask Free Question', prompt: '' },
  ],
  trend: [
    { label: 'Glucose Trend', prompt: 'Show this patient glucose trend and cite exact stored values where available.' },
    { label: 'Hemoglobin Trend', prompt: 'Show this patient hemoglobin trend and cite exact stored values where available.' },
    { label: 'Cholesterol Trend', prompt: 'Show this patient cholesterol trend and cite exact stored values where available.' },
    { label: 'Ask Free Question', prompt: '' },
  ],
  ocr: [
    { label: 'Failed Processing', prompt: 'Summarize failed processing and OCR/extraction investigation patterns for my accessible workflow.' },
    { label: 'Low Confidence Patterns', prompt: 'Identify low confidence extraction patterns from my accessible reports.' },
    { label: 'HITL Drivers', prompt: 'Summarize likely drivers for HITL review in my accessible workflow.' },
    { label: 'Ask Free Question', prompt: '' },
  ],
  abnormality: [
    { label: 'List Abnormal Values', prompt: 'List abnormal values for this patient using exact stored data only.' },
    { label: 'Explain Critical Values', prompt: 'Explain this patient critical values and verification priorities.' },
    { label: 'Prioritize Review', prompt: 'Prioritize which abnormalities need review first for this patient.' },
    { label: 'Ask Free Question', prompt: '' },
  ],
};

function getContextKey(mode: WorkflowMode | null, patient: PatientProfile | null) {
  if (!mode) {
    return 'unselected';
  }

  return `${mode}:${patient?.user_id ?? 'global'}`;
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '-';
  }

  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }

  return JSON.stringify(value);
}

function getAssistantText(response: DoctorQueryResponse) {
  if (isReasoningResult(response)) {
    return response.interpretation;
  }

  if (isTrendResult(response)) {
    return response.insight;
  }

  return response.query_interpretation;
}

function AssistantResponse({ response }: { response: DoctorQueryResponse }) {
  if (isReasoningResult(response)) {
    return (
      <div className="space-y-2">
        <p>{response.interpretation}</p>
        {response.clinical_significance ? (
          <p className="text-xs text-clinical-text-secondary">{response.clinical_significance}</p>
        ) : null}
        {response.critical_flags.length > 0 ? (
          <ul className="list-disc pl-4 text-xs text-clinical-critical">
            {response.critical_flags.map((flag) => <li key={flag}>{flag}</li>)}
          </ul>
        ) : null}
      </div>
    );
  }

  if (isTrendResult(response)) {
    return (
      <div className="space-y-1">
        <p>{response.insight}</p>
        <p className="text-xs text-clinical-text-secondary">
          Trend: {response.trend_direction}; points: {response.data_points.length}
        </p>
      </div>
    );
  }

  if (isRetrievalResult(response)) {
    return (
      <div className="space-y-2">
        <p>{response.query_interpretation}</p>
        <p className="text-xs text-clinical-text-secondary">
          {response.total_count} records found by {response.retrieval_type} retrieval.
        </p>
        {response.records.length > 0 ? (
          <div className="space-y-2">
            {response.records.slice(0, 4).map((record, index) => (
              <div
                key={`${response.query_interpretation}-${index}`}
                className="rounded-md border border-clinical-border bg-white px-2 py-1.5 text-xs"
              >
                {Object.entries(record).slice(0, 4).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-3">
                    <span className="text-clinical-text-secondary">{key}</span>
                    <span className="font-medium text-clinical-text-primary">{stringifyValue(value)}</span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return null;
}

function PatientSearchStep({
  selectedPatient,
  onSelectPatient,
}: {
  selectedPatient: PatientProfile | null;
  onSelectPatient: (patient: PatientProfile | null) => void;
}) {
  const [search, setSearch] = useState('');
  const patientSearch = usePatientSearch(search);
  const patients = patientSearch.data ?? [];

  return (
    <div className="space-y-3 rounded-md border border-clinical-border bg-slate-50 p-3">
      <div>
        <label className="text-xs font-semibold uppercase text-clinical-text-secondary" htmlFor="doctor-ai-patient-search">
          Patient context
        </label>
        <div className="mt-1 flex items-center gap-2 rounded-md border border-clinical-border bg-white px-3 py-2">
          <Search className="h-4 w-4 text-clinical-text-muted" aria-hidden="true" />
          <input
            id="doctor-ai-patient-search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
            placeholder="Search by Patient ID or name"
          />
        </div>
      </div>

      {selectedPatient ? (
        <div className="flex items-start justify-between gap-3 rounded-md border border-clinical-primary bg-clinical-primary-light px-3 py-2">
          <div>
            <p className="text-sm font-semibold text-clinical-primary">{selectedPatient.full_name}</p>
            <p className="font-mono text-xs text-clinical-text-secondary">{selectedPatient.patient_uid}</p>
          </div>
          <button
            type="button"
            className="rounded-md px-2 py-1 text-xs font-medium text-clinical-primary hover:bg-white"
            onClick={() => onSelectPatient(null)}
          >
            Change
          </button>
        </div>
      ) : null}

      {!selectedPatient && search.trim().length > 0 ? (
        <div className="max-h-36 space-y-1 overflow-y-auto">
          {patientSearch.isLoading ? (
            <p className="text-xs text-clinical-text-secondary">Searching assigned patients...</p>
          ) : null}
          {!patientSearch.isLoading && patients.length === 0 ? (
            <p className="text-xs text-clinical-text-secondary">No assigned patients found.</p>
          ) : null}
          {patients.map((patient) => (
            <button
              key={patient.user_id}
              type="button"
              className="w-full rounded-md border border-clinical-border bg-white px-3 py-2 text-left hover:border-clinical-primary"
              onClick={() => onSelectPatient(patient)}
            >
              <span className="block text-sm font-medium text-clinical-text-primary">{patient.full_name}</span>
              <span className="block font-mono text-xs text-clinical-text-secondary">{patient.patient_uid}</span>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function DoctorFloatingAssistant() {
  const [panelState, setPanelState] = useState<PanelState>('closed');
  const [mode, setMode] = useState<WorkflowMode | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<PatientProfile | null>(null);
  const [input, setInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [messagesByContext, setMessagesByContext] = useState<Record<string, ChatMessage[]>>({});
  const doctorQuery = useDoctorQuery();
  const abortControllerRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const activeOption = workflowOptions.find((option) => option.id === mode) ?? null;
  const contextKey = getContextKey(mode, selectedPatient);
  const messages = messagesByContext[contextKey] ?? [];
  const requiresPatient = Boolean(activeOption?.requiresPatient);
  const contextReady = Boolean(activeOption) && (!requiresPatient || Boolean(selectedPatient));

  const activeContextLabel = useMemo(() => {
    if (!activeOption) {
      return 'Choose a workflow';
    }

    if (requiresPatient) {
      return selectedPatient
        ? `${activeOption.label} · ${selectedPatient.full_name}`
        : `${activeOption.label} · patient required`;
    }

    return activeOption.label;
  }, [activeOption, requiresPatient, selectedPatient]);

  useEffect(() => {
    return () => abortControllerRef.current?.abort();
  }, []);

  const selectMode = (nextMode: WorkflowMode) => {
    const nextOption = workflowOptions.find((option) => option.id === nextMode);
    setMode(nextMode);
    setInput('');
    setErrorMessage(null);

    if (!nextOption?.requiresPatient) {
      setSelectedPatient(null);
    }
  };

  const sendPrompt = async (prompt: string) => {
    const text = prompt.trim();
    if (!text || !activeOption || !contextReady) {
      return;
    }

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    setErrorMessage(null);
    setInput('');

    const nextContextKey = getContextKey(mode, selectedPatient);
    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessagesByContext((current) => ({
      ...current,
      [nextContextKey]: [...(current[nextContextKey] ?? []), userMessage],
    }));

    try {
      const response = await doctorQuery.mutateAsync({
        data: {
          text,
          patient_id: selectedPatient?.user_id,
          mode: activeOption.requestMode,
          workflow: activeOption.label,
        },
        signal: abortController.signal,
      });
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: getAssistantText(response),
        reasoningResult: isReasoningResult(response) ? response : undefined,
        trendResult: isTrendResult(response) ? response : undefined,
        retrievalResult: isRetrievalResult(response) ? response : undefined,
        timestamp: new Date().toISOString(),
      };
      setMessagesByContext((current) => ({
        ...current,
        [nextContextKey]: [...(current[nextContextKey] ?? []), assistantMessage],
      }));
    } catch (error) {
      if (!abortController.signal.aborted) {
        setErrorMessage(normalizeApiError(error).message);
      }
    }
  };

  if (panelState === 'closed') {
    return (
      <button
        type="button"
        className="fixed bottom-6 right-6 z-50 inline-flex h-14 w-14 items-center justify-center rounded-full bg-clinical-primary text-white shadow-lg transition hover:bg-clinical-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary focus-visible:ring-offset-2"
        onClick={() => setPanelState('expanded')}
        aria-label="Open Doctor AI Assistant"
      >
        <Bot className="h-6 w-6" aria-hidden="true" />
      </button>
    );
  }

  if (panelState === 'minimized') {
    return (
      <button
        type="button"
        className="fixed bottom-6 right-6 z-50 inline-flex items-center gap-2 rounded-md bg-clinical-primary px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-clinical-primary-dark focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-primary focus-visible:ring-offset-2"
        onClick={() => setPanelState('expanded')}
      >
        <Sparkles className="h-4 w-4" aria-hidden="true" />
        AI Assistant
        <ChevronDown className="h-4 w-4 rotate-180" aria-hidden="true" />
      </button>
    );
  }

  return (
    <section
      className="fixed bottom-6 right-6 z-50 flex h-[min(720px,calc(100vh-3rem))] w-[min(440px,calc(100vw-2rem))] flex-col overflow-hidden rounded-lg border border-clinical-border bg-clinical-surface shadow-2xl"
      aria-label="Doctor AI Assistant"
    >
      <header className="border-b border-clinical-border px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-clinical-primary-light text-clinical-primary">
                <Bot className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <h2 className="text-sm font-semibold text-clinical-text-primary">Doctor AI Assistant</h2>
                <p className="text-xs text-clinical-text-secondary">{activeContextLabel}</p>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-1 text-xs text-clinical-text-secondary">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
              RBAC-scoped retrieval before AI response
            </div>
          </div>
          <div className="flex gap-1">
            <button
              type="button"
              className="rounded-md p-2 text-clinical-text-secondary hover:bg-slate-100"
              onClick={() => setPanelState('minimized')}
              aria-label="Minimize assistant"
            >
              <Minimize2 className="h-4 w-4" aria-hidden="true" />
            </button>
            <button
              type="button"
              className="rounded-md p-2 text-clinical-text-secondary hover:bg-slate-100"
              onClick={() => setPanelState('closed')}
              aria-label="Close assistant"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {workflowOptions.map((option) => (
            <button
              key={option.id}
              type="button"
              className={`rounded-md border px-3 py-2 text-left transition ${
                mode === option.id
                  ? 'border-clinical-primary bg-clinical-primary-light'
                  : 'border-clinical-border bg-white hover:border-clinical-primary'
              }`}
              onClick={() => selectMode(option.id)}
            >
              <span className="block text-sm font-semibold text-clinical-text-primary">{option.label}</span>
              <span className="mt-1 block text-xs text-clinical-text-secondary">{option.description}</span>
            </button>
          ))}
        </div>

        {activeOption?.requiresPatient ? (
          <PatientSearchStep selectedPatient={selectedPatient} onSelectPatient={setSelectedPatient} />
        ) : null}

        {activeOption ? (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase text-clinical-text-secondary">Suggested actions</p>
            <div className="flex flex-wrap gap-2">
              {suggestionsByMode[activeOption.id].map((action) => (
                <button
                  key={action.label}
                  type="button"
                  className="rounded-full border border-clinical-border bg-white px-3 py-1.5 text-xs font-medium text-clinical-text-primary hover:border-clinical-primary disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={!contextReady || doctorQuery.isPending}
                  onClick={() => {
                    if (action.prompt) {
                      void sendPrompt(action.prompt);
                    } else {
                      inputRef.current?.focus();
                    }
                  }}
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {errorMessage ? (
          <div className="rounded-md border border-clinical-critical bg-clinical-critical-bg px-3 py-2 text-sm text-clinical-critical" role="alert">
            {errorMessage}
          </div>
        ) : null}

        <div className="min-h-48 space-y-3 rounded-md border border-clinical-border bg-slate-50 p-3" role="log" aria-live="polite">
          {messages.length === 0 ? (
            <p className="text-sm text-clinical-text-secondary">
              Select a workflow mode first. Patient-scoped modes require a patient context before prompts are sent.
            </p>
          ) : null}
          {messages.map((message) => (
            <div
              key={`${message.timestamp}-${message.role}`}
              className={`rounded-md px-3 py-2 text-sm ${
                message.role === 'user'
                  ? 'ml-auto max-w-[90%] bg-clinical-primary text-white'
                  : 'mr-auto max-w-[90%] border border-clinical-border bg-white text-clinical-text-primary'
              }`}
            >
              {message.role === 'user' ? message.content : null}
              {message.role === 'assistant' && message.reasoningResult ? <AssistantResponse response={message.reasoningResult} /> : null}
              {message.role === 'assistant' && message.trendResult ? <AssistantResponse response={message.trendResult} /> : null}
              {message.role === 'assistant' && message.retrievalResult ? <AssistantResponse response={message.retrievalResult} /> : null}
            </div>
          ))}
          {doctorQuery.isPending ? (
            <div className="mr-auto max-w-[90%] rounded-md border border-clinical-border bg-white px-3 py-2 text-sm text-clinical-text-secondary">
              Thinking with scoped retrieval...
            </div>
          ) : null}
        </div>
      </div>

      <form
        className="border-t border-clinical-border p-3"
        onSubmit={(event) => {
          event.preventDefault();
          void sendPrompt(input);
        }}
      >
        <div className="flex gap-2">
          <input
            ref={inputRef}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            className="min-w-0 flex-1 rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light disabled:bg-slate-50"
            placeholder={contextReady ? 'Ask a scoped question' : 'Choose mode and context first'}
            disabled={!contextReady}
            aria-label="Assistant prompt"
          />
          <Button
            type="submit"
            className="px-3"
            loading={doctorQuery.isPending}
            disabled={!contextReady || !input.trim()}
            aria-label="Send assistant prompt"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </form>
    </section>
  );
}
