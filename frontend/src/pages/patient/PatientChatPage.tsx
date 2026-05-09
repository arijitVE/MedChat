import { useEffect, useRef, useState } from 'react';
import { Send } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Toast } from '../../components/ui/Toast';
import { useAuth } from '../../hooks/useAuth';
import { usePatientChat } from '../../hooks/useIntelligence';
import { normalizeApiError } from '../../lib/apiError';
import type { ChatMessage, PatientChatResult } from '../../types/intelligence';

const fallbackDisclaimer = 'This chat does not replace medical advice from your care team.';

function getLatestDisclaimer(messages: ChatMessage[]) {
  return [...messages].reverse().find((message) => message.patientResult?.disclaimer)?.patientResult?.disclaimer;
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
  const abortControllerRef = useRef<AbortController | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const disclaimer = getLatestDisclaimer(messages) ?? fallbackDisclaimer;

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
        data: { text, patient_id: user.user_id },
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
        <h1 className="text-lg font-semibold text-clinical-text-primary">Patient Chat</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Ask about your released reports in plain language.</p>
      </div>

      <div className="sticky top-0 z-20 rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-950 shadow-sm">
        {disclaimer}
      </div>

      {errorMessage ? <Toast variant="error">{errorMessage}</Toast> : null}

      <Card className="flex min-h-[32rem] flex-col gap-4">
        <div className="flex-1 space-y-4 overflow-y-auto" role="log" aria-live="polite" aria-label="Patient chat messages">
          {messages.length === 0 ? (
            <div className="flex h-full min-h-72 items-center justify-center text-sm text-clinical-text-secondary">
              No messages yet.
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={`${message.timestamp}-${message.role}-${index}`}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {message.role === 'assistant' && message.patientResult ? (
                  <AssistantMessage result={message.patientResult} content={message.content} />
                ) : (
                  <div className="max-w-2xl rounded-lg bg-clinical-primary px-4 py-3 text-sm leading-6 text-white">
                    {message.content}
                  </div>
                )}
              </div>
            ))
          )}
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
            placeholder="Ask about your report"
          />
          <Button
            type="submit"
            loading={patientChat.isPending}
            disabled={!input.trim() || !user}
            leftIcon={<Send className="h-4 w-4" aria-hidden="true" />}
          >
            Send
          </Button>
        </form>
      </Card>
    </div>
  );
}
