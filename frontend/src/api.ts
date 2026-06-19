let authToken: string | null = localStorage.getItem('token');
let unauthorizedCallback: (() => void) | null = null;

const BASE_URL = 'http://127.0.0.1:8000';

export function setAuthToken(token: string | null) {
  authToken = token;
  if (token) {
    localStorage.setItem('token', token);
  } else {
    localStorage.removeItem('token');
  }
}

export function getAuthToken() {
  return authToken;
}

export function onUnauthorized(callback: () => void) {
  unauthorizedCallback = callback;
}

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const headers = new Headers(options.headers || {});
  
  if (authToken) {
    headers.set('Authorization', `Bearer ${authToken}`);
  }
  
  if (!(options.body instanceof FormData)) {
    if (!headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json');
    }
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    setAuthToken(null);
    if (unauthorizedCallback) {
      unauthorizedCallback();
    }
    throw new Error('Unauthorized');
  }

  if (!response.ok) {
    let errorMessage = 'API Error';
    try {
      const errorData = await response.json();
      errorMessage = errorData.detail || errorMessage;
    } catch (e) {
      // Ignored
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  login: (data: any) => fetchWithAuth('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  signup: (data: any) => fetchWithAuth('/auth/signup', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  getMe: () => fetchWithAuth('/users/me'),
  
  listCases: () => fetchWithAuth('/api/v1/cases'),
  
  getCase: (caseId: string) => fetchWithAuth(`/api/v1/cases/${caseId}`),
  
  createCase: (data: { title: string; description?: string }) => fetchWithAuth('/api/v1/cases', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
  
  uploadDocument: (caseId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return fetchWithAuth(`/api/v1/cases/${caseId}/upload`, {
      method: 'POST',
      body: formData,
    });
  },
  
  processCase: (caseId: string) => fetchWithAuth(`/api/v1/cases/${caseId}/process`, {
    method: 'POST',
  }),
  
  getJobStatus: (caseId: string, jobId: string) => fetchWithAuth(`/api/v1/cases/${caseId}/jobs/${jobId}`),
  
  getSummary: (caseId: string) => fetchWithAuth(`/api/v1/cases/${caseId}/summary`),
  
  getOpinion: (caseId: string) => fetchWithAuth(`/api/v1/cases/${caseId}/opinion`),
  
  chatWithCase: (caseId: string, message: string) => fetchWithAuth(`/api/v1/cases/${caseId}/chat`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  }),
};
