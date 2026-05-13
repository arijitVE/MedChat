import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { Bot, FileText, HeartPulse, MessageSquarePlus, RefreshCw, Send } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Toast } from '../../components/ui/Toast';
import { useAuth } from '../../hooks/useAuth';
import { usePatientChat } from '../../hooks/useIntelligence';
import { useMyReports } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import { getReportDisplayName } from '../../lib/reportName';
import type { ChatMessage, PatientChatResult } from '../../types/intelligence';

const fallbackDisclaimer = 'This chat does not replace medical advice from your care team.';

function getLatestDisclaimer(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.patientResult?.disclaimer)?.patientResult?.disclaimer;
}

function AssistantBubble({ children }: { children: ReactNode }) {
  return (
    <div className="mr-auto max-w-3xl rounded-lg border border-clinical-border bg-white px-4 py-3 text-sm leading-6 text-clinical-text-primary shadow-sm">
      {children}
    </div>
  );
}

function UserBubble({ children }: { children: ReactNode }) {
  return (
    <div className="ml-auto max-w-2xl rounded-lg bg-clinical-primary px-4 py-3 text-sm leading-6 text-white">
      {children}
    </div>
  );
}

function GuidedOption({
  icon,
  label,
  description,
  active,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  description: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`w-full rounded-md border px-4 py-3 text-left text-sm transition hover:border-clinical-primary hover:bg-clinical-primary-light ${
        active ? 'border-clinical-primary bg-clinical-primary-light' : 'border-clinical-border bg-white'
      }`}
      onClick={onClick}
    >
      <span className="flex items-center gap-2 font-semibold text-clinical-text-primary">
        {icon}
        {label}
      </span>
      <span className="mt-1 block text-clinical-text-secondary">{description}</span>
    </button>
  );
}

function AssistantMessage({ result, content }: { result: PatientChatResult; content: string }) {
  return (
    <div className="max-w-3xl rounded-lg border border-clinical-border bg-clinical-muted p-4">
      {result.safety_blocked ? (
        <div className="mb-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          This request was blocked for safety.
        </div>
      ) : null}
      <p className="whitespace-pre-wrap text-sm leading-6 text-clinical-text-primary">{content}</p>
      {result.simplified_fields.length > 0 ? (
        <dl className="mt-4 grid gap-2 rounded-md border border-clinical-border bg-clinical-surface p-3 text-sm sm:grid-cols-2">
          {result.simplified_fields.map((field) => (
            <div key={`${field.name}-${field.value}`}>
              <dt className="font-medium text-clinical-text-primary">{field.name}</dt>
              <dd className="text-clinical-text-secondary">
                {field.value} · {field.status}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      <p className="mt-3 border-t border-clinical-border pt-3 text-xs text-clinical-text-secondary">
        {result.disclaimer}
      </p>
    </div>
  );
}

export default function PatientChatPage() {
  const { user } = useAuth();
  const patientChat = usePatientChat();
  const reports = useMyReports();
  const abortControllerRef = useRef<AbortController | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [contextMode, setContextMode] = useState<'general' | 'report' | null>(null);
  const [selectedReportId, setSelectedReportId] = useState('');
  const [input, setInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const disclaimer = getLatestDisclaimer(messages) ?? fallbackDisclaimer;
  const selectedReport = reports.data?.find((report) => report.report_id === selectedReportId);
  const canChat = Boolean(user && contextMode && (contextMode === 'general' || selectedReportId));

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || !user) {
      return;
    }
    if (!canChat) {
      setErrorMessage('Choose a conversation context first.');
      return;
    }

    abortControllerRef.current?.abort();
    const abortController = new AbortController();
    abortControllerRef.current = abortController;
    setInput('');
    setErrorMessage(null);

    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((current) => [...current, userMessage]);

    try {
      const result = await patientChat.mutateAsync({
        data: {
          text,
          patient_id: user.user_id,
          context_mode: contextMode ?? 'general',
          report_id: contextMode === 'report' ? selectedReportId : undefined,
        },
        signal: abortController.signal,
      });
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: result.response,
        patientResult: result,
        timestamp: new Date().toISOString(),
      };
      setMessages((current) => [...current, assistantMessage]);
    } catch (error) {
      if (!abortController.signal.aborted) {
        setErrorMessage(normalizeApiError(error).message);
      }
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Chat Assistant</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Ask about your reports in simple, safe language.</p>
      </div>

      <div className="sticky top-0 z-20 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950 shadow-sm">
        {disclaimer}
      </div>

      {errorMessage ? <Toast variant="error">{errorMessage}</Toast> : null}

      <Card className="flex min-h-[32rem] flex-col gap-4">
        <div className="flex-1 space-y-4 overflow-y-auto" role="log" aria-live="polite" aria-label="Patient chat messages">
          <AssistantBubble>
            <div className="space-y-1">
              <p className="flex items-center gap-2 font-semibold">
                <Bot className="h-4 w-4 text-clinical-primary" aria-hidden="true" />
                Hello, I&apos;m your HDIMS Health Assistant.
              </p>
              <p>Choose how you would like to continue.</p>
            </div>
          </AssistantBubble>

          {!contextMode ? (
            <div className="grid gap-3 md:grid-cols-2">
              <GuidedOption
                icon={<FileText className="h-4 w-4 text-clinical-primary" aria-hidden="true" />}
                label="Discuss a specific report"
                description="Select one report and keep answers focused on that report."
                active={contextMode === 'report'}
                onClick={() => setContextMode('report')}
              />
              <GuidedOption
                icon={<HeartPulse className="h-4 w-4 text-clinical-primary" aria-hidden="true" />}
                label="General Health discussion"
                description="Use your stored report history for broader health questions."
                active={contextMode === 'general'}
                onClick={() => {
                  setContextMode('general');
                  setSelectedReportId('');
                }}
              />
            </div>
          ) : null}

          {contextMode === 'general' ? (
            <>
              <UserBubble>General Health discussion</UserBubble>
              <AssistantBubble>
                General Health Discussion Mode is active. Ask about trends, past report values, or simple explanations from your stored reports.
              </AssistantBubble>
            </>
          ) : null}

          {contextMode === 'report' ? (
            <>
              <UserBubble>Discuss a specific report</UserBubble>
              <AssistantBubble>
                <div className="space-y-3">
                  <p>Select the report you want to discuss.</p>
                  <select
                    className="w-full rounded-md border border-clinical-border px-3 py-2 text-sm"
                    value={selectedReportId}
                    onChange={(event) => setSelectedReportId(event.target.value)}
                    aria-label="Select report context"
                  >
                    <option value="">Select a report</option>
                    {(reports.data ?? []).map((report) => (
                      <option key={report.report_id} value={report.report_id}>
                        {getReportDisplayName(report)}
                      </option>
                    ))}
                  </select>
                  {reports.isLoading ? <p className="text-xs text-clinical-text-secondary">Loading your reports...</p> : null}
                  {selectedReport ? (
                    <p className="rounded-md bg-clinical-primary-light px-3 py-2 text-xs font-medium text-clinical-primary">
                      Discussing: {getReportDisplayName(selectedReport)}
                    </p>
                  ) : null}
                </div>
              </AssistantBubble>
            </>
          ) : null}

          {contextMode ? (
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                className="min-h-9 px-3 py-1.5 text-xs"
                leftIcon={<RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />}
                onClick={() => {
                  setContextMode(null);
                  setSelectedReportId('');
                  setInput('');
                  setErrorMessage(null);
                }}
              >
                Change context
              </Button>
              <Button
                type="button"
                variant="ghost"
                className="min-h-9 px-3 py-1.5 text-xs"
                leftIcon={<MessageSquarePlus className="h-3.5 w-3.5" aria-hidden="true" />}
                onClick={() => {
                  setMessages([]);
                  setInput('');
                  setErrorMessage(null);
                }}
              >
                Start new conversation
              </Button>
            </div>
          ) : null}

          {messages.length > 0 ? (
            messages.map((message, index) => (
              <div
                key={`${message.timestamp}-${message.role}-${index}`}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && message.patientResult ? (
                  <AssistantMessage result={message.patientResult} content={message.content} />
                ) : (
                  <UserBubble>{message.content}</UserBubble>
                )}
              </div>
            ))
          ) : null}
          {patientChat.isPending ? (
            <div
              className="max-w-3xl rounded-lg border border-clinical-border bg-clinical-muted p-4 text-sm text-clinical-text-secondary"
              role="status"
              aria-live="polite"
            >
              Thinking...
            </div>
          ) : null}
        </div>

        <form
          className="flex gap-3 border-t border-clinical-border pt-4"
          onSubmit={(event) => {
            event.preventDefault();
            void sendMessage();
          }}
        >
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            className="min-h-10 flex-1 rounded-md border border-clinical-border px-3 py-2 text-sm text-clinical-text-primary focus:border-clinical-primary focus:outline-none focus:ring-2 focus:ring-clinical-primary/20"
            aria-label="Chat message"
            placeholder={canChat ? 'Ask a follow-up in this selected context' : 'Choose a context first'}
            disabled={!canChat || patientChat.isPending}
          />
          <Button
            type="submit"
            loading={patientChat.isPending}
            disabled={!input.trim() || !canChat}
            leftIcon={<Send className="h-4 w-4" aria-hidden="true" />}
          >
            Send
          </Button>
        </form>
      </Card>
    </div>
  );
}
