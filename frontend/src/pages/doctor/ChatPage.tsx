import { useEffect, useRef, useState } from 'react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { normalizeApiError } from '../../lib/apiError';
import { useDoctorQuery } from '../../hooks/useIntelligence';
import {
  isReasoningResult,
  isRetrievalResult,
  isTrendResult,
  type ChatMessage,
  type DoctorQueryResponse,
} from '../../types/intelligence';

function AssistantResponse({ response }: { response: DoctorQueryResponse }) {
  if (isReasoningResult(response)) {
    return (
      <div className="space-y-2">
        <p>{response.interpretation}</p>
        <p className="text-sm text-clinical-text-secondary">{response.clinical_significance}</p>
        {response.critical_flags.length > 0 ? (
          <ul className="list-disc pl-5 text-sm text-clinical-critical">
            {response.critical_flags.map((flag) => <li key={flag}>{flag}</li>)}
          </ul>
        ) : null}
      </div>
    );
  }

  if (isTrendResult(response)) {
    return (
      <div>
        <p>{response.insight}</p>
        <p className="mt-1 text-sm text-clinical-text-secondary">
          Trend: {response.trend_direction}; points: {response.data_points.length}
        </p>
      </div>
    );
  }

  if (isRetrievalResult(response)) {
    return (
      <div>
        <p>{response.query_interpretation}</p>
        <p className="mt-1 text-sm text-clinical-text-secondary">
          {response.total_count} records found by {response.retrieval_type} retrieval.
        </p>
      </div>
    );
  }

  return null;
}

export default function ChatPage() {
  const [mode, setMode] = useState<'patient' | 'global'>('patient');
  const [patientId, setPatientId] = useState('');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const doctorQuery = useDoctorQuery();
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => abortControllerRef.current?.abort();
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || (mode === 'patient' && !patientId.trim())) {
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
    setMessages((current) => [...current, userMessage]);

    try {
      const response = await doctorQuery.mutateAsync({
        data: {
          text,
          patient_id: mode === 'patient' ? patientId.trim() : undefined,
        },
        signal: abortController.signal,
      });
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: isReasoningResult(response)
          ? response.interpretation
          : isTrendResult(response)
            ? response.insight
            : response.query_interpretation,
        reasoningResult: isReasoningResult(response) ? response : undefined,
        trendResult: isTrendResult(response) ? response : undefined,
        retrievalResult: isRetrievalResult(response) ? response : undefined,
        timestamp: new Date().toISOString(),
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch (error) {
      if (!abortController.signal.aborted) {
        setErrorMessage(normalizeApiError(error).message);
      }
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Doctor Chat</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Use patient-specific mode for scoped records, or global mode for aggregate workflow insights.</p>
      </div>

      <Card>
        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            className={`rounded-md border px-3 py-2 text-left text-sm ${mode === 'patient' ? 'border-clinical-primary bg-clinical-primary-light text-clinical-primary' : 'border-clinical-border text-clinical-text-secondary'}`}
            onClick={() => setMode('patient')}
          >
            Patient-Specific Mode
          </button>
          <button
            type="button"
            className={`rounded-md border px-3 py-2 text-left text-sm ${mode === 'global' ? 'border-clinical-primary bg-clinical-primary-light text-clinical-primary' : 'border-clinical-border text-clinical-text-secondary'}`}
            onClick={() => setMode('global')}
          >
            Global Analytics Mode
          </button>
        </div>
        {mode === 'patient' ? (
          <div className="mt-4">
            <label className="block text-sm font-medium text-clinical-text-primary" htmlFor="patient-id">
              Patient ID
            </label>
            <input
              id="patient-id"
              value={patientId}
              onChange={(event) => setPatientId(event.target.value)}
              className="mt-1 w-full rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            />
          </div>
        ) : null}
        <p className="mt-3 text-sm font-medium text-clinical-text-secondary">
          Active context: {mode === 'patient' ? `Patient-Specific Mode${patientId ? ` · ${patientId}` : ''}` : 'Global Analytics Mode'}
        </p>
      </Card>

      {errorMessage ? (
        <div className="rounded-md border border-clinical-critical bg-clinical-critical-bg px-4 py-3 text-sm text-clinical-critical" role="alert" aria-live="assertive">
          {errorMessage}
        </div>
      ) : null}

      <Card>
        <div className="h-[420px] space-y-3 overflow-y-auto" role="log" aria-live="polite" aria-label="Chat conversation">
          {messages.map((message) => (
            <div
              key={`${message.timestamp}-${message.role}`}
              className={`rounded-lg px-4 py-3 text-sm ${
                message.role === 'user'
                  ? 'ml-auto max-w-[80%] bg-clinical-primary text-white'
                  : 'mr-auto max-w-[80%] bg-slate-100 text-clinical-text-primary'
              }`}
            >
              {message.role === 'assistant' && message.reasoningResult ? <AssistantResponse response={message.reasoningResult} /> : null}
              {message.role === 'assistant' && message.trendResult ? <AssistantResponse response={message.trendResult} /> : null}
              {message.role === 'assistant' && message.retrievalResult ? <AssistantResponse response={message.retrievalResult} /> : null}
              {message.role === 'user' ? message.content : null}
            </div>
          ))}
          {doctorQuery.isPending ? (
            <div className="mr-auto max-w-[80%] rounded-lg bg-slate-100 px-4 py-3 text-sm text-clinical-text-secondary">
              <span className="inline-flex gap-1" aria-label="Assistant is typing">
                <span className="h-2 w-2 animate-pulse rounded-full bg-clinical-text-muted" />
                <span className="h-2 w-2 animate-pulse rounded-full bg-clinical-text-muted" />
                <span className="h-2 w-2 animate-pulse rounded-full bg-clinical-text-muted" />
              </span>
            </div>
          ) : null}
        </div>

        <form
          className="mt-4 flex gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            void sendMessage();
          }}
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            className="min-w-0 flex-1 rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            placeholder={mode === 'patient' ? 'Ask about this patient' : 'Ask about aggregate workflow trends'}
            aria-label="Chat message"
          />
          <Button type="submit" loading={doctorQuery.isPending} disabled={mode === 'patient' && !patientId.trim()}>
            Send
          </Button>
        </form>
      </Card>
    </div>
  );
}
