import { isAxiosError } from 'axios';

export interface ApiError {
  code: string;
  message: string;
  fieldErrors?: Record<string, string>;
  retryable: boolean;
  statusCode: number;
  raw?: unknown;
}

export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'code' in error &&
    'message' in error &&
    'retryable' in error &&
    'statusCode' in error
  );
}

export function normalizeApiError(err: unknown): ApiError {
  if (isApiError(err)) {
    return err;
  }

  if (!isAxiosError(err)) {
    return {
      code: 'UNKNOWN',
      message: 'An unexpected error occurred.',
      retryable: false,
      statusCode: 0,
    };
  }

  const status = err.response?.status ?? 0;
  const data = err.response?.data as Record<string, unknown> | undefined;

  if (status === 409 && data?.duplicate_type === 'exact') {
    return {
      code: 'DUPLICATE_EXACT',
      message: String(data.detail ?? 'This file has already been uploaded.'),
      retryable: false,
      statusCode: 409,
      raw: data,
    };
  }

  if (status === 429) {
    return {
      code: 'RATE_LIMITED',
      message: 'Too many requests. Please wait before trying again.',
      retryable: true,
      statusCode: 429,
    };
  }

  if (status === 401) {
    return {
      code: 'UNAUTHORIZED',
      message: 'Session expired. Please log in again.',
      retryable: false,
      statusCode: 401,
    };
  }

  if (status === 422) {
    return {
      code: 'VALIDATION_ERROR',
      message: 'The submitted data is invalid.',
      fieldErrors: extractFieldErrors(data),
      retryable: false,
      statusCode: 422,
    };
  }

  if (status >= 500) {
    return {
      code: 'SERVER_ERROR',
      message: 'A server error occurred. Please try again.',
      retryable: true,
      statusCode: status,
    };
  }

  return {
    code: 'API_ERROR',
    message: String(data?.detail ?? 'An error occurred.'),
    retryable: false,
    statusCode: status,
    raw: data,
  };
}

function extractFieldErrors(data: unknown): Record<string, string> {
  if (!data || typeof data !== 'object' || !('detail' in data)) {
    return {};
  }

  const detail = (data as { detail?: unknown }).detail;
  if (!Array.isArray(detail)) {
    return {};
  }

  return Object.fromEntries(
    detail
      .filter(
        (entry): entry is { loc?: unknown[]; msg?: unknown } =>
          typeof entry === 'object' && entry !== null && 'msg' in entry,
      )
      .map((entry) => [
        String(entry.loc?.slice(-1)[0] ?? 'field'),
        String(entry.msg),
      ]),
  );
}
