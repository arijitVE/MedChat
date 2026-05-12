import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
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
import { reportsApi } from '../../api/reports';
import { useDoctorQuery } from '../../hooks/useIntelligence';
import { usePatientSearch } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import type { PatientProfile } from '../../types/assignment';
import {
  isReasoningResult,
  isRetrievalResult,
  isTrendResult,
  type ChatMessage,
  type DoctorAssistantMode,
  type DoctorQueryResponse,
} from '../../types/intelligence';
import type { Report } from '../../types/report';
import { Button } from '../ui/Button';

type PanelState = 'closed' | 'minimized' | 'expanded';
type PrimaryMode = 'patient' | 'global';
type PatientWorkflow = 'report' | 'trend' | 'abnormality' | 'free';
type GlobalWorkflow = 'population' | 'operational' | 'ocr' | 'free';

interface GuidedAction {
  label: string;
  prompt: string;
  mode: DoctorAssistantMode;
  workflow: string;
  filters?: Record<string, unknown>;
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
    <div className="space-y-3">
      <AssistantBubble>Search by Patient Name/Patient ID.</AssistantBubble>
      <div className="rounded-md border border-clinical-border bg-slate-50 p-3">
        <div className="flex items-center gap-2 rounded-md border border-clinical-border bg-white px-3 py-2">
          <Search className="h-4 w-4 text-clinical-text-muted" aria-hidden="true" />
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            className="min-w-0 flex-1 bg-transparent text-sm outline-none"
            placeholder="Search patient name or Patient ID"
            aria-label="Search patient name or patient id"
          />
        </div>

        {selectedPatient ? (
          <div className="mt-3 flex items-start justify-between gap-3 rounded-md border border-clinical-primary bg-clinical-primary-light px-3 py-2">
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
          <div className="mt-3 max-h-40 space-y-1 overflow-y-auto">
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
    </div>
  );
}

function AssistantBubble({ children }: { children: ReactNode }) {
  return (
    <div className="mr-auto max-w-[92%] rounded-lg border border-clinical-border bg-white px-3 py-2 text-sm text-clinical-text-primary shadow-sm">
      {children}
    </div>
  );
}

function UserBubble({ children }: { children: ReactNode }) {
  return (
    <div className="ml-auto max-w-[86%] rounded-lg bg-clinical-primary px-3 py-2 text-sm font-medium text-white">
      {children}
    </div>
  );
}

function OptionButton({
  label,
  description,
  disabled = false,
  onClick,
}: {
  label: string;
  description?: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="w-full rounded-lg border border-clinical-border bg-white px-3 py-2 text-left transition hover:border-clinical-primary hover:bg-clinical-primary-light disabled:cursor-not-allowed disabled:opacity-50"
      disabled={disabled}
      onClick={onClick}
    >
      <span className="block text-sm font-semibold text-clinical-text-primary">{label}</span>
      {description ? <span className="mt-0.5 block text-xs text-clinical-text-secondary">{description}</span> : null}
    </button>
  );
}

function QuickActionButton({
  label,
  disabled = false,
  onClick,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="rounded-full border border-clinical-border bg-white px-3 py-1.5 text-xs font-medium text-clinical-text-primary transition hover:border-clinical-primary hover:bg-clinical-primary-light disabled:cursor-not-allowed disabled:opacity-50"
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  );
}

function reportLabel(report: Report) {
  const date = report.first_uploaded_at ? new Date(report.first_uploaded_at).toLocaleDateString() : 'No date';
  return `${report.file_name} · ${date}`;
}

export function DoctorFloatingAssistant() {
  const [panelState, setPanelState] = useState<PanelState>('closed');
  const [primaryMode, setPrimaryMode] = useState<PrimaryMode | null>(null);
  const [patientWorkflow, setPatientWorkflow] = useState<PatientWorkflow | null>(null);
  const [globalWorkflow, setGlobalWorkflow] = useState<GlobalWorkflow | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<PatientProfile | null>(null);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [reportSearch, setReportSearch] = useState('');
  const [freeChatEnabled, setFreeChatEnabled] = useState(false);
  const [activeScopeLabel, setActiveScopeLabel] = useState<string | null>(null);
  const [activeRequestMode, setActiveRequestMode] = useState<DoctorAssistantMode>('patient_specific');
  const [activeFilters, setActiveFilters] = useState<Record<string, unknown> | undefined>();
  const [input, setInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [messagesByContext, setMessagesByContext] = useState<Record<string, ChatMessage[]>>({});
  const doctorQuery = useDoctorQuery();
  const abortControllerRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const reportsQuery = useQuery({
    queryKey: queryKeys.reports.list({
      role: 'doctor-assistant',
      patient_id: selectedPatient?.user_id,
      query: reportSearch,
    }),
    queryFn: async ({ signal }) => {
      if (!selectedPatient) {
        return [];
      }

      const response = await reportsApi.getDoctorReports({
        patient_id: selectedPatient.user_id,
        query: reportSearch.trim() || undefined,
      }, { signal });
      return response.data;
    },
    enabled: Boolean(selectedPatient) && patientWorkflow === 'report',
    staleTime: staleTime.reportDetail,
  });

  const contextKey = useMemo(() => {
    const patientKey = selectedPatient?.user_id ?? 'global';
    const workflowKey = primaryMode === 'patient' ? patientWorkflow ?? 'patient-menu' : globalWorkflow ?? 'global-menu';
    const scopeKey = selectedReport?.report_id ?? activeScopeLabel ?? 'unscoped';
    return `${primaryMode ?? 'start'}:${patientKey}:${workflowKey}:${scopeKey}`;
  }, [activeScopeLabel, globalWorkflow, patientWorkflow, primaryMode, selectedPatient, selectedReport]);
  const messages = messagesByContext[contextKey] ?? [];

  const activeContextLabel = useMemo(() => {
    if (!primaryMode) {
      return 'Choose a mode';
    }

    if (primaryMode === 'patient') {
      if (!selectedPatient) {
        return 'Patient-Specific Mode';
      }
      return activeScopeLabel
        ? `${selectedPatient.full_name} · ${activeScopeLabel}`
        : `${selectedPatient.full_name} · Patient-Specific Mode`;
    }

    return activeScopeLabel ? `Global Analytics · ${activeScopeLabel}` : 'Global Analytics Mode';
  }, [activeScopeLabel, primaryMode, selectedPatient]);

  useEffect(() => {
    return () => abortControllerRef.current?.abort();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ block: 'end' });
  }, [contextKey, doctorQuery.isPending, messages.length]);

  const resetPatientScope = () => {
    setPatientWorkflow(null);
    setSelectedPatient(null);
    setSelectedReport(null);
    setReportSearch('');
    setFreeChatEnabled(false);
    setActiveScopeLabel(null);
    setActiveFilters(undefined);
    setActiveRequestMode('patient_specific');
    setInput('');
    setErrorMessage(null);
  };

  const resetGlobalScope = () => {
    setGlobalWorkflow(null);
    setSelectedReport(null);
    setFreeChatEnabled(false);
    setActiveScopeLabel(null);
    setActiveFilters(undefined);
    setActiveRequestMode('global_analytics');
    setInput('');
    setErrorMessage(null);
  };

  const selectPrimaryMode = (mode: PrimaryMode) => {
    setPrimaryMode(mode);
    setErrorMessage(null);
    if (mode === 'patient') {
      resetPatientScope();
    } else {
      resetGlobalScope();
      setSelectedPatient(null);
    }
  };

  const selectPatient = (patient: PatientProfile | null) => {
    setSelectedPatient(patient);
    setPatientWorkflow(null);
    setSelectedReport(null);
    setReportSearch('');
    setFreeChatEnabled(false);
    setActiveScopeLabel(null);
    setActiveFilters(undefined);
    setActiveRequestMode('patient_specific');
    setInput('');
    setErrorMessage(null);
  };

  const activateScopedPrompt = async (action: GuidedAction) => {
    const targetKey = `${primaryMode ?? 'start'}:${selectedPatient?.user_id ?? 'global'}:${
      primaryMode === 'patient' ? patientWorkflow ?? 'patient-menu' : globalWorkflow ?? 'global-menu'
    }:${action.workflow}`;
    setFreeChatEnabled(true);
    setActiveScopeLabel(action.workflow);
    setActiveRequestMode(action.mode);
    setActiveFilters(action.filters);
    setSelectedReport(null);
    await sendPrompt(action.prompt, {
      mode: action.mode,
      workflow: action.workflow,
      filters: action.filters,
      nextContextKey: targetKey,
    });
  };

  const activateSpecificReport = async (report: Report) => {
    const filters = {
      report_scope: 'specific_report',
      job_ids: [report.job_id],
      report_ids: [report.report_id],
      max_fields: 60,
    };
    const workflow = `Specific Report: ${report.file_name}`;
    setSelectedReport(report);
    setFreeChatEnabled(true);
    setActiveScopeLabel(workflow);
    setActiveRequestMode('report_discussion');
    setActiveFilters(filters);
    await sendPrompt(`Summarize ${report.file_name}. Use only this selected report context and highlight key findings, abnormalities, and verification concerns.`, {
      mode: 'report_discussion',
      workflow,
      filters,
      nextContextKey: `${primaryMode ?? 'patient'}:${selectedPatient?.user_id ?? 'unknown'}:report:${report.report_id}`,
    });
  };

  const sendPrompt = async (
    prompt: string,
    override?: {
      mode?: DoctorAssistantMode;
      workflow?: string;
      filters?: Record<string, unknown>;
      nextContextKey?: string;
    },
  ) => {
    const text = prompt.trim();
    if (!text) {
      return;
    }

    const requestMode = override?.mode ?? activeRequestMode;
    const workflow = override?.workflow ?? activeScopeLabel ?? (primaryMode === 'global' ? 'Global Analytics' : 'Patient-Specific Mode');
    const filters = override?.filters ?? activeFilters;
    const nextContextKey = override?.nextContextKey ?? contextKey;

    if (primaryMode === 'patient' && !selectedPatient) {
      return;
    }

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    setErrorMessage(null);
    setInput('');

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
          patient_id: primaryMode === 'patient' ? selectedPatient?.user_id : undefined,
          mode: requestMode,
          workflow,
          filters,
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

  const reportActions: GuidedAction[] = [
    {
      label: 'Last Report',
      prompt: 'Summarize the latest report for this patient. Use the latest report only and include key findings, abnormal values, and verification concerns.',
      mode: 'report_discussion',
      workflow: 'Last Report',
      filters: { report_scope: 'last_reports', report_limit: 1, max_fields: 60 },
    },
    {
      label: 'Last 3 Reports',
      prompt: 'Summarize and compare the last 3 reports for this patient. Highlight progression, abnormalities, and clinically relevant changes.',
      mode: 'report_discussion',
      workflow: 'Last 3 Reports',
      filters: { report_scope: 'last_reports', report_limit: 3, max_fields: 90 },
    },
    {
      label: 'Last 5 Reports',
      prompt: 'Summarize and compare the last 5 reports for this patient. Highlight progression, repeated abnormalities, and verification concerns.',
      mode: 'report_discussion',
      workflow: 'Last 5 Reports',
      filters: { report_scope: 'last_reports', report_limit: 5, max_fields: 120 },
    },
    {
      label: 'Continue to Free Discussion',
      prompt: 'Prepare an overall report context summary for this patient using all accessible reports. Keep responses grounded in stored report data.',
      mode: 'report_discussion',
      workflow: 'All Reports Discussion',
      filters: { report_scope: 'all_reports', max_fields: 120 },
    },
  ];

  const trendActions: GuidedAction[] = [
    {
      label: 'Last Report Trend',
      prompt: 'Analyze trend-relevant values in the latest report and explain what changed compared with stored prior values if available.',
      mode: 'trend_analysis',
      workflow: 'Last Report Trend',
      filters: { report_scope: 'last_reports', report_limit: 1, max_fields: 60 },
    },
    {
      label: 'Last 3 Reports Trend',
      prompt: 'Compare clinically important values across the last 3 reports. Identify increasing, decreasing, or stable patterns.',
      mode: 'trend_analysis',
      workflow: 'Last 3 Reports Trend',
      filters: { report_scope: 'last_reports', report_limit: 3, max_fields: 90 },
    },
    {
      label: 'Longitudinal Trend',
      prompt: 'Analyze longitudinal trends across all accessible reports for this patient. Highlight deterioration, improvement, and recurring abnormalities.',
      mode: 'trend_analysis',
      workflow: 'Longitudinal Trend',
      filters: { report_scope: 'all_reports', max_fields: 120 },
    },
    {
      label: 'Critical Value Changes',
      prompt: 'Identify critical value changes over time for this patient using exact stored values where available.',
      mode: 'trend_analysis',
      workflow: 'Critical Value Changes',
      filters: { report_scope: 'all_reports', abnormal_only: true, max_fields: 120 },
    },
    {
      label: 'Continue to Free Discussion',
      prompt: 'Prepare a patient trend context summary for follow-up questions. Use only this patient accessible trend and report data.',
      mode: 'trend_analysis',
      workflow: 'Trend Free Discussion',
      filters: { report_scope: 'all_reports', max_fields: 120 },
    },
  ];

  const abnormalityActions: GuidedAction[] = [
    {
      label: 'Critical Abnormalities',
      prompt: 'Prioritize critical abnormalities for this patient and explain why they matter clinically.',
      mode: 'abnormality_review',
      workflow: 'Critical Abnormalities',
      filters: { abnormal_only: true, max_fields: 80 },
    },
    {
      label: 'High-Risk Values',
      prompt: 'Identify high-risk values for this patient from stored reports and summarize possible clinical concerns without making a diagnosis.',
      mode: 'abnormality_review',
      workflow: 'High-Risk Values',
      filters: { abnormal_only: true, max_fields: 80 },
    },
    {
      label: 'Confidence Warnings',
      prompt: 'Review fields with confidence warnings for this patient and explain what should be verified carefully.',
      mode: 'abnormality_review',
      workflow: 'Confidence Warnings',
      filters: { low_confidence_only: true, max_fields: 80 },
    },
    {
      label: 'Verification Needed Fields',
      prompt: 'List fields that appear to need doctor verification and explain priority order.',
      mode: 'abnormality_review',
      workflow: 'Verification Needed Fields',
      filters: { verification_needed_only: true, max_fields: 80 },
    },
    {
      label: 'Continue to Free Discussion',
      prompt: 'Prepare an abnormality review context for follow-up questions. Stay grounded in this patient stored reports.',
      mode: 'abnormality_review',
      workflow: 'Abnormality Free Discussion',
      filters: { abnormal_only: true, max_fields: 120 },
    },
  ];

  const populationActions: GuidedAction[] = [
    {
      label: 'Common Abnormalities',
      prompt: 'Summarize common abnormalities across my accessible patient population using aggregated analytics only.',
      mode: 'global_analytics',
      workflow: 'Common Abnormalities',
      filters: { global_scope: 'population_trends', anonymized: true },
    },
    {
      label: 'Diabetes Trends',
      prompt: 'Analyze diabetes-related trends across my accessible patient population using anonymized aggregate data.',
      mode: 'global_analytics',
      workflow: 'Diabetes Trends',
      filters: { global_scope: 'population_trends', topic: 'diabetes', anonymized: true },
    },
    {
      label: 'Thyroid Trends',
      prompt: 'Analyze thyroid-related trends across my accessible patient population using anonymized aggregate data.',
      mode: 'global_analytics',
      workflow: 'Thyroid Trends',
      filters: { global_scope: 'population_trends', topic: 'thyroid', anonymized: true },
    },
    {
      label: 'High-Risk Patterns',
      prompt: 'Summarize high-risk patterns across my accessible population without exposing unnecessary patient identity.',
      mode: 'global_analytics',
      workflow: 'High-Risk Patterns',
      filters: { global_scope: 'population_trends', topic: 'high_risk', anonymized: true },
    },
    {
      label: 'Age-Based Trends',
      prompt: 'Summarize age-based trend patterns across accessible patients using aggregate analytics only.',
      mode: 'global_analytics',
      workflow: 'Age-Based Trends',
      filters: { global_scope: 'population_trends', topic: 'age', anonymized: true },
    },
  ];

  const operationalActions: GuidedAction[] = [
    {
      label: 'Reports Processed Today',
      prompt: 'Summarize reports processed today across my accessible workflow.',
      mode: 'global_analytics',
      workflow: 'Reports Processed Today',
      filters: { global_scope: 'operational_analytics', metric: 'processed_today' },
    },
    {
      label: 'HITL Queue Analysis',
      prompt: 'Analyze my HITL queue and summarize workload priority areas.',
      mode: 'global_analytics',
      workflow: 'HITL Queue Analysis',
      filters: { global_scope: 'operational_analytics', metric: 'hitl_queue' },
    },
    {
      label: 'Verification Bottlenecks',
      prompt: 'Identify verification bottlenecks in my accessible report workflow.',
      mode: 'global_analytics',
      workflow: 'Verification Bottlenecks',
      filters: { global_scope: 'operational_analytics', metric: 'verification_bottlenecks' },
    },
    {
      label: 'Doctor Workload Insights',
      prompt: 'Summarize my doctor workload insights using accessible workflow analytics.',
      mode: 'global_analytics',
      workflow: 'Doctor Workload Insights',
      filters: { global_scope: 'operational_analytics', metric: 'doctor_workload' },
    },
    {
      label: 'Processing Time Analytics',
      prompt: 'Summarize processing time analytics and identify reports that may be delayed.',
      mode: 'global_analytics',
      workflow: 'Processing Time Analytics',
      filters: { global_scope: 'operational_analytics', metric: 'processing_time' },
    },
  ];

  const ocrActions: GuidedAction[] = [
    {
      label: 'Failed OCR Reports',
      prompt: 'Summarize failed OCR or failed processing reports in my accessible workflow.',
      mode: 'ocr_investigation',
      workflow: 'Failed OCR Reports',
      filters: { global_scope: 'ocr_failure_analysis', metric: 'failed_ocr' },
    },
    {
      label: 'Low Confidence Fields',
      prompt: 'Identify low confidence extraction patterns across my accessible reports.',
      mode: 'ocr_investigation',
      workflow: 'Low Confidence Fields',
      filters: { global_scope: 'ocr_failure_analysis', metric: 'low_confidence' },
    },
    {
      label: 'Extraction Quality Issues',
      prompt: 'Summarize extraction quality issues and likely causes across my accessible workflow.',
      mode: 'ocr_investigation',
      workflow: 'Extraction Quality Issues',
      filters: { global_scope: 'ocr_failure_analysis', metric: 'quality_issues' },
    },
    {
      label: 'Most Common OCR Failures',
      prompt: 'Summarize the most common OCR failure patterns across my accessible workflow.',
      mode: 'ocr_investigation',
      workflow: 'Most Common OCR Failures',
      filters: { global_scope: 'ocr_failure_analysis', metric: 'common_failures' },
    },
  ];

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
                <h2 className="text-sm font-semibold text-clinical-text-primary">HDMIS AI Clinical Assistant</h2>
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

      <div className="flex-1 space-y-4 overflow-y-auto bg-slate-50 p-4">
        <AssistantBubble>
          <div className="space-y-1">
            <p className="font-semibold">Hello Doctor 👋</p>
            <p>I&apos;m your HDMIS AI Clinical Assistant. Choose how you would like to continue.</p>
          </div>
        </AssistantBubble>

        {!primaryMode ? (
          <div className="space-y-2">
            <OptionButton
              label="Patient-Specific Mode"
              description="Analyze one selected patient only."
              onClick={() => selectPrimaryMode('patient')}
            />
            <OptionButton
              label="Global Analytics Mode"
              description="Use aggregated, anonymized workflow analytics."
              onClick={() => selectPrimaryMode('global')}
            />
          </div>
        ) : null}

        {primaryMode === 'patient' ? (
          <div className="space-y-4">
            <UserBubble>Patient-Specific Mode</UserBubble>
            <PatientSearchStep selectedPatient={selectedPatient} onSelectPatient={selectPatient} />

            {selectedPatient ? (
              <>
                <AssistantBubble>
                  <div>
                    <p className="font-semibold">{selectedPatient.full_name}</p>
                    <p className="font-mono text-xs text-clinical-text-secondary">{selectedPatient.patient_uid}</p>
                  </div>
                </AssistantBubble>

                {!patientWorkflow ? (
                  <div className="space-y-2">
                    <OptionButton label="Report Discussion" onClick={() => setPatientWorkflow('report')} />
                    <OptionButton label="Trend Analysis" onClick={() => setPatientWorkflow('trend')} />
                    <OptionButton label="Abnormality Review" onClick={() => setPatientWorkflow('abnormality')} />
                    <OptionButton
                      label="Free Chat"
                      description="Start with patient-wide context."
                      onClick={() => {
                        setPatientWorkflow('free');
                        void activateScopedPrompt({
                          label: 'Free Chat',
                          prompt: 'Prepare a patient-wide clinical context summary for follow-up questions. Use only this selected patient accessible stored reports.',
                          mode: 'patient_specific',
                          workflow: 'Patient Free Chat',
                          filters: { report_scope: 'all_reports', max_fields: 120 },
                        });
                      }}
                    />
                  </div>
                ) : null}

                {patientWorkflow === 'report' ? (
                  <div className="space-y-3">
                    <UserBubble>Report Discussion</UserBubble>
                    <AssistantBubble>Choose the report context. I&apos;ll summarize it first, then you can continue freely.</AssistantBubble>
                    <div className="flex flex-wrap gap-2">
                      {reportActions.map((action) => (
                        <QuickActionButton
                          key={action.label}
                          label={action.label}
                          disabled={doctorQuery.isPending}
                          onClick={() => void activateScopedPrompt(action)}
                        />
                      ))}
                    </div>
                    <div className="space-y-2 rounded-md border border-clinical-border bg-white p-3">
                      <p className="text-xs font-semibold uppercase text-clinical-text-secondary">Select Specific Report</p>
                      <div className="flex items-center gap-2 rounded-md border border-clinical-border px-3 py-2">
                        <Search className="h-4 w-4 text-clinical-text-muted" aria-hidden="true" />
                        <input
                          value={reportSearch}
                          onChange={(event) => setReportSearch(event.target.value)}
                          className="min-w-0 flex-1 text-sm outline-none"
                          placeholder="Search report filename or type"
                          aria-label="Search report"
                        />
                      </div>
                      <div className="max-h-36 space-y-1 overflow-y-auto">
                        {reportsQuery.isLoading ? <p className="text-xs text-clinical-text-secondary">Loading reports...</p> : null}
                        {!reportsQuery.isLoading && (reportsQuery.data ?? []).length === 0 ? (
                          <p className="text-xs text-clinical-text-secondary">No reports found for this patient.</p>
                        ) : null}
                        {(reportsQuery.data ?? []).slice(0, 8).map((report) => (
                          <button
                            key={report.report_id}
                            type="button"
                            className="w-full rounded-md border border-clinical-border px-3 py-2 text-left text-sm hover:border-clinical-primary"
                            disabled={doctorQuery.isPending}
                            onClick={() => void activateSpecificReport(report)}
                          >
                            <span className="block font-medium text-clinical-text-primary">{report.file_name}</span>
                            <span className="text-xs text-clinical-text-secondary">{reportLabel(report)}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}

                {patientWorkflow === 'trend' ? (
                  <div className="space-y-3">
                    <UserBubble>Trend Analysis</UserBubble>
                    <AssistantBubble>Choose a trend scope. I&apos;ll ground the answer in this patient&apos;s accessible records.</AssistantBubble>
                    <div className="flex flex-wrap gap-2">
                      {trendActions.map((action) => (
                        <QuickActionButton
                          key={action.label}
                          label={action.label}
                          disabled={doctorQuery.isPending}
                          onClick={() => void activateScopedPrompt(action)}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}

                {patientWorkflow === 'abnormality' ? (
                  <div className="space-y-3">
                    <UserBubble>Abnormality Review</UserBubble>
                    <AssistantBubble>Choose what to review first. I&apos;ll prioritize clinically important and verification-sensitive findings.</AssistantBubble>
                    <div className="flex flex-wrap gap-2">
                      {abnormalityActions.map((action) => (
                        <QuickActionButton
                          key={action.label}
                          label={action.label}
                          disabled={doctorQuery.isPending}
                          onClick={() => void activateScopedPrompt(action)}
                        />
                      ))}
                    </div>
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        ) : null}

        {primaryMode === 'global' ? (
          <div className="space-y-4">
            <UserBubble>Global Analytics Mode</UserBubble>
            {!globalWorkflow ? (
              <div className="space-y-2">
                <OptionButton label="Population Trends" onClick={() => setGlobalWorkflow('population')} />
                <OptionButton label="Operational Analytics" onClick={() => setGlobalWorkflow('operational')} />
                <OptionButton label="OCR Failure Analysis" onClick={() => setGlobalWorkflow('ocr')} />
                <OptionButton
                  label="Free Analytics Query"
                  description="Ask after aggregate analytics mode is selected."
                  onClick={() => {
                    setGlobalWorkflow('free');
                    setFreeChatEnabled(true);
                    setActiveScopeLabel('Free Analytics Query');
                    setActiveRequestMode('global_analytics');
                    setActiveFilters({ global_scope: 'free_analytics', anonymized: true });
                    inputRef.current?.focus();
                  }}
                />
              </div>
            ) : null}

            {globalWorkflow === 'population' ? (
              <div className="space-y-3">
                <UserBubble>Population Trends</UserBubble>
                <AssistantBubble>Choose a population analytics lens. Results should stay aggregated and anonymized.</AssistantBubble>
                <div className="flex flex-wrap gap-2">
                  {populationActions.map((action) => (
                    <QuickActionButton
                      key={action.label}
                      label={action.label}
                      disabled={doctorQuery.isPending}
                      onClick={() => void activateScopedPrompt(action)}
                    />
                  ))}
                </div>
              </div>
            ) : null}

            {globalWorkflow === 'operational' ? (
              <div className="space-y-3">
                <UserBubble>Operational Analytics</UserBubble>
                <AssistantBubble>Choose an operational view for your accessible workflow.</AssistantBubble>
                <div className="flex flex-wrap gap-2">
                  {operationalActions.map((action) => (
                    <QuickActionButton
                      key={action.label}
                      label={action.label}
                      disabled={doctorQuery.isPending}
                      onClick={() => void activateScopedPrompt(action)}
                    />
                  ))}
                </div>
              </div>
            ) : null}

            {globalWorkflow === 'ocr' ? (
              <div className="space-y-3">
                <UserBubble>OCR Failure Analysis</UserBubble>
                <AssistantBubble>Choose an extraction quality view. I&apos;ll avoid exposing internal embeddings or provider details.</AssistantBubble>
                <div className="flex flex-wrap gap-2">
                  {ocrActions.map((action) => (
                    <QuickActionButton
                      key={action.label}
                      label={action.label}
                      disabled={doctorQuery.isPending}
                      onClick={() => void activateScopedPrompt(action)}
                    />
                  ))}
                </div>
              </div>
            ) : null}
          </div>
        ) : null}

        {errorMessage ? (
          <div className="rounded-md border border-clinical-critical bg-clinical-critical-bg px-3 py-2 text-sm text-clinical-critical" role="alert">
            {errorMessage}
          </div>
        ) : null}

        {messages.map((message) => (
          <div
            key={`${message.timestamp}-${message.role}`}
            className={`rounded-lg px-3 py-2 text-sm ${
              message.role === 'user'
                ? 'ml-auto max-w-[86%] bg-clinical-primary text-white'
                : 'mr-auto max-w-[92%] border border-clinical-border bg-white text-clinical-text-primary shadow-sm'
            }`}
          >
            {message.role === 'user' ? message.content : null}
            {message.role === 'assistant' && message.reasoningResult ? <AssistantResponse response={message.reasoningResult} /> : null}
            {message.role === 'assistant' && message.trendResult ? <AssistantResponse response={message.trendResult} /> : null}
            {message.role === 'assistant' && message.retrievalResult ? <AssistantResponse response={message.retrievalResult} /> : null}
          </div>
        ))}

        {doctorQuery.isPending ? (
          <AssistantBubble>Retrieving scoped context...</AssistantBubble>
        ) : null}

        <div ref={messagesEndRef} />
      </div>

      <form
        className="border-t border-clinical-border bg-clinical-surface p-3"
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
            placeholder={freeChatEnabled ? 'Ask a follow-up in this scoped context' : 'Follow the guided options first'}
            disabled={!freeChatEnabled || doctorQuery.isPending}
            aria-label="Assistant prompt"
          />
          <Button
            type="submit"
            className="px-3"
            loading={doctorQuery.isPending}
            disabled={!freeChatEnabled || !input.trim()}
            aria-label="Send assistant prompt"
          >
            <Send className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      </form>
    </section>
  );
}
