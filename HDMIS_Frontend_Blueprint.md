# HDMIS Frontend — Implementation Blueprint v4
### React + TypeScript Clinical Dashboard
### ⚠️ FINAL v4 — All 15 original gaps resolved + 13 production gaps addressed

---

## CHANGE LOG

### v1 → v2 (3 known gaps + 6 found on review)

| # | Gap | Fix Applied |
|---|-----|-------------|
| G1 | `Assignment` type undefined | Fully defined in `src/types/assignment.ts` |
| G2 | `AdminStats` type undefined | Fully defined in `src/types/admin.ts` |
| G3 | `ReportField.is_locked` conflicts with Product Layer FIX #3 | Replaced with `is_final: boolean` everywhere |
| G4 | `api/assignments.ts` never specified | Full typed API module added |
| G5 | `api/notifications.ts` never specified | Full typed API module added |
| G6 | `api/admin.ts` never specified | Full typed API module added |
| G7 | `uiStore.ts` never specified | Full Zustand store spec added |
| G8 | Duplicate upload flow (409 / TIER 2) had no UI handling | `DuplicateWarningModal` and force-upload flow added |
| G9 | `document_type` split (Product FIX 10) not reflected | `Report` type updated with both fields; filter UI updated |

### v2 → v3 (6 more gaps found by cross-referencing Pipeline B blueprint)

| # | Gap | Fix Applied |
|---|-----|-------------|
| G10 | `intelligenceApi.doctorQuery` return typed as `any` | `DoctorQueryResponse` union type added; `ChatWindow` renders typed fields |
| G11 | `PatientChatResult` has `simplified_fields[]` + top-level `disclaimer` string — missing from `intelligence.ts` | `PatientChatResult` type added; `ChatWindow` reads `result.disclaimer` directly |
| G12 | `AnalyticsResult` has `ai_insight` (not `insight`) + `abnormal_fields`/`normal_fields` as `ClinicalField[]` | `AnalyticsResult` type added; `AbnormalityPanel` props spec updated |
| G13 | `intelligenceApi.getAnalytics` return completely untyped | Now typed as `AnalyticsResult` |
| G14 | `NotificationItem` defined inside `api/notifications.ts` instead of `src/types/` | Moved to `src/types/notification.ts` |
| G15 | `ReasoningResult.citations` field missing from frontend type | Added `citations: string[]` to `ReasoningResult` type |

### v3 → v4 (13 production-readiness gaps addressed)

| # | Gap | Fix Applied |
|---|-----|-------------|
| P1 | No WebSocket abstraction — polling coupled directly to components | `RealtimeProvider` + `useRealtimeEvent` hook added; internally polls, ready for WebSocket swap |
| P2 | No resumable upload strategy documented | Roadmap section added; `UploadDropzone` exposes `onProgress`; chunked upload path noted |
| P3 | No optimistic UI strategy defined | React Query `onMutate`/`onError`/`onSettled` pattern mandated for notifications, field verification, assignment approval |
| P4 | No global API error normalization | `src/lib/apiError.ts` added; `ApiError` standard type; all components consume normalized errors |
| P5 | No query stale-time strategy | Query stale-time table added to Section 5; constants file `src/lib/queryKeys.ts` specified |
| P6 | No offline/error recovery UX | `NetworkDisconnectedBanner`, `RetryPanel`, `AutoReconnectIndicator` components added |
| P7 | `FileViewer` architecture underspecified | Full FileViewer spec: PDF page nav + zoom + skeleton; image pan + zoom + rotate |
| P8 | No accessibility rules | Accessibility standards section added: keyboard nav, ARIA, focus, screen reader |
| P9 | Notification model incomplete | Notification cache strategy: latest-first, max 50, dedupe by `notification_id`, unread count |
| P10 | No form validation schema strategy | `src/validation/` folder specified; named schema convention; shared validators |
| P11 | No frontend security hardening section | Security rules section added: no raw HTML, sanitize filenames, console hygiene, auth/CSP/token handling |
| P12 | No skeleton loader standard | Skeleton loader components added alongside Spinner; usage rules defined per component type |
| P13 | Auth weak for production (no refresh token) | Silent refresh strategy added; `httpOnly` cookie path documented; MVP vs production tiers documented |

### v4 review refinements (7 follow-up issues addressed)

| # | Issue | Fix Applied |
|---|-------|-------------|
| R1 | Browser developer-tool blocking was security theater | Removed entirely; frontend security now relies on real controls only |
| R2 | No observability architecture | Added Monitoring & Observability roadmap |
| R3 | Pagination lacked backend conventions | Added shared pagination params/response and endpoint rules |
| R4 | Notification polling could become wasteful | Added hidden-tab pause, focus resume, and exponential retry |
| R5 | Missing request cancellation patterns | Added Axios `signal` / `AbortController` conventions |
| R6 | Chat local state has healthcare retention limits | Added production persistence/audit roadmap note |
| R7 | Offline state too simple for production | Added queued mutation/draft persistence roadmap |

---

## AGENT INSTRUCTIONS — READ BEFORE WRITING ANY CODE

> This is the authoritative specification for the HDMIS React frontend.
> The backend (Pipeline A, Pipeline B, Product Layer) is fully built and tested.
> The frontend consumes the backend API — it does not contain any business logic.
> You are a coding agent. Follow every rule in this section strictly.

### Non-Negotiable Rules

1. **No business logic in the frontend.** All calculations, decisions, and data transformations happen in the backend. The frontend renders what the API returns.
2. **Every API call goes through the central API client.** Never use `fetch` directly in components. Always use the typed API client functions in `src/api/`.
3. **Auth token is stored in Zustand memory only.** Never store JWT in localStorage — it is an XSS vulnerability. On page refresh the user must log in again (MVP). See Section 19 for production refresh token upgrade path.
4. **Role-based rendering is enforced at the route level.** A patient cannot see doctor routes even if they navigate directly to the URL.
5. **No component fetches data directly.** Data fetching happens in page-level components or React Query hooks. Presentational components receive props only.
6. **TypeScript strict mode is on.** No `any` types. All API responses have typed interfaces matching the backend Pydantic models exactly.
7. **The design system is clinical.** White backgrounds, blue-grey palette, no decorative gradients, no dark mode. Readable at 100% zoom on a 1280px screen.
8. **All mutations use optimistic updates** (see Section 6 — Optimistic UI Strategy). No mutation may fire-and-wait without providing immediate feedback.
9. **All API errors are normalized through `src/lib/apiError.ts`.** No component reads raw Axios errors.
10. **No raw HTML rendering.** Never use `dangerouslySetInnerHTML`. Sanitize all user-provided content displayed back to user.

---

### Tech Stack

```
Framework:     React 18 + TypeScript (strict)
Build:         Vite
Styling:       Tailwind CSS (clinical palette only — see Section 2)
State:         React Query (server state) + Zustand (auth/UI state)
Routing:       React Router v6
Charts:        Recharts
Forms:         React Hook Form + Zod validation
HTTP:          Axios with interceptors
Icons:         Lucide React
PDF viewer:    react-pdf
Realtime:      Polling (P1: RealtimeProvider abstraction; WebSocket-ready)
```

---

### Mandatory Folder Structure

```
hdmis/frontend/
│
├── public/
│   └── favicon.ico
│
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   │
│   ├── api/
│   │   ├── client.ts
│   │   ├── auth.ts
│   │   ├── reports.ts
│   │   ├── verification.ts
│   │   ├── assignments.ts
│   │   ├── intelligence.ts
│   │   ├── notifications.ts
│   │   └── admin.ts
│   │
│   ├── types/
│   │   ├── common.ts             ← R3: pagination shared types
│   │   ├── auth.ts
│   │   ├── report.ts
│   │   ├── verification.ts
│   │   ├── assignment.ts
│   │   ├── intelligence.ts
│   │   ├── notification.ts       ← G14
│   │   └── admin.ts
│   │
│   ├── lib/
│   │   ├── apiError.ts           ← P4: normalized error type
│   │   ├── queryKeys.ts          ← P5: stale-time constants + key factories
│   │   └── sanitize.ts           ← P11: filename + content sanitization
│   │
│   ├── validation/               ← P10: Zod schemas
│   │   ├── authSchemas.ts
│   │   ├── uploadSchemas.ts
│   │   └── verificationSchemas.ts
│   │
│   ├── providers/
│   │   └── RealtimeProvider.tsx  ← P1: polling abstraction (WebSocket-ready)
│   │
│   ├── store/
│   │   ├── authStore.ts
│   │   └── uiStore.ts
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useReports.ts
│   │   ├── useVerification.ts
│   │   ├── useAssignments.ts
│   │   ├── useIntelligence.ts
│   │   ├── useNotifications.ts
│   │   └── useRealtimeEvent.ts   ← P1
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Topbar.tsx
│   │   │
│   │   ├── ui/
│   │   │   ├── Button.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Spinner.tsx
│   │   │   ├── Skeleton.tsx      ← P12: skeleton loader primitives
│   │   │   ├── EmptyState.tsx
│   │   │   └── Pagination.tsx
│   │   │
│   │   ├── feedback/             ← P6: network/error recovery
│   │   │   ├── NetworkDisconnectedBanner.tsx
│   │   │   ├── RetryPanel.tsx
│   │   │   └── AutoReconnectIndicator.tsx
│   │   │
│   │   ├── report/
│   │   │   ├── ReportCard.tsx
│   │   │   ├── ReportStatusBadge.tsx
│   │   │   ├── FieldsTable.tsx
│   │   │   ├── FieldRow.tsx
│   │   │   ├── FileViewer.tsx    ← P7: full spec
│   │   │   ├── UploadDropzone.tsx
│   │   │   └── DuplicateWarningModal.tsx
│   │   │
│   │   ├── charts/
│   │   │   ├── TrendLineChart.tsx
│   │   │   ├── FieldBarChart.tsx
│   │   │   └── AbnormalityPanel.tsx
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   └── ChatInput.tsx
│   │   │
│   │   └── notifications/
│   │       ├── NotificationBell.tsx
│   │       └── NotificationPanel.tsx
│   │
│   └── pages/
│       ├── auth/
│       │   ├── LoginPage.tsx
│       │   └── SignupPage.tsx
│       │
│       ├── doctor/
│       │   ├── DoctorDashboard.tsx
│       │   ├── PatientListPage.tsx
│       │   ├── PatientDetailPage.tsx
│       │   ├── ReportDetailPage.tsx
│       │   ├── UploadPage.tsx
│       │   ├── HITLQueuePage.tsx
│       │   ├── AnalyticsPage.tsx
│       │   └── ChatPage.tsx
│       │
│       ├── patient/
│       │   ├── PatientDashboard.tsx
│       │   ├── MyReportsPage.tsx
│       │   ├── ReportViewPage.tsx
│       │   ├── TrendsPage.tsx
│       │   └── PatientChatPage.tsx
│       │
│       └── admin/
│           ├── AdminDashboard.tsx
│           ├── UsersPage.tsx
│           └── HITLOverviewPage.tsx
│
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 2. Design System

### Clinical Color Palette (Tailwind config)

```typescript
// tailwind.config.ts
colors: {
  clinical: {
    primary:          '#1D4ED8',   // blue-700
    'primary-light':  '#DBEAFE',   // blue-100
    'primary-dark':   '#1E3A8A',   // blue-900
    bg:               '#F8FAFC',   // slate-50
    surface:          '#FFFFFF',
    border:           '#E2E8F0',   // slate-200
    'text-primary':   '#0F172A',   // slate-900
    'text-secondary': '#475569',   // slate-600
    'text-muted':     '#94A3B8',   // slate-400
    auto:             '#16A34A',   // green-600
    'auto-bg':        '#DCFCE7',   // green-100
    hitl:             '#D97706',   // amber-600
    'hitl-bg':        '#FEF3C7',   // amber-100
    verified:         '#1D4ED8',   // blue-700
    'verified-bg':    '#DBEAFE',   // blue-100
    final:            '#7C3AED',   // violet-600
    'final-bg':       '#EDE9FE',   // violet-100
    critical:         '#DC2626',   // red-600
    'critical-bg':    '#FEE2E2',   // red-100
    warning:          '#D97706',   // amber-600
    normal:           '#16A34A',   // green-600
    offline:          '#6B7280',   // gray-500  ← P6
    'offline-bg':     '#F3F4F6',   // gray-100  ← P6
  }
}
```

### Typography + Component Conventions

```
Font:       Inter (Google Fonts) — 14px base
Cards:      white bg, 1px clinical-border, rounded-lg, p-6, shadow-sm
Tables:     white bg, border, rounded-lg, text-sm, row hover bg-slate-50
Buttons:    rounded-md, px-4 py-2, text-sm, font-medium
Badges:     rounded-full, px-2 py-0.5, text-xs, font-medium
Modals:     white, rounded-xl, shadow-xl, max-w-lg, centered overlay
Sidebar:    w-64, white bg, border-r clinical-border
Topbar:     h-14, white bg, border-b clinical-border
Skeleton:   bg-slate-200 animate-pulse rounded (P12)
```

### Skeleton Loader Standards (P12)

Skeleton loaders are mandatory on all async content. Use `Spinner` only for actions (button submit, inline loading). Use `Skeleton` for content areas.

```
Content Type      Skeleton Shape
─────────────────────────────────────────────
Table rows        Full-width rectangle h-10, 8 rows
Report cards      Card-shaped block h-24
Stat cards        Rectangle h-16, w-full
FileViewer        Full panel h-full bg-slate-100
Analytics chart   Rectangle h-48
Chat messages     Two alternating bubble shapes
Field list        Rectangle rows h-8 × 6
```

Rules: Never show an empty table while loading — always show skeleton rows. `FileViewer` must show skeleton while PDF loads pages.

---

## 3. TypeScript Types (Mirror Backend Exactly)

### src/types/common.ts

```typescript
export interface PaginationParams {
  /** 1-based page number. Omit only when endpoint is intentionally unpaginated. */
  page?: number;
  /** Defaults to 20. Frontend must not request more than 100. */
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}
```

### src/types/auth.ts

```typescript
export interface User {
  user_id: string;
  email: string;
  role: 'doctor' | 'patient' | 'admin';
  full_name: string;
  patient_uid?: string;
  license_number?: string;
  specialization?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface SignupRequest {
  email: string;
  password: string;
  role: 'doctor' | 'patient';
  full_name: string;
  phone?: string;
  license_number?: string;
  date_of_birth?: string;
  sex?: string;
  claim_patient_uid?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}
```

### src/types/report.ts

```typescript
export type LifecycleStatus =
  | 'uploaded' | 'processing' | 'auto_approved'
  | 'hitl_required' | 'patient_verified'
  | 'doctor_verified' | 'fully_verified';

export type FieldPipelineStatus = 'auto' | 'hitl';

export interface Report {
  report_id: string;
  job_id: string;
  patient_id: string;
  uploaded_by: string;
  file_name: string;
  file_mime: string;
  upload_document_type: string;           // G9
  inferred_document_type: string;         // G9
  lifecycle_status: LifecycleStatus;
  released_to_patient: boolean;
  first_uploaded_at: string;
  last_edited_at: string | null;
  upload_count: number;
  is_duplicate: boolean;
  duplicate_of: string | null;
  duplicate_warning?: DuplicateWarning | null;  // G8
}

export interface DuplicateWarning {
  type: 'probable';
  existing_report_id: string;
  existing_uploaded_at: string;
  uploaded_by_role: 'doctor' | 'patient';
  message: string;
}

export interface ExactDuplicateError {
  detail: string;
  duplicate_type: 'exact';
  existing_report_id: string;
  existing_uploaded_at: string;
  uploaded_by_role: 'doctor' | 'patient';
  uploaded_by_user_id: string;
}

export interface ReportField {
  field_name: string;
  value: string | null;
  display_value: string;
  numeric_value: number | null;
  unit: string | null;
  reference_range: string | null;
  ref_low: number | null;
  ref_high: number | null;
  confidence: number;
  pipeline_status: FieldPipelineStatus;
  patient_verified: boolean;
  doctor_verified: boolean;
  is_final: boolean;                      // G3: replaces is_locked
  eda_available: boolean;
  is_abnormal: boolean | null;
}

export interface FieldVerifyRequest {
  verification_type: 'approved' | 'edited' | 'rejected';
  edited_value?: string;
  edit_reason?: string;
}
```

### src/types/verification.ts

```typescript
export type VerificationType = 'approved' | 'edited' | 'rejected';

export interface FieldVerification {
  verification_id: string;
  field_name: string;
  field_value: string | null;
  edited_value: string | null;
  verifier_role: 'doctor' | 'patient';
  verification_type: VerificationType;
  is_final: boolean;
  verified_at: string;
}
```

### src/types/assignment.ts

```typescript
export type AssignmentStatus = 'pending' | 'active' | 'rejected';

export interface Assignment {
  assignment_id: string;
  doctor_id: string;
  patient_id: string;
  assigned_by: 'admin' | 'doctor' | 'patient';
  status: AssignmentStatus;
  created_at: string;
  updated_at: string;
}

export interface DoctorProfile {
  user_id: string;
  full_name: string;
  email: string;
  license_number: string | null;
  specialization: string | null;
}

export interface PatientProfile {
  user_id: string;
  full_name: string;
  email: string;
  patient_uid: string;
  date_of_birth: string | null;
  sex: string | null;
}

export interface AssignmentRequest {
  doctor_id: string;
  patient_id: string;
}
```

### src/types/notification.ts

```typescript
export interface NotificationItem {
  notification_id: string;
  type: string;
  title: string;
  message: string;
  report_id: string | null;
  is_read: boolean;
  created_at: string;
}
```

### src/types/admin.ts

```typescript
export interface AdminStats {
  total_doctors: number;
  total_patients: number;
  total_reports: number;
  processing_now: number;
  hitl_pending: number;
  fully_verified: number;
  assignments_active: number;
  assignments_pending: number;
}

export interface HITLQueueItem {
  report_id: string;
  patient_name: string;
  patient_uid: string;
  doctor_name: string;
  report_date: string;
  fields_pending: number;
  days_waiting: number;
}

export interface UserListItem {
  user_id: string;
  full_name: string;
  email: string;
  role: 'doctor' | 'patient' | 'admin';
  patient_uid: string | null;
  license_number: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PasswordResetRequest {
  user_id: string;
  new_password: string;
}
```

### src/types/intelligence.ts

```typescript
export interface TrendPoint {
  date: string;
  value: string;
  numeric_value: number | null;
  unit: string | null;
  is_abnormal: boolean | null;
}

export interface ChartMeta {
  label: string;
  unit: string;
  ref_low: number | null;
  ref_high: number | null;
}

export interface ClinicalField {
  field_id: string;
  job_id: string;
  patient_id: string;
  name: string;
  raw_name: string;
  value: string;
  numeric_value: number | null;
  unit: string | null;
  reference_range: string | null;
  ref_low: number | null;
  ref_high: number | null;
  confidence: number;
  status: string;
  is_abnormal: boolean | null;
}

export interface TrendResult {
  field_name: string;
  patient_id: string;
  data_points: TrendPoint[];
  trend_direction: 'increasing' | 'decreasing' | 'stable' | 'insufficient_data';
  percent_change: number | null;
  chart_json: {
    type: string;
    data: { x: string[]; y: number[] };
    meta: ChartMeta;
  };
  insight: string;
  cached: boolean;
}

export interface ReasoningResult {
  interpretation: string;
  clinical_significance: string;
  possible_conditions: string[];
  critical_flags: string[];
  confidence: number;
  citations: string[];             // G15
  cached: boolean;
}

export interface RetrievalResult {
  records: Record<string, unknown>[];
  total_count: number;
  query_interpretation: string;
  retrieval_type: 'filter' | 'semantic';
}

export type DoctorQueryResponse = ReasoningResult | TrendResult | RetrievalResult;

export function isReasoningResult(r: DoctorQueryResponse): r is ReasoningResult {
  return 'interpretation' in r;
}
export function isTrendResult(r: DoctorQueryResponse): r is TrendResult {
  return 'data_points' in r;
}
export function isRetrievalResult(r: DoctorQueryResponse): r is RetrievalResult {
  return 'records' in r;
}

export interface SimplifiedField {
  name: string;
  value: string;
  status: string;
}

export interface PatientChatResult {
  response: string;
  simplified_fields: SimplifiedField[];
  disclaimer: string;              // G11: top-level field, not text keyword
  safety_blocked: boolean;
}

export interface AnalyticsResult {
  patient_id: string;
  abnormal_fields: ClinicalField[];
  normal_fields: ClinicalField[];
  abnormal_count: number;
  normal_count: number;
  chart_json: {
    type: string;
    data: {
      fields: string[];
      values: number[];
      ref_low: (number | null)[];
      ref_high: (number | null)[];
    };
    meta: { patient_id: string; date: string };
  };
  ai_insight: string;              // G12: NOT `insight`
  cached: boolean;
}

export interface DoctorQueryRequest {
  text: string;
  patient_id?: string;
}

export interface PatientChatRequest {
  text: string;
  patient_id: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  reasoningResult?: ReasoningResult;
  trendResult?: TrendResult;
  retrievalResult?: RetrievalResult;
  patientResult?: PatientChatResult;
  timestamp: string;
}
```

---

## 4. API Error Normalization (P4)

### src/lib/apiError.ts

```typescript
export interface ApiError {
  code: string;          // e.g. 'DUPLICATE_EXACT', 'RATE_LIMITED', 'UNAUTHORIZED'
  message: string;       // human-readable
  fieldErrors?: Record<string, string>;  // validation errors keyed by field name
  retryable: boolean;    // safe to retry?
  statusCode: number;
  raw?: unknown;         // original error for debugging (never shown to user)
}

export function normalizeApiError(err: unknown): ApiError {
  if (!isAxiosError(err)) {
    return { code: 'UNKNOWN', message: 'An unexpected error occurred.',
             retryable: false, statusCode: 0 };
  }
  const status = err.response?.status ?? 0;
  const data = err.response?.data as Record<string, unknown> | undefined;

  if (status === 409 && data?.duplicate_type === 'exact') {
    return { code: 'DUPLICATE_EXACT', message: data.detail as string,
             retryable: false, statusCode: 409, raw: data };
  }
  if (status === 429) {
    return { code: 'RATE_LIMITED',
             message: 'Too many requests. Please wait before trying again.',
             retryable: true, statusCode: 429 };
  }
  if (status === 401) {
    return { code: 'UNAUTHORIZED', message: 'Session expired. Please log in again.',
             retryable: false, statusCode: 401 };
  }
  if (status === 422) {
    return { code: 'VALIDATION_ERROR',
             message: 'The submitted data is invalid.',
             fieldErrors: extractFieldErrors(data),
             retryable: false, statusCode: 422 };
  }
  if (status >= 500) {
    return { code: 'SERVER_ERROR',
             message: 'A server error occurred. Please try again.',
             retryable: true, statusCode: status };
  }
  return { code: 'API_ERROR',
           message: (data?.detail as string) ?? 'An error occurred.',
           retryable: false, statusCode: status, raw: data };
}

function extractFieldErrors(data: unknown): Record<string, string> {
  // Parse FastAPI 422 detail array → { field: message } map
  if (!data || typeof data !== 'object' || !('detail' in data)) return {};
  const detail = (data as { detail?: unknown }).detail;
  if (!Array.isArray(detail)) return {};

  return Object.fromEntries(
    detail
      .filter((e): e is { loc?: unknown[]; msg?: unknown } =>
        typeof e === 'object' && e !== null && 'msg' in e)
      .map((e) => [String(e.loc?.slice(-1)[0] ?? 'field'), String(e.msg)])
  );
}
```

**Rules:** Every `catch` block in every hook and component calls `normalizeApiError(err)` and works with `ApiError`. No component reads `err.response?.data` directly.

---

## 5. Query Keys + Stale-Time Strategy (P5)

### src/lib/queryKeys.ts

```typescript
export const queryKeys = {
  reports: {
    all: ['reports'] as const,
    detail: (id: string) => ['reports', id] as const,
    fields: (id: string) => ['reports', id, 'fields'] as const,
    rawFile: (id: string) => ['reports', id, 'raw-file'] as const,
    forPatient: (patientId: string) => ['reports', 'patient', patientId] as const,
  },
  patients: {
    all: ['patients'] as const,
    detail: (id: string) => ['patients', id] as const,
    profile: (id: string) => ['patients', id, 'profile'] as const,
    analytics: (id: string) => ['patients', id, 'analytics'] as const,
    trend: (id: string, field: string) => ['patients', id, 'trend', field] as const,
  },
  notifications: {
    all: (role: string) => ['notifications', role] as const,
  },
  admin: {
    stats: ['admin', 'stats'] as const,
    users: (filters?: object) => ['admin', 'users', filters] as const,
    hitlQueue: ['admin', 'hitl'] as const,
  },
  hitlQueue: (myPatientsOnly: boolean) => ['hitl-queue', myPatientsOnly] as const,
} as const;

// Stale-time constants (milliseconds)
export const staleTime = {
  reportDetail:      30_000,    // 30s — may update during processing
  reportFields:      30_000,    // 30s
  notifications:     60_000,    // 60s — realtime provider handles faster updates
  adminStats:        30_000,    // 30s
  analytics:        300_000,    // 5m — expensive computation, cached backend
  trends:           300_000,    // 5m
  patientList:       60_000,    // 60s
  hitlQueue:         30_000,    // 30s — action-critical
  usersList:         60_000,    // 60s
} as const;
```

**Usage pattern in hooks:**

```typescript
// useReports.ts example
export function useReportDetail(reportId: string) {
  return useQuery({
    queryKey: queryKeys.reports.detail(reportId),
    queryFn: () => reportsApi.getReport(reportId).then(r => r.data),
    staleTime: staleTime.reportDetail,
  });
}
```

### Pagination Standards (R3)

All paginated backend list endpoints use offset pagination for MVP.

```
Rule                     Specification
─────────────────────────────────────────────────────────────────
Page parameter           page
Page numbering           1-based
Page size parameter      page_size
Default page size        20
Max frontend page size   100
Response shape           PaginatedResponse<T> from src/types/common.ts
Infinite scroll          Not used for MVP tables; use Pagination component
Cursor pagination        Future only: activity feeds, audit logs, chat history
```

Do not introduce endpoint-specific pagination shapes. If the backend later exposes cursor pagination for feed-like data, add a separate `CursorPaginatedResponse<T>` instead of overloading `PaginatedResponse<T>`.

---

## 6. Optimistic UI Strategy (P3)

All mutations that update frequently-touched data must use optimistic updates. Use React Query's `onMutate`/`onError`/`onSettled` pattern.

### Mandatory Optimistic Mutations

**Mark Notification Read:**

```typescript
useMutation({
  mutationFn: (id: string) => notificationsApi.markDoctorRead(id),
  onMutate: async (id) => {
    await queryClient.cancelQueries({ queryKey: queryKeys.notifications.all(role) });
    const prev = queryClient.getQueryData(queryKeys.notifications.all(role));
    queryClient.setQueryData(queryKeys.notifications.all(role),
      (old: NotificationItem[]) =>
        old.map(n => n.notification_id === id ? { ...n, is_read: true } : n));
    return { prev };
  },
  onError: (_err, _id, ctx) => {
    queryClient.setQueryData(queryKeys.notifications.all(role), ctx?.prev);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all(role) });
  },
})
```

**Approve/Reject Assignment:**

Same pattern — optimistically update `status` field in the assignments list cache; rollback on error.

**Field Verify (doctor):**

Optimistically mark `is_final: true` + `doctor_verified: true` on the field in the cache immediately. Rollback if the API call fails. This eliminates the visible delay after clicking "Verify".

**General Rule:** Any mutation that changes data the user is currently viewing must be optimistic. Mutations that navigate away on success (upload, create) do not need optimistic updates.

---

## 7. API Client

### src/api/client.ts

```typescript
import axios from 'axios';
import { useAuthStore } from '../store/authStore';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// P13: Production upgrade — when refresh token is implemented,
// add silent refresh logic here BEFORE the 401 redirect.
// See Section 19 for the full refresh token upgrade path.
```

### Request Cancellation Standards (R5)

All route-sensitive or rapid-input requests must accept an Axios `signal` option and be cancellable via `AbortController` or React Query's provided query signal.

```
Request type              Required cancellation behavior
─────────────────────────────────────────────────────────────────
Patient search            Abort previous request as the search term changes
Doctor/patient chat       Abort in-flight request on route leave or new send
Analytics/trend switching Abort previous field/patient query before rendering new result
File blob loading         Abort raw-file request on report change or unmount
React Query queries       Pass queryFn signal into the API function when available
```

Canceled requests must not show error toasts or overwrite newer state. Treat Axios cancellation as a neutral outcome.

### src/api/auth.ts

```typescript
import { apiClient } from './client';
import type { TokenResponse, SignupRequest, LoginRequest } from '../types/auth';

export const authApi = {
  signup: (data: SignupRequest) =>
    apiClient.post<TokenResponse>('/auth/signup', data),
  login: (data: LoginRequest) =>
    apiClient.post<TokenResponse>('/auth/login', data),
  logout: () =>
    apiClient.post('/auth/logout'),
  refresh: () =>
    apiClient.post<TokenResponse>('/auth/refresh'),
};
```

### src/api/reports.ts

```typescript
import type { AxiosRequestConfig } from 'axios';
import { apiClient } from './client';
import type { Report, ReportField } from '../types/report';

type RequestOptions = Pick<AxiosRequestConfig, 'signal'>;

export const reportsApi = {
  upload: (formData: FormData, force?: boolean) =>
    apiClient.post<Report>(
      `/doctor/upload${force ? '?force=true' : ''}`, formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    ),
  getReport: (reportId: string) =>
    apiClient.get<Report>(`/doctor/reports/${reportId}`),
  getReportFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/doctor/reports/${reportId}/fields`),
  getRawFile: (reportId: string, options?: RequestOptions) =>
    apiClient.get(`/doctor/reports/${reportId}/raw-file`, {
      responseType: 'blob',
      signal: options?.signal,
    }),
  releaseToPatient: (reportId: string) =>
    apiClient.post(`/doctor/reports/${reportId}/release`),
  reupload: (reportId: string, formData: FormData, force?: boolean) =>
    apiClient.put(
      `/doctor/reports/${reportId}/reupload${force ? '?force=true' : ''}`,
      formData, { headers: { 'Content-Type': 'multipart/form-data' } }
    ),
  getDoctorPatientReports: (patientId: string) =>
    apiClient.get<Report[]>(`/doctor/patients/${patientId}/reports`),
  getDashboard: () =>
    apiClient.get('/doctor/dashboard'),
  searchPatients: (q: string, options?: RequestOptions) =>
    apiClient.get('/doctor/patients/search', { params: { q }, signal: options?.signal }),
  getHITLQueue: (myPatientsOnly?: boolean) =>
    apiClient.get('/doctor/hitl-queue', { params: { my_patients_only: myPatientsOnly } }),
  patientUpload: (formData: FormData, force?: boolean) =>
    apiClient.post<Report>(
      `/patient/upload${force ? '?force=true' : ''}`, formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    ),
  getMyReports: (params?: { date_from?: string; date_to?: string; document_type?: string }) =>
    apiClient.get<Report[]>('/patient/reports', { params }),
  getMyReport: (reportId: string) =>
    apiClient.get<Report>(`/patient/reports/${reportId}`),
  getMyReportFields: (reportId: string) =>
    apiClient.get<ReportField[]>(`/patient/reports/${reportId}/fields`),
  getMyReportRawFile: (reportId: string, options?: RequestOptions) =>
    apiClient.get(`/patient/reports/${reportId}/raw-file`, {
      responseType: 'blob',
      signal: options?.signal,
    }),
  patientReupload: (reportId: string, formData: FormData, force?: boolean) =>
    apiClient.put(
      `/patient/reports/${reportId}/reupload${force ? '?force=true' : ''}`,
      formData, { headers: { 'Content-Type': 'multipart/form-data' } }
    ),
};
```

### src/api/verification.ts

```typescript
import { apiClient } from './client';
import type { FieldVerification } from '../types/verification';
import type { FieldVerifyRequest } from '../types/report';

export const verificationApi = {
  verifyField: (reportId: string, fieldName: string, data: FieldVerifyRequest) =>
    apiClient.post<FieldVerification>(
      `/doctor/reports/${reportId}/fields/${fieldName}/verify`, data
    ),
  patientVerifyField: (reportId: string, fieldName: string, data: FieldVerifyRequest) =>
    apiClient.post<FieldVerification>(
      `/patient/reports/${reportId}/fields/${fieldName}/verify`, data
    ),
};
```

### src/api/assignments.ts

```typescript
import { apiClient } from './client';
import type { Assignment, AssignmentRequest, PatientProfile } from '../types/assignment';
import type { PaginationParams, PaginatedResponse } from '../types/common';

export const assignmentsApi = {
  createAssignment: (data: AssignmentRequest) =>
    apiClient.post<Assignment>('/doctor/assignments', data),
  getDoctorAssignments: () =>
    apiClient.get<Assignment[]>('/doctor/assignments'),
  approveAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/doctor/assignments/${assignmentId}/approve`),
  rejectAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/doctor/assignments/${assignmentId}/reject`),
  getDoctorPatients: (params: PaginationParams = {}) =>
    apiClient.get<PaginatedResponse<PatientProfile>>('/doctor/patients', {
      params: { page: 1, page_size: 20, ...params },
    }),
  getPatientProfile: (patientId: string) =>
    apiClient.get<PatientProfile>(`/doctor/patients/${patientId}/profile`),
  createPatientAssignment: (data: AssignmentRequest) =>
    apiClient.post<Assignment>('/patient/assignments', data),
  getPatientAssignments: () =>
    apiClient.get<Assignment[]>('/patient/assignments'),
  patientApproveAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/patient/assignments/${assignmentId}/approve`),
  patientRejectAssignment: (assignmentId: string) =>
    apiClient.put<Assignment>(`/patient/assignments/${assignmentId}/reject`),
  adminCreateAssignment: (data: AssignmentRequest) =>
    apiClient.post<Assignment>('/admin/assignments', data),
};
```

### src/api/intelligence.ts

```typescript
import type { AxiosRequestConfig } from 'axios';
import { apiClient } from './client';
import type {
  DoctorQueryRequest, PatientChatRequest,
  DoctorQueryResponse, PatientChatResult,
  TrendResult, AnalyticsResult,
} from '../types/intelligence';

type RequestOptions = Pick<AxiosRequestConfig, 'signal'>;

export const intelligenceApi = {
  doctorQuery: (data: DoctorQueryRequest, options?: RequestOptions) =>
    apiClient.post<DoctorQueryResponse>('/doctor/query', data, { signal: options?.signal }),
  getTrend: (patientId: string, fieldName: string, options?: RequestOptions) =>
    apiClient.get<TrendResult>(`/doctor/patients/${patientId}/trend`, {
      params: { field_name: fieldName },
      signal: options?.signal,
    }),
  getAnalytics: (patientId: string, options?: RequestOptions) =>
    apiClient.get<AnalyticsResult>(`/doctor/patients/${patientId}/analytics`, {
      signal: options?.signal,
    }),
  patientChat: (data: PatientChatRequest, options?: RequestOptions) =>
    apiClient.post<PatientChatResult>('/patient/chat', data, { signal: options?.signal }),
  getMyTrends: (fieldName: string, options?: RequestOptions) =>
    apiClient.get<TrendResult>('/patient/trends', {
      params: { field_name: fieldName },
      signal: options?.signal,
    }),
  getMyEDA: (reportId: string) =>
    apiClient.get(`/patient/reports/${reportId}/eda`),
};
```

### src/api/notifications.ts

```typescript
import { apiClient } from './client';
import type { NotificationItem } from '../types/notification';

export { type NotificationItem };

export const notificationsApi = {
  getDoctorNotifications: () =>
    apiClient.get<NotificationItem[]>('/doctor/notifications'),
  markDoctorRead: (notificationId: string) =>
    apiClient.put(`/doctor/notifications/${notificationId}/read`),
  getPatientNotifications: () =>
    apiClient.get<NotificationItem[]>('/patient/notifications'),
  markPatientRead: (notificationId: string) =>
    apiClient.put(`/patient/notifications/${notificationId}/read`),
};
```

### src/api/admin.ts

```typescript
import { apiClient } from './client';
import type { AdminStats, HITLQueueItem, UserListItem, PasswordResetRequest } from '../types/admin';
import type { PaginationParams, PaginatedResponse } from '../types/common';

type UserListParams = PaginationParams & { role?: 'doctor' | 'patient' | 'admin' };

export const adminApi = {
  getStats: () =>
    apiClient.get<AdminStats>('/admin/stats'),
  getUsers: (params: UserListParams = {}) =>
    apiClient.get<PaginatedResponse<UserListItem>>('/admin/users', {
      params: { page: 1, page_size: 20, ...params },
    }),
  getUser: (userId: string) =>
    apiClient.get<UserListItem>(`/admin/users/${userId}`),
  getHITLQueue: () =>
    apiClient.get<HITLQueueItem[]>('/admin/hitl-queue'),
  resetPassword: (data: PasswordResetRequest) =>
    apiClient.post('/admin/password-reset', data),
  deactivateUser: (userId: string) =>
    apiClient.put(`/admin/users/${userId}/deactivate`),
  activateUser: (userId: string) =>
    apiClient.put(`/admin/users/${userId}/activate`),
};
```

---

## 8. Realtime Provider (P1)

The realtime layer is abstracted behind a provider. Internally it polls with tab-visibility and retry controls. When WebSocket support is added to the backend, only the provider internals change — no component code changes.

### src/providers/RealtimeProvider.tsx

```typescript
import React, { createContext, useCallback, useContext, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../store/authStore';
import { notificationsApi } from '../api/notifications';
import { queryKeys } from '../lib/queryKeys';
import type { NotificationItem } from '../types/notification';

interface RealtimeContextValue {
  isConnected: boolean;
}

const RealtimeContext = createContext<RealtimeContextValue>({ isConnected: true });
const NORMAL_POLL_MS = 60_000;
const MAX_RETRY_MS = 5 * 60_000;

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const timeoutRef = useRef<number | undefined>();
  const failureCountRef = useRef(0);

  const poll = useCallback(async () => {
    if (!user) return;
    if (document.visibilityState === 'hidden') return;

    try {
      const fn = user.role === 'doctor'
        ? notificationsApi.getDoctorNotifications
        : notificationsApi.getPatientNotifications;
      const res = await fn();
      failureCountRef.current = 0;
      queryClient.setQueryData(
        queryKeys.notifications.all(user.role),
        // Dedupe by notification_id, keep latest 50, sort newest-first
        (old: NotificationItem[] = []) => {
          const merged = new Map([
            ...old.map(n => [n.notification_id, n]),
            ...res.data.map(n => [n.notification_id, n]),
          ]);
          return [...merged.values()]
            .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
            .slice(0, 50);
        }
      );
    } catch {
      failureCountRef.current += 1;
      // Network error — handled by NetworkDisconnectedBanner.
    }
  }, [user, queryClient]);

  useEffect(() => {
    if (!user) return;

    const scheduleNextPoll = () => {
      window.clearTimeout(timeoutRef.current);
      const retryDelay = Math.min(
        NORMAL_POLL_MS * 2 ** failureCountRef.current,
        MAX_RETRY_MS
      );
      const delay = failureCountRef.current === 0 ? NORMAL_POLL_MS : retryDelay;
      timeoutRef.current = window.setTimeout(async () => {
        await poll();
        scheduleNextPoll();
      }, delay);
    };

    const resume = () => {
      if (document.visibilityState === 'visible') {
        poll();
        scheduleNextPoll();
      }
    };

    poll();
    scheduleNextPoll();
    document.addEventListener('visibilitychange', resume);
    window.addEventListener('focus', resume);
    return () => {
      window.clearTimeout(timeoutRef.current);
      document.removeEventListener('visibilitychange', resume);
      window.removeEventListener('focus', resume);
    };
  }, [user, poll]);

  // Future: replace polling with WebSocket subscription here.
  // Components subscribe via useRealtimeEvent() — no change needed.

  return (
    <RealtimeContext.Provider value={{ isConnected: true }}>
      {children}
    </RealtimeContext.Provider>
  );
}

export const useRealtime = () => useContext(RealtimeContext);
```

### src/hooks/useRealtimeEvent.ts

```typescript
// Placeholder for WebSocket event subscription.
// Currently a no-op — components call this for future compatibility.
// When WebSocket is implemented, subscribe here and call queryClient.invalidateQueries.

import { useEffect } from 'react';

type RealtimeEventType = 'report_processed' | 'field_updated' | 'assignment_changed';

export function useRealtimeEvent(
  _event: RealtimeEventType,
  _handler: (payload: unknown) => void
) {
  useEffect(() => {
    // WebSocket subscription goes here in Phase 2.
  }, []);
}
```

---

## 9. Stores

### src/store/authStore.ts

```typescript
import { create } from 'zustand';
import type { User } from '../types/auth';

interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  setAuth: (token, user) => set({ token, user, isAuthenticated: true }),
  logout: () => set({ token: null, user: null, isAuthenticated: false }),
}));
```

### src/store/uiStore.ts

```typescript
import { create } from 'zustand';

type ModalType =
  | 'field-verify'
  | 'patient-verify'
  | 'assignment'
  | 'duplicate-warning'
  | null;

interface UIState {
  sidebarOpen: boolean;
  activeModal: ModalType;
  modalPayload: Record<string, unknown> | null;
  isOffline: boolean;                       // P6
  setSidebarOpen: (open: boolean) => void;
  openModal: (modal: ModalType, payload?: Record<string, unknown>) => void;
  closeModal: () => void;
  setOffline: (offline: boolean) => void;   // P6
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  activeModal: null,
  modalPayload: null,
  isOffline: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  openModal: (modal, payload = null) =>
    set({ activeModal: modal, modalPayload: payload }),
  closeModal: () => set({ activeModal: null, modalPayload: null }),
  setOffline: (offline) => set({ isOffline: offline }),
}));
```

---

## 10. Form Validation Schemas (P10)

### src/validation/authSchemas.ts

```typescript
import { z } from 'zod';

export const loginSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export const signupSchema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  full_name: z.string().min(2, 'Full name required'),
  role: z.enum(['doctor', 'patient']),
  phone: z.string().optional(),
  license_number: z.string().optional(),
  date_of_birth: z.string().optional(),
  sex: z.enum(['M', 'F', 'Other']).optional(),
  claim_patient_uid: z.string().optional(),
}).refine(data => data.role !== 'doctor' || !!data.license_number, {
  message: 'License number is required for doctors',
  path: ['license_number'],
});
```

### src/validation/uploadSchemas.ts

```typescript
import { z } from 'zod';

const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'];
const MAX_SIZE_MB = 50;

export const uploadSchema = z.object({
  patient_uid: z.string().min(1, 'Patient UID is required'),
  file: z.instanceof(File)
    .refine(f => ALLOWED_TYPES.includes(f.type), 'Only PDF, JPEG, PNG, or TIFF allowed')
    .refine(f => f.size <= MAX_SIZE_MB * 1024 * 1024, `File must be under ${MAX_SIZE_MB}MB`),
});
```

### src/validation/verificationSchemas.ts

```typescript
import { z } from 'zod';

export const verifyFieldSchema = z.object({
  verification_type: z.enum(['approved', 'edited', 'rejected']),
  edited_value: z.string().optional(),
  edit_reason: z.string().optional(),
}).refine(
  data => data.verification_type !== 'edited' || !!data.edited_value,
  { message: 'Edited value is required when editing', path: ['edited_value'] }
);
```

---

## 11. Security Hardening (P11)

### src/lib/sanitize.ts

```typescript
// P11: Sanitize user-provided strings before rendering or displaying

/** Strip path traversal characters and suspicious patterns from filenames */
export function sanitizeFilename(name: string): string {
  return name
    .replace(/[/\\?%*:|"<>]/g, '_')  // unsafe filename chars
    .replace(/\.\./g, '_')             // path traversal
    .slice(0, 255);                    // max filename length
}

/** Escape content for display — never use dangerouslySetInnerHTML */
export function escapeForDisplay(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
```

### Mandatory Security Rules

These rules are enforced at code review. Any violation is a blocker.

1. **No `dangerouslySetInnerHTML` anywhere.** Period. Use text nodes only.
2. **All filenames displayed to the user pass through `sanitizeFilename()`** before render.
3. **No sensitive data in `console.log`.** No tokens, patient IDs, or PHI in console output. Use `console.warn` for non-PHI operational warnings only.
4. **Do not attempt to block browser developer tools.** This is not a security boundary and can break debugging/tooling.
5. **Frontend security relies on real controls:** backend authentication, backend authorization, least-privilege API responses, data minimization, CSP, secure token handling, sanitization, and no PHI logging.
6. **Never expose stack traces to users.** Generic messages only. Stack traces go to the browser console (non-PHI) or a future error reporting service.
7. **File MIME type is never trusted from the frontend.** The API validates MIME on the server. The upload Zod schema validates client-side for UX only — not for security.
8. **Axios instance never logs request/response bodies** in production.

---

## 12. Routing (Role-Based)

```typescript
// src/App.tsx

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <NetworkDisconnectedBanner />   {/* P6: always mounted */}
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          <Route element={<RoleGuard role="doctor" />}>
            <Route element={<AppShell />}>
              <Route path="/doctor" element={<DoctorDashboard />} />
              <Route path="/doctor/patients" element={<PatientListPage />} />
              <Route path="/doctor/patients/:patientId" element={<PatientDetailPage />} />
              <Route path="/doctor/reports/:reportId" element={<ReportDetailPage />} />
              <Route path="/doctor/upload" element={<UploadPage />} />
              <Route path="/doctor/hitl" element={<HITLQueuePage />} />
              <Route path="/doctor/analytics/:patientId" element={<AnalyticsPage />} />
              <Route path="/doctor/chat" element={<ChatPage />} />
            </Route>
          </Route>

          <Route element={<RoleGuard role="patient" />}>
            <Route element={<AppShell />}>
              <Route path="/patient" element={<PatientDashboard />} />
              <Route path="/patient/reports" element={<MyReportsPage />} />
              <Route path="/patient/reports/:reportId" element={<ReportViewPage />} />
              <Route path="/patient/trends" element={<TrendsPage />} />
              <Route path="/patient/chat" element={<PatientChatPage />} />
            </Route>
          </Route>

          <Route element={<RoleGuard role="admin" />}>
            <Route element={<AppShell />}>
              <Route path="/admin" element={<AdminDashboard />} />
              <Route path="/admin/users" element={<UsersPage />} />
              <Route path="/admin/hitl" element={<HITLOverviewPage />} />
            </Route>
          </Route>

          <Route path="/" element={<RootRedirect />} />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

function RoleGuard({ role }: { role: string }) {
  const { user, isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" />;
  if (user?.role !== role) return <Navigate to={`/${user?.role}`} />;
  return <Outlet />;
}

function RootRedirect() {
  const { user, isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" />;
  return <Navigate to={`/${user!.role}`} />;
}
```

---

## 13. Offline / Error Recovery Components (P6)

### NetworkDisconnectedBanner

```typescript
// Mounted at App root — always present, only visible when offline.
// Listens to window 'online'/'offline' events.
// Shows: grey banner at top of viewport: "No internet connection — some features may be unavailable"
// Auto-dismisses when online event fires.
// Updates uiStore.isOffline state.
```

### RetryPanel

```typescript
// Props: onRetry: () => void, message?: string
// Usage: replace failed data sections (not full page)
// Shows: icon + "Failed to load" + "Try Again" button
// Example usage: wrap table content when useQuery returns isError
```

### AutoReconnectIndicator

```typescript
// Shown inside RetryPanel or alongside NetworkDisconnectedBanner
// Displays countdown: "Retrying in 30s..."
// Counts down, fires retry automatically, resets on success
```

### Production Offline Roadmap (R7)

MVP offline support is intentionally limited to clear network status, failed-section retry, and reconnect feedback. Do not build queued mutations for MVP.

Future production offline support should add:

- queued mutations with idempotency keys for safe retry
- retry queue UI for failed writes
- local draft persistence for chat text, verification notes, and upload metadata
- conflict handling when server state changes while the user was offline
- explicit PHI-safe storage review before persisting anything locally

---

## 14. FileViewer Full Specification (P7)

### src/components/report/FileViewer.tsx

```typescript
// Props:
//   reportId: string
//   role: 'doctor' | 'patient'
//   mimeType: string

// PDF rendering (react-pdf):
//   - Show Skeleton full-height while loading
//   - Page navigation: "< Page 2 of 5 >" controls below viewer
//   - Zoom: 50% / 75% / 100% / 125% / 150% — dropdown
//   - Default zoom: 100%
//   - Page renders inside overflow-auto container
//   - Error: RetryPanel if PDF fails to load
//   - ARIA: aria-label="Document viewer, page N of M"

// Image rendering (JPEG, PNG, TIFF):
//   - Display in <img> tag with object-contain
//   - Pan: click-drag with cursor: grab / grabbing
//   - Zoom in/out: buttons + mouse wheel
//   - Rotate: 90° clockwise / anti-clockwise buttons
//   - Reset button returns to default zoom + rotation
//   - ARIA: aria-label="Uploaded image document"

// Loading state: always show Skeleton while blob URL is being fetched
// Error state: RetryPanel with onRetry={() => refetch()}
// Request cancellation: pass React Query signal to reportsApi raw-file call
// Blob URL cleanup: revoke on component unmount
//   useEffect(() => () => URL.revokeObjectURL(blobUrl), [blobUrl]);
```

---

## 15. Notification Cache Strategy (P9)

The notification system must follow these rules consistently:

```
Rule                     Specification
─────────────────────────────────────────────────────────────────
Ordering                 Latest-first (sort by created_at DESC)
Max in cache             50 notifications per role
Deduplication            By notification_id — never show duplicate
Unread count             Computed client-side: notifications.filter(n => !n.is_read).length
Unread badge             Red circle on NotificationBell — max "99+" display
Mark-as-read             Optimistic (P3) — instant visual, rollback on failure
Poll frequency           60s after success (via RealtimeProvider — P1)
Hidden tab behavior      Pause polling while document.visibilityState === 'hidden'
Resume behavior          Poll immediately on tab visible/focus, then resume 60s cadence
Failure retry            Exponential retry after repeated failures, capped at 5 minutes
Panel scroll             Virtualized if count > 20; else simple overflow-y-auto
Notification navigation  report_id present → navigate to /{role}/reports/{report_id}
                         no report_id → show in panel only, no navigation
Panel max-height         400px with scroll
```

---

## 15A. Monitoring & Observability (Production Roadmap) (R2)

MVP does not require an observability vendor or SDK. Production should add a PHI-safe frontend monitoring layer before clinical rollout.

```
Concern                  Production direction
─────────────────────────────────────────────────────────────────
Error tracking           Sentry or equivalent with PHI scrubbing enabled
Performance telemetry    Web Vitals + route transition timing
API latency              Axios interceptors emit endpoint, method, status, duration
Tracing                  OpenTelemetry-compatible spans/events where feasible
Session diagnostics      Non-PHI breadcrumbs: route, role, feature area, error code
Logging pipeline         Browser logs shipped only after PHI redaction review
```

Observability events must never include tokens, patient IDs, names, report text, raw field values, filenames, chat messages, request bodies, or response bodies. Use opaque correlation IDs from the backend when available.

---

## 16. Accessibility Standards (P8)

These are mandatory minimums for a healthcare application.

### Keyboard Navigation

All interactive elements must be keyboard-accessible:

```
Element                  Requirement
─────────────────────────────────────────────────────────────────
Buttons                  Focusable, Enter/Space activate
Modal                    Focus trap (Tab cycles within modal), Escape closes
Dropdown/Select          Arrow keys navigate options
Table rows with action   Tab to row action buttons
Sidebar links            Tab through all links
Notification panel       Escape closes panel, Tab cycles notifications
```

### ARIA Requirements

```typescript
// Modal
<div role="dialog" aria-modal="true" aria-labelledby="modal-title">

// Status badges
<span role="status" aria-label="Report status: Auto approved">

// Loading states
<div role="status" aria-live="polite" aria-label="Loading...">

// Error messages
<div role="alert" aria-live="assertive">

// Table with sortable columns
<th scope="col" aria-sort="ascending">

// Notification bell
<button aria-label={`Notifications, ${unreadCount} unread`}>

// FileViewer
<main aria-label="Document viewer">
```

### Focus Management

```
Action                   Required Behavior
─────────────────────────────────────────────────────────────────
Modal opens              Focus moves to modal title or first input
Modal closes             Focus returns to trigger element
Toast appears            aria-live="polite" announces message
Error appears            aria-live="assertive" announces error
Navigation               Focus moves to page heading (h1) on route change
```

### Color Contrast

All text must meet WCAG AA: 4.5:1 for normal text, 3:1 for large text. Do not convey information by color alone — always pair color with icon or text label (e.g., abnormal fields show red color AND a warning icon).

---

## 17. Page-by-Page Specifications

### Auth Pages

```
LoginPage (/login)
  Fields: email, password — validated by loginSchema (P10)
  On submit: authApi.login() → setAuth() → navigate to /{role}
  Error 401: "Invalid email or password"
  Error 429: "Too many attempts. Please wait 15 minutes."
  Link: "Create account" → /signup

SignupPage (/signup)
  Fields: full_name, email, password, role (Doctor/Patient)
  Schema: signupSchema (P10)
  Conditional: license_number if role=Doctor
  Conditional: date_of_birth + sex if role=Patient
  Optional: claim_patient_uid — helper: "Enter your Patient UID if your doctor has already pre-registered you."
  On submit: authApi.signup() → setAuth() → navigate to /{role}
```

### Doctor Pages

```
DoctorDashboard (/doctor)
  4 stat cards — Skeleton while loading (P12)
  Recent Reports table — Skeleton rows while loading (P12)
  Notifications panel (last 5 unread from realtime cache)

PatientListPage (/doctor/patients)
  Search bar, paginated table — Skeleton rows (P12)
  Patient search cancels stale requests with AbortController / Axios signal (R5)
  Table: Name | Patient UID | Reports | Last Upload | Assignment Status
  Add Patient → assignment modal → assignmentsApi.createAssignment()
    Approve/reject uses optimistic update (P3)

PatientDetailPage (/doctor/patients/:patientId)
  Header: name, uid, age, sex
  Tab "Reports": list with status badges — Skeleton cards (P12)
  Tab "Analytics": AbnormalityPanel + TrendLineChart
    Data from intelligenceApi.getAnalytics(patientId) → AnalyticsResult (G12)
    AbnormalityPanel receives abnormal_fields + normal_fields (ClinicalField[])

ReportDetailPage (/doctor/reports/:reportId)
  Split: left 60% FieldsTable, right 40% FileViewer (P7)
  FieldsTable: Skeleton rows while loading (P12)
  FileViewer: Skeleton while file loads (P12, P7)
  Above table: ReportStatusBadge + lifecycle timeline
  is_duplicate=true: amber banner "Flagged as probable duplicate"
  Verify field: optimistic update (P3) — instant visual feedback
  FieldsTable: is_final=true → violet lock icon, no action (G3)
  Re-upload: hidden if any field has is_final=true (G3)
  Route/report change cancels in-flight raw-file request (R5)

HITLQueuePage (/doctor/hitl)
  Toggle: "All Patients" | "My Patients Only"
  Table — Skeleton rows (P12)
  Empty state: EmptyState component

AnalyticsPage (/doctor/analytics/:patientId)
  Field selector dropdown
  TrendLineChart — Skeleton while loading (P12)
  Field/patient switches cancel stale analytics/trend requests (R5)
  AI insight card: from TrendResult.insight
  AbnormalityPanel: ClinicalField[] from AnalyticsResult.ai_insight (G12)
  ARIA: chart labeled with aria-label including field name

ChatPage (/doctor/chat)
  Patient selector
  ChatWindow — G10 typed rendering
  Typing indicator: three animated dots during loading
  Messages in local state only (not persisted, not cached)
  In-flight doctorQuery cancels on route leave or a new send (R5)
  Production healthcare upgrade: persist sessions only after retention, audit, and PHI policy review (R6)

UploadPage (/doctor/upload)
  Step 1 — Patient UID confirmed before file area enables (SECURITY CRITICAL)
  Step 2 — UploadDropzone (enabled after patient confirmed)
  Schema: uploadSchemas.ts (P10)
  On 409: DuplicateWarningModal type='exact' (G8)
  On 200 + duplicate_warning: DuplicateWarningModal type='probable' (G8)
  On 429: toast "Upload rate limit reached — try again later" (specific message)
  On success: navigate to /doctor/reports/{report_id}
```

### Patient Pages

```
PatientDashboard (/patient)
  Welcome banner with name
  3 stat cards — Skeleton while loading (P12)
  Last 5 released reports

MyReportsPage (/patient/reports)
  Filters: date range + inferred_document_type (G9)
  'unknown' → label "Processing"; 'cbc' → 'Complete Blood Count' etc.
  Paginated report cards — Skeleton cards (P12)
  Upload: DuplicateWarningModal if needed (G8)

ReportViewPage (/patient/reports/:reportId)
  Fields as cards (not table) — Skeleton cards (P12)
  FileViewer — Skeleton while loading (P12, P7)
  Route/report change cancels in-flight raw-file request (R5)
  is_final=true → "Verified by doctor ✓" violet badge (G3)
  PatientVerifyModal → optimistic update (P3)

TrendsPage (/patient/trends)
  Field selector (fields with ≥2 data points)
  TrendLineChart — Skeleton while loading (P12)
  Field switches cancel stale trend requests (R5)
  Plain English insight from TrendResult.insight

PatientChatPage (/patient/chat)
  Sticky disclaimer banner (position: sticky, top: 0, NO dismiss)
  ChatWindow — G11: reads patientResult.disclaimer as field (not text detection)
  Disclaimer shown as footer on EVERY assistant bubble
  safety_blocked: amber banner before bubble
  Send → intelligenceApi.patientChat({ text, patient_id: user.user_id })
  In-flight patientChat cancels on route leave or a new send (R5)
  Production healthcare upgrade: persist sessions only after retention, audit, and PHI policy review (R6)
```

### Admin Pages

```
AdminDashboard (/admin)
  6 stat cards — Skeleton (P12): Total Doctors | Total Patients | Total Reports |
                                  Processing | HITL Pending | Fully Verified
  Recent signups table — Skeleton rows (P12)

UsersPage (/admin/users)
  Role tabs: All | Doctors | Patients
  Paginated table — Skeleton rows (P12)
  Actions: Deactivate/Activate (optimistic — P3) | Reset Password
  Reset Password modal → adminApi.resetPassword()

HITLOverviewPage (/admin/hitl)
  Table: Patient | Patient UID | Doctor | Report Date | Fields Pending | Days Waiting
  Sorted: days_waiting DESC
  Skeleton rows while loading (P12)
  Read-only — links to /doctor/reports/:reportId
```

---

## 18. Key Components Implementation

### FieldsTable

```typescript
// Props: fields: ReportField[], reportId: string, role: 'doctor' | 'patient'
// Status badge mapping:
//   auto + !doctor_verified + !patient_verified → "Auto-approved" (clinical-auto green)
//   hitl + !doctor_verified                     → "Needs Verification" (clinical-hitl amber)
//   patient_verified + !doctor_verified         → "Patient Verified" (clinical-verified blue)
//   is_final=true (G3)                          → "Doctor Verified ✓" (clinical-final violet)
// Loading: Skeleton rows (P12)
// Accessibility: th scope="col", aria-sort on sortable cols (P8)
```

### DuplicateWarningModal (G8)

```typescript
// Props:
//   type: 'exact' | 'probable'
//   existingReportId: string, existingUploadedAt: string
//   uploadedByRole: 'doctor' | 'patient'
//   onUseExisting: () => void
//   onForceUpload: () => void
//   onDismiss: () => void  // only for 'probable'
// type='exact': red border, no dismiss X, role="dialog" aria-modal="true"
// type='probable': amber border, dismiss X, role="dialog" aria-modal="true"
```

### TrendLineChart

```typescript
// Props: data: TrendPoint[], meta: ChartMeta, insight: string
// CRITICAL: Only render ReferenceArea if meta.ref_low !== null && meta.ref_high !== null
// Accessibility: aria-label="Trend chart for {field} — {trend_direction}"
// Loading: Skeleton h-48 (P12)
```

### AbnormalityPanel (G12)

```typescript
// Props: abnormalFields: ClinicalField[], normalFields: ClinicalField[]
// (NOT ReportField[] — ClinicalField from AnalyticsResult)
// Abnormal chips: red border + critical-bg + warning icon (color NOT sole indicator — P8)
// Normal chips: green border + auto-bg + check icon
```

### ChatWindow (G10 + G11)

```typescript
// Doctor rendering — G10 type guard pattern
// Patient rendering — G11 reads patientResult.disclaimer directly
// Loading: animated three-dot indicator
// Auto-scroll on new message
// Accessibility: role="log", aria-live="polite", aria-label="Chat conversation"
```

### Skeleton Component (P12)

```typescript
// src/components/ui/Skeleton.tsx
// Props: className?: string; lines?: number; variant?: 'text' | 'card' | 'table-row'

// Usage:
// <Skeleton variant="table-row" lines={8} />
// <Skeleton variant="card" />
// <Skeleton className="h-48 w-full" />  // custom shape
```

---

## 19. Auth Architecture — MVP vs Production (P13)

### Current State (MVP — Implemented)

```
Storage:    JWT in Zustand memory only (zero XSS risk)
Refresh:    None — user re-logs on refresh/tab close
Security:   Excellent for MVP; no persistent attack surface
Limitation: Poor UX for long sessions; doctors lose work on tab refresh
```

### Production Upgrade Path (Future — Not Implemented Now)

When the backend adds refresh token support, implement in this order:

```
Step 1 — Backend:
  POST /auth/refresh endpoint (already in auth.ts API)
  Returns short-lived access_token in response body
  Sets httpOnly Secure SameSite=Strict cookie with refresh token

Step 2 — Frontend (client.ts only):
  Add 401 interceptor logic to attempt silent refresh BEFORE logout:
    const refreshed = await authApi.refresh();
    store new access_token in Zustand
    retry original request with new token
    if refresh fails → logout()

Step 3 — Auth store:
  Add refreshing: boolean state to prevent concurrent refreshes
  Use a mutex/flag to avoid refresh storm on concurrent 401s

Step 4 — Session timeout:
  Add configurable inactivity timeout (e.g., 30 min)
  Warn user 5 min before: "Your session will expire in 5 minutes"
```

**Do NOT implement the production path now.** The backend refresh endpoint is not yet built. Mark the `client.ts` interceptor with the `// P13` comment as a placeholder.

---

## 20. Upload Resumable Roadmap (P2)

### Current State (MVP — Implemented)

Single multipart upload via `Content-Type: multipart/form-data`. Files up to 50MB. On network failure, user must re-select and retry from scratch.

### Future: Chunked / Resumable Uploads

When reliability for large files becomes a priority:

```
Protocol:     tus (https://tus.io) or AWS S3 Multipart Upload
Library:      tus-js-client
UploadDropzone changes:
  - Add onProgress: (percent: number) => void prop
  - Progress bar replaces spinner
  - "Pause" / "Resume" buttons
  - Chunk size: 5MB per chunk
  - Retry: automatic with exponential backoff on chunk failure
Backend:      Requires new chunked upload endpoint — coordinate with Pipeline A team
```

**Current UploadDropzone must already expose `onProgress` prop** (even if currently unused) so the API surface doesn't change when chunked upload is implemented.

```typescript
// UploadDropzone props — include now:
interface UploadDropzoneProps {
  onUploadSuccess: (report: Report) => void;
  onDuplicateExact: (error: ExactDuplicateError) => void;
  onDuplicateProbable: (warning: DuplicateWarning) => void;
  onProgress?: (percent: number) => void;  // P2: future chunked upload
  patientId?: string;
  disabled?: boolean;
}
```

---

## 21. Implementation Prompts

### PROMPT 1 — Project Setup

```
TASK: Initialize the React frontend project ONLY

From inside hdmis/frontend/:

1. npm create vite@latest . -- --template react-ts

2. npm install react-router-dom @tanstack/react-query zustand axios
   npm install react-hook-form @hookform/resolvers zod
   npm install recharts lucide-react react-pdf
   npm install -D tailwindcss postcss autoprefixer @types/node
   npx tailwindcss init -p

3. Configure tailwind.config.ts with clinical palette from Section 2.
   Include "final"/"final-bg" (G3) and "offline"/"offline-bg" (P6).

4. tsconfig.json: strict: true

5. Create full folder structure including:
   src/lib/apiError.ts (P4)
   src/lib/queryKeys.ts (P5)
   src/lib/sanitize.ts (P11)
   src/types/common.ts (R3 — PaginationParams + PaginatedResponse)
   src/validation/ (P10)
   src/providers/RealtimeProvider.tsx (P1)
   src/hooks/useRealtimeEvent.ts (P1)
   src/components/feedback/ (P6)
   src/components/ui/Skeleton.tsx (P12)

6. Create placeholder empty-export files for everything listed.

7. .env: VITE_API_URL=http://localhost:8000

8. `src/main.tsx` mounts the app/providers only; do not add security-through-obscurity browser-tool blocking.

npm run dev → http://localhost:5173 with no errors.
```

### PROMPT 2 — Lib + Types + API Client + Stores

```
TASK: Implement lib, types, API client, and stores ONLY

src/lib/apiError.ts              (P4 — normalizeApiError, ApiError type)
src/lib/queryKeys.ts             (P5 — query key factories + staleTime constants)
src/lib/sanitize.ts              (P11 — sanitizeFilename, escapeForDisplay)

src/types/common.ts              (R3 — PaginationParams + PaginatedResponse)
src/types/ — all remaining files as Section 3
src/validation/ — all files as Section 10

src/api/client.ts                (P13 comment placeholder in interceptor)
src/api/auth.ts
src/api/reports.ts
src/api/verification.ts
src/api/assignments.ts           (G4)
src/api/intelligence.ts          (G10, G11, G13)
src/api/notifications.ts         (G14)
src/api/admin.ts                 (G6)

src/store/authStore.ts
src/store/uiStore.ts             (G7; isOffline + setOffline — P6)

CRITICAL: npx tsc --noEmit must pass zero errors.
```

### PROMPT 3 — Design System Components

```
TASK: Implement UI primitives ONLY

src/components/ui/Button.tsx     variants: primary, secondary, danger, ghost
                                 disabled + loading spinner state
src/components/ui/Badge.tsx      variants: auto, hitl, verified, final (G3), processing
src/components/ui/Card.tsx
src/components/ui/Table.tsx
src/components/ui/Modal.tsx      focus trap + Escape closes + aria-modal (P8)
src/components/ui/Toast.tsx      aria-live="polite" (P8)
src/components/ui/Spinner.tsx
src/components/ui/Skeleton.tsx   (P12 — variant prop: text/card/table-row)
src/components/ui/EmptyState.tsx
src/components/ui/Pagination.tsx

src/components/feedback/NetworkDisconnectedBanner.tsx   (P6)
src/components/feedback/RetryPanel.tsx                  (P6)
src/components/feedback/AutoReconnectIndicator.tsx      (P6)

All accept className prop. No business logic.
All interactive elements keyboard-accessible (P8).
```

### PROMPT 4 — Realtime Provider + Layout + Routing

```
TASK: Realtime, layout shell, and routing ONLY

src/providers/RealtimeProvider.tsx    (P1 — polling abstraction)
src/hooks/useRealtimeEvent.ts         (P1 — placeholder)
src/components/layout/AppShell.tsx    (wraps with RealtimeProvider)
src/components/layout/Sidebar.tsx
src/components/layout/Topbar.tsx
src/components/notifications/NotificationBell.tsx   (aria-label unread count — P8)
src/components/notifications/NotificationPanel.tsx  (P9 strategy; optimistic read — P3)
src/App.tsx                           (NetworkDisconnectedBanner mounted at root)
src/main.tsx

Notification panel: latest-first, max 50, dedupe by notification_id (P9)
RealtimeProvider: pause polling when tab hidden, resume on focus, exponential retry on failure (R4)
Mark-as-read: optimistic mutation (P3)
Sidebar links per role — all keyboard-navigable (P8)
```

### PROMPT 5 — Auth Pages

```
TASK: Auth pages ONLY

src/pages/auth/LoginPage.tsx     loginSchema validation (P10)
src/pages/auth/SignupPage.tsx    signupSchema validation (P10)
src/hooks/useAuth.ts

Errors: use normalizeApiError (P4) — not raw Axios
429 → "Too many attempts. Please wait 15 minutes." (specific message)
```

### PROMPT 6 — Report Components

```
TASK: Report components ONLY

src/components/report/ReportCard.tsx
src/components/report/ReportStatusBadge.tsx
src/components/report/FieldsTable.tsx           (is_final G3; Skeleton P12; aria P8)
src/components/report/FieldRow.tsx
src/components/report/FileViewer.tsx            (full P7 spec: PDF nav/zoom; image pan/zoom/rotate)
src/components/report/UploadDropzone.tsx        (onProgress prop P2; expose duplicate state — G8)
src/components/report/DuplicateWarningModal.tsx (G8; aria-modal P8)

FileViewer: Skeleton while loading, RetryPanel on error (P6)
UploadDropzone: all errors via normalizeApiError (P4)
uploadSchema validation (P10)
```

### PROMPT 7 — Chart Components

```
TASK: Chart components ONLY

src/components/charts/TrendLineChart.tsx
  null-guard ref_low/ref_high before ReferenceArea (existing)
  Skeleton while loading (P12)
  aria-label with field name and trend direction (P8)
src/components/charts/FieldBarChart.tsx
src/components/charts/AbnormalityPanel.tsx
  Props: abnormalFields: ClinicalField[], normalFields: ClinicalField[] (G12)
  Abnormal: red border + warning icon (P8 — not color alone)
  Normal: green border + check icon
```

### PROMPT 8 — Doctor Pages + Hooks

```
TASK: Doctor pages + hooks ONLY

All pages use:
  - Skeleton while loading (P12)
  - RetryPanel on error (P6)
  - normalizeApiError (P4)
  - queryKeys + staleTime (P5)

src/pages/doctor/DoctorDashboard.tsx
src/pages/doctor/PatientListPage.tsx       (assignment approve: optimistic P3)
src/pages/doctor/PatientDetailPage.tsx     (AnalyticsResult G12)
src/pages/doctor/ReportDetailPage.tsx      (is_final G3; verify: optimistic P3; FileViewer P7)
src/pages/doctor/UploadPage.tsx            (DuplicateWarningModal G8; uploadSchema P10; 429 specific toast)
src/pages/doctor/HITLQueuePage.tsx
src/pages/doctor/AnalyticsPage.tsx         (ai_insight G12)
src/pages/doctor/ChatPage.tsx              (DoctorQueryResponse G10; type guards)
src/hooks/useReports.ts
src/hooks/useVerification.ts
src/hooks/useAssignments.ts
src/hooks/useIntelligence.ts

Cancellation (R5): pass React Query signal / AbortController to patient search,
analytics/trend queries, file blob requests, and chat sends.
ChatPage: after doctorQuery resolves, use isReasoningResult/isTrendResult/isRetrievalResult
ChatWindow: keyboard-navigable send (Enter key) (P8)
Chat remains local state for MVP; do not add persistence until retention/audit policy exists (R6).
```

### PROMPT 9 — Patient Pages

```
TASK: Patient pages ONLY

src/pages/patient/PatientDashboard.tsx
src/pages/patient/MyReportsPage.tsx          (inferred_document_type filter G9; Skeleton P12)
src/pages/patient/ReportViewPage.tsx         (is_final G3; verify: optimistic P3; FileViewer P7)
src/pages/patient/TrendsPage.tsx             (Skeleton P12)
src/pages/patient/PatientChatPage.tsx        (PatientChatResult G11; sticky disclaimer safety)

Cancellation (R5): pass React Query signal / AbortController to trends,
file blob requests, and chat sends.
PatientChatPage G11 critical:
  Store PatientChatResult in message.patientResult
  Set message.content = result.response
  ChatWindow reads message.patientResult.disclaimer as field
  safety_blocked → amber banner
  Disclaimer banner: position sticky, top-0, NO dismiss button (safety requirement)
  Every assistant bubble: patientResult.disclaimer as grey small footer
Chat remains local state for MVP; do not add persistence until retention/audit policy exists (R6).
```

### PROMPT 10 — Admin Pages + Notifications Hook

```
TASK: Admin pages + notification hook ONLY

src/pages/admin/AdminDashboard.tsx         (AdminStats G2; Skeleton P12)
src/pages/admin/UsersPage.tsx              (UserListItem G2; deactivate: optimistic P3; Skeleton P12)
src/pages/admin/HITLOverviewPage.tsx       (HITLQueueItem G2; patient_uid column; Skeleton P12)
src/hooks/useNotifications.ts

useNotifications: reads from RealtimeProvider cache (do NOT poll independently)
NotificationBell: aria-label with unread count (P8, P9)
Clicking notification: navigate to /{role}/reports/{report_id} if present (P9)
UsersPage uses Pagination component with PaginationParams / PaginatedResponse<UserListItem> (R3)
```

### PROMPT 11 — Integration + Polish

```
TASK: Wire together and polish ONLY

Cache invalidation:
  upload → reports list
  verify field → report fields + report status (optimistic already applied)
  assignment approve → patient list (optimistic already applied)
  re-upload → all data for that report_id
  admin password reset → users list

Error normalization audit:
  Every catch block uses normalizeApiError (P4)
  Specific 429 messages on upload + login
  No raw Axios errors anywhere

Pagination audit:
  Paged endpoints use PaginationParams + PaginatedResponse<T> (R3)
  page is 1-based, page_size defaults to 20, frontend max is 100 (R3)
  Pagination component drives paged tables/lists, not ad hoc params (R3)

Cancellation audit:
  Patient search aborts stale requests (R5)
  Analytics/trend switching aborts stale requests (R5)
  Chat sends abort on route leave or new send (R5)
  FileViewer raw-file loads abort on report change or unmount (R5)

Accessibility audit:
  All modals have focus trap + Escape close + aria-modal (P8)
  All loading states have role="status" (P8)
  All error alerts have role="alert" aria-live="assertive" (P8)
  Chart aria-labels include field name (P8)
  Color never used as sole indicator (P8)

Security audit:
  No dangerouslySetInnerHTML anywhere (P11)
  All displayed filenames through sanitizeFilename() (P11)
  No browser developer-tool blocking code (P11)
  No PHI in console.log (P11)

Observability roadmap audit:
  Monitoring & Observability section is documented (R2)
  No MVP observability dependency is required (R2)
  Future telemetry explicitly forbids PHI, tokens, request bodies, and response bodies (R2)

Skeleton coverage audit:
  All tables: Skeleton rows while loading (P12)
  All stat cards: Skeleton while loading (P12)
  FileViewer: Skeleton while blob fetching (P12)
  Analytics chart: Skeleton while loading (P12)

End-to-end smoke test paths:
  Doctor:  login → upload (duplicate flow) → fields → verify (optimistic) → release → analytics → chat
  Patient: login → view report → verify (optimistic) → trends → chat (disclaimer visible + sticky)
  Admin:   login → stats → deactivate user (optimistic) → reset password
  Offline: disconnect network → NetworkDisconnectedBanner appears → reconnect → banner dismisses

npm run build — zero TS errors, zero warnings.
```

---

## 22. Critical Implementation Notes

**`is_final` everywhere — `is_locked` does not exist (G3).** Field locking is expressed by `is_final: boolean` on `ReportField`. Tailwind token is `clinical-final` (violet).

**Doctor query responses are typed — never `any` (G10).** Use `isReasoningResult`, `isTrendResult`, `isRetrievalResult` type guards after API call.

**`PatientChatResult.disclaimer` is a field, not text content (G11).** Read `result.patientResult.disclaimer` directly — never detect "disclaimer" as a keyword in response text.

**`AnalyticsResult.ai_insight` — not `insight` (G12).** Wrong field name produces `undefined` silently. The type definition enforces this.

**`AbnormalityPanel` receives `ClinicalField[]`, not `ReportField[]` (G12).** These are different types from different pipeline stages.

**`NotificationItem` lives in `src/types/notification.ts` (G14).** All backend-mirroring types are in `src/types/`.

**Duplicate upload 409 uses `normalizeApiError` (G8, P4).** The `normalizeApiError` function recognizes `duplicate_type: 'exact'` and returns `code: 'DUPLICATE_EXACT'`. Components check the code and open `DuplicateWarningModal`.

**Optimistic mutations must rollback cleanly (P3).** Every `onMutate` saves previous cache state in context. Every `onError` restores it. Every `onSettled` invalidates to confirm with server truth.

**Skeleton is not Spinner (P12).** Spinner = action in progress (button submit). Skeleton = content loading. Never show an empty table — always show skeleton rows.

**Realtime is abstracted (P1).** Components never call `setInterval` for polling. All realtime concerns live in `RealtimeProvider`. `useRealtimeEvent` is the future subscription hook.

**Notification polling is visibility-aware (R4).** `RealtimeProvider` pauses polling while the tab is hidden, resumes on focus/visibility change, and uses exponential retry after repeated failures.

**Pagination is standardized (R3).** Paged APIs use `PaginationParams` and `PaginatedResponse<T>` only. `page` is 1-based, `page_size` defaults to 20, and the frontend must not request more than 100.

**Rapid-changing requests are cancellable (R5).** Patient search, chat sends, analytics/trend switching, and FileViewer blob loads must pass an Axios `signal` and ignore cancellation as a neutral outcome.

**Patient disclaimer is non-negotiable safety.** `PatientChatPage` must have the banner at `position: sticky; top: 0` with no dismiss. Every assistant message bubble must render `patientResult.disclaimer` as footer text.

**Chat persistence is a production healthcare decision (R6).** MVP chat messages remain in local component state only. Do not add persistence until retention, audit trail, export, and PHI policy requirements are defined.

---

## 23. Agent Checklist — Before Marking Any Step Complete

### Foundation
- [ ] `npx tsc --noEmit` passes zero errors after every prompt
- [ ] `npm run build` zero warnings, zero unused imports
- [ ] No `any` types anywhere
- [ ] No direct `fetch` — all calls through `src/api/`
- [ ] Auth token in Zustand only — not localStorage
- [ ] Monitoring & Observability documented as production roadmap, not MVP dependency (R2)
- [ ] Future observability forbids PHI, tokens, request bodies, and response bodies (R2)

### Auth + Routing
- [ ] RoleGuard blocks wrong-role URL access
- [ ] Root `/` redirects to `/{role}` when authenticated
- [ ] 429 on login shows specific rate limit message (P4)

### Type Correctness
- [ ] `PaginationParams` + `PaginatedResponse<T>` live in `src/types/common.ts` (R3)
- [ ] `is_locked` does not appear anywhere — only `is_final` (G3)
- [ ] `Report` has `upload_document_type` + `inferred_document_type` (G9)
- [ ] `Assignment`, `DoctorProfile`, `PatientProfile` typed (G1)
- [ ] `AdminStats`, `HITLQueueItem`, `UserListItem` typed (G2)
- [ ] `ReasoningResult` has `citations: string[]` field (G15)
- [ ] `DoctorQueryResponse` is a union type with three type guards (G10)
- [ ] `PatientChatResult` has `simplified_fields` + `disclaimer` fields (G11)
- [ ] `AnalyticsResult` has `ai_insight` (not `insight`) field (G12)
- [ ] `ClinicalField` typed for use with `AbnormalityPanel` (G12)
- [ ] `NotificationItem` in `src/types/notification.ts` (G14)

### API Modules
- [ ] Paged API methods use `PaginationParams` + `PaginatedResponse<T>` (R3)
- [ ] `page` is 1-based and `page_size` defaults to 20, max 100 (R3)
- [ ] `api/assignments.ts` all endpoints implemented (G4)
- [ ] `api/notifications.ts` imports `NotificationItem` from types/ (G5, G14)
- [ ] `api/admin.ts` all endpoints implemented (G6)
- [ ] `api/intelligence.ts` — `doctorQuery` returns `DoctorQueryResponse` (G10)
- [ ] `api/intelligence.ts` — `patientChat` returns `PatientChatResult` (G11)
- [ ] `api/intelligence.ts` — `getAnalytics` returns `AnalyticsResult` (G13)
- [ ] `api/reports.ts` — upload/reupload accept `force` param (G8)

### New Lib + Validation (P4, P5, P10, P11)
- [ ] `src/lib/apiError.ts` implemented — `normalizeApiError` handles 409/429/401/422/5xx
- [ ] Every `catch` block in every hook calls `normalizeApiError` — no raw Axios reads
- [ ] `src/lib/queryKeys.ts` implemented — all queries use key factories
- [ ] `staleTime` constants applied in all `useQuery` calls
- [ ] `src/validation/authSchemas.ts` — `loginSchema` + `signupSchema` used in auth pages
- [ ] `src/validation/uploadSchemas.ts` — `uploadSchema` used in UploadDropzone
- [ ] `src/validation/verificationSchemas.ts` — `verifyFieldSchema` used in verify modals
- [ ] `src/lib/sanitize.ts` — `sanitizeFilename` applied to all displayed filenames
- [ ] No `dangerouslySetInnerHTML` anywhere (P11)
- [ ] No browser developer-tool blocking code (P11)
- [ ] No PHI in `console.log` (P11)

### Request Cancellation (R5)
- [ ] Patient search aborts previous request when the query changes
- [ ] Analytics/trend switching aborts stale requests
- [ ] FileViewer raw-file requests abort on report change or unmount
- [ ] Doctor and patient chat requests abort on route leave or new send
- [ ] Canceled requests do not show error toasts or overwrite newer state

### Stores
- [ ] `uiStore.ts` has `isOffline` + `setOffline` (P6)
- [ ] `uiStore.ts` has `'duplicate-warning'` modal type (G7, G8)

### Realtime (P1)
- [ ] `RealtimeProvider` mounted in `AppShell` wrapping all authenticated routes
- [ ] `useRealtimeEvent` hook exists (even as no-op placeholder)
- [ ] No component calls `setInterval` directly for polling
- [ ] Notification polling pauses when tab hidden and resumes on focus/visibility change (R4)
- [ ] Notification polling uses exponential retry after repeated failures (R4)
- [ ] Notifications deduped by `notification_id`, max 50, latest-first (P9)

### Optimistic Updates (P3)
- [ ] Mark notification read → optimistic (P3)
- [ ] Approve/reject assignment → optimistic (P3)
- [ ] Verify field (doctor) → optimistic (P3)
- [ ] Patient verify field → optimistic (P3)
- [ ] Admin deactivate/activate user → optimistic (P3)
- [ ] All optimistic mutations rollback on error via `onError` (P3)

### Skeleton Loaders (P12)
- [ ] All tables show Skeleton rows while loading (P12)
- [ ] All stat cards show Skeleton while loading (P12)
- [ ] FileViewer shows Skeleton while blob fetching (P12)
- [ ] Analytics chart shows Skeleton while loading (P12)
- [ ] No empty tables visible during loading (P12)

### Offline / Error Recovery (P6)
- [ ] `NetworkDisconnectedBanner` mounted at App root, listens to window online/offline events
- [ ] `RetryPanel` used for all `isError` states on data sections
- [ ] `AutoReconnectIndicator` shown inside RetryPanel
- [ ] Queued mutations/draft persistence are documented as production roadmap, not MVP scope (R7)

### FileViewer (P7)
- [ ] PDF: page navigation controls, zoom dropdown (50%–150%), Skeleton while loading
- [ ] Image: pan, zoom, rotate, reset controls
- [ ] Blob URL revoked on unmount
- [ ] RetryPanel on load failure
- [ ] ARIA labels present (P8)

### Accessibility (P8)
- [ ] All modals: focus trap + Escape closes + `role="dialog"` + `aria-modal="true"`
- [ ] All loading: `role="status"` + `aria-live="polite"`
- [ ] All errors: `role="alert"` + `aria-live="assertive"`
- [ ] Notification bell: `aria-label` with unread count
- [ ] Charts: `aria-label` with field name + trend direction
- [ ] Color never used as sole indicator — always paired with icon/label
- [ ] Tables: `th scope="col"` present
- [ ] All buttons keyboard-activatable (Enter/Space)

### Component Behaviour
- [ ] FieldsTable: `is_final=true` → violet lock icon, no action (G3)
- [ ] FieldsTable: patient HITL unverified → `display_value`, no action
- [ ] DuplicateWarningModal implemented for both TIER 1 + TIER 2 (G8)
- [ ] UploadDropzone exposes `onProgress` prop (P2 — even if unused now)
- [ ] UploadDropzone exposes duplicate state to parent — no direct toast (G8)
- [ ] TrendLineChart: null-guards ref_low/ref_high before ReferenceArea render
- [ ] AbnormalityPanel props are `ClinicalField[]` not `ReportField[]` (G12)
- [ ] ChatWindow doctor path uses type guards + renders structured response (G10)
- [ ] ChatWindow patient path reads `patientResult.disclaimer` as field (G11)
- [ ] Chat messages remain local state only for MVP; persistence is production roadmap (R6)
- [ ] PatientChatPage disclaimer banner: sticky, no dismiss (safety requirement)
- [ ] Every patient assistant bubble shows `patientResult.disclaimer` footer (G11)

### Page Behaviour
- [ ] Doctor UploadPage: patient UID confirmed before file area enables (security)
- [ ] Doctor UploadPage: 409 → DuplicateWarningModal (not generic toast) (G8)
- [ ] Doctor UploadPage: 429 → specific rate limit toast (not generic error)
- [ ] ReportDetailPage: `is_duplicate=true` shows amber info banner (G8)
- [ ] ReportDetailPage: re-upload hidden if any `is_final=true` field (G3)
- [ ] MyReportsPage: filter uses `inferred_document_type`; 'unknown' → 'Processing' (G9)
- [ ] AnalyticsPage: displays `ai_insight` text (not `insight`) (G12)
- [ ] HITLOverviewPage: includes `patient_uid` column (G2)
- [ ] Admin UsersPage: deactivate optimistic — instant status change (P3)

### Auth Architecture
- [ ] `client.ts` has `// P13` comment placeholder in response interceptor
- [ ] `authApi.refresh` endpoint defined in `api/auth.ts` (wired up later in P13)
- [ ] No refresh logic implemented in MVP (intentional — P13)

### Build
- [ ] `npm run build` — zero TS errors, zero warnings
- [ ] No hardcoded hex colors — clinical palette tokens only
- [ ] All pages responsive at 1280px minimum width
- [ ] React Query cache invalidated after every mutation
