# DocuMed-AI Project Tree

Tags: #documed-ai #hdims #project-map #architecture

This note maps the current DocuMed-AI / HDIMS repository for Obsidian. It explains the purpose of each main folder and each project file that is part of the source, configuration, tests, documentation, or sample assets.

## Project Purpose

DocuMed-AI is a healthcare document management and intelligence system. It lets patients and doctors upload medical PDFs/images, runs OCR and LLM extraction through Pipeline A, stores structured clinical fields in a product database layer, and exposes analytics, trend detection, retrieval, notifications, HITL review, and role-based dashboards through Pipeline B and the React frontend.

## Runtime And Generated Folders

These folders exist in the workspace but are not treated as source-tree content:

- `.git/` - Git repository metadata.
- `.venv/` - Local Python virtual environment.
- `__pycache__/` - Python bytecode cache.
- `pytest-cache-files-7uwfpzvm/` - Locked/generated pytest cache artifact.
- `pytest-cache-files-9jegwmwj/` - Locked/generated pytest cache artifact.
- `qdrant_storage/` - Local Qdrant vector database storage.
- `frontend/node_modules/`, if present - Installed frontend dependencies.

## Root

- `.env` - Local runtime secrets and environment values. Do not publish or commit.
- `.env.example` - Safe template showing required environment variables.
- `.gitignore` - Ignore rules for secrets, virtualenvs, caches, local storage, logs, frontend builds, and sample reports.
- `README.md` - Main system documentation covering purpose, architecture, setup, routes, roles, and workflows.
- `PROJECT_TREE_OBSIDIAN.md` - This Obsidian-ready project tree and purpose map.
- `requirements.txt` - Python dependencies for FastAPI, SQLAlchemy, OCR, OpenAI/LangChain, Qdrant, Celery, auth, and tests.
- `pyrightconfig.json` - Pyright static type checker configuration.
- `main.py` - FastAPI application entrypoint; loads env, mounts routers, configures CORS, serves `/dashboard`, and exposes `/health`.
- `run_pipeline_a.py` - Local script for running Pipeline A processing manually.
- `seed_admin.py` - Local helper to create/seed an admin user.
- `check_db2.py` - Database connectivity/debug helper.
- `fix_background_tasks.py` - Helper script for adjusting or debugging background task behavior.
- `test_manual.py` - Manual integration-style checks for the document pipeline.
- `test_qdrant.py` - Manual Qdrant connectivity/vector-store test.
- `HDMIS_Frontend_Blueprint.md` - Frontend product/design blueprint.
- `HDMIS_Pipeline_A_Blueprint .md` - Pipeline A OCR/extraction blueprint.
- `HDMIS_Pipeline_B_Blueprint.md` - Pipeline B intelligence/retrieval blueprint.
- `HDMIS_Product_Layer_Blueprint.md` - Product API/business-layer blueprint.
- `LongReport.pdf` - Ignored sample medical PDF used for local/manual testing.
- `report.pdf` - Ignored sample report PDF used for local/manual testing.
- `newreport.jpeg` - Ignored sample report image used for local/manual testing.

## `dashboard/`

Static HTML dashboard mounted by FastAPI at `/dashboard`.

- `dashboard/__init__.py` - Python package marker.
- `dashboard/index.html` - Static dashboard landing/admin-style page.
- `dashboard/patient.html` - Static patient dashboard page.

## `frontend/`

React 18 + TypeScript + Vite application for patient, doctor, and admin workflows.

- `frontend/.gitignore` - Frontend-specific ignore rules.
- `frontend/README.md` - Vite/React starter documentation and frontend command notes.
- `frontend/package.json` - Frontend scripts and dependencies.
- `frontend/package-lock.json` - Locked npm dependency graph.
- `frontend/index.html` - Vite HTML shell.
- `frontend/vite.config.ts` - Vite React build/dev-server configuration.
- `frontend/tsconfig.json` - Root TypeScript project references.
- `frontend/tsconfig.app.json` - TypeScript config for browser app code.
- `frontend/tsconfig.node.json` - TypeScript config for Node-side tooling files.
- `frontend/eslint.config.js` - ESLint flat config for React and TypeScript.
- `frontend/tailwind.config.ts` - Tailwind theme/content configuration.
- `frontend/postcss.config.js` - PostCSS configuration for Tailwind.

### `frontend/public/`

Static assets copied directly into the frontend build.

- `frontend/public/favicon.ico` - Browser favicon placeholder/icon.
- `frontend/public/favicon.svg` - SVG favicon asset.

### `frontend/src/`

Main frontend source tree.

- `frontend/src/main.tsx` - React root; sets up BrowserRouter, TanStack Query, and app providers.
- `frontend/src/App.tsx` - Role-based route map and guards for auth, doctor approval, patient, doctor, and admin screens.
- `frontend/src/index.css` - Global Tailwind CSS imports.

### `frontend/src/api/`

Axios API clients matching backend product/intelligence endpoints.

- `frontend/src/api/client.ts` - Shared Axios client with base URL, token injection, refresh handling, and login redirect behavior.
- `frontend/src/api/auth.ts` - Login, signup, logout, refresh, and profile API calls.
- `frontend/src/api/admin.ts` - Admin API calls for users, reports, assignments, HITL, health, notifications, and password reset.
- `frontend/src/api/assignments.ts` - Doctor/patient assignment API calls.
- `frontend/src/api/intelligence.ts` - Pipeline B analytics, trends, doctor assistant, and patient chat API calls.
- `frontend/src/api/notifications.ts` - Notification list/read API calls.
- `frontend/src/api/reports.ts` - Report search, detail, field, upload, reupload, raw-file, and release API calls.
- `frontend/src/api/verification.ts` - Field/report verification and edit API calls.

### `frontend/src/components/`

Reusable UI, layout, report, chart, notification, assistant, and feedback components.

- `frontend/src/components/assistant/DoctorFloatingAssistant.tsx` - Doctor-facing floating assistant UI for query modes, patient context, and intelligence results.
- `frontend/src/components/charts/AbnormalityPanel.tsx` - Highlights abnormal clinical fields.
- `frontend/src/components/charts/FieldBarChart.tsx` - Bar chart for report field values.
- `frontend/src/components/charts/PatientAnalyticsDashboard.tsx` - Rich patient analytics dashboard with summaries, ranges, trends, and charts.
- `frontend/src/components/charts/TrendLineChart.tsx` - Line chart for clinical field trend history.
- `frontend/src/components/chat/ChatInput.tsx` - Placeholder chat input module.
- `frontend/src/components/chat/ChatMessage.tsx` - Placeholder chat message module.
- `frontend/src/components/chat/ChatWindow.tsx` - Placeholder chat window module.
- `frontend/src/components/feedback/AutoReconnectIndicator.tsx` - UI indicator for reconnect/polling recovery state.
- `frontend/src/components/feedback/NetworkDisconnectedBanner.tsx` - Global network offline/disconnected banner.
- `frontend/src/components/feedback/RetryPanel.tsx` - Retry/error recovery panel.
- `frontend/src/components/layout/AppShell.tsx` - Shared authenticated layout with sidebar/topbar and nested route outlet.
- `frontend/src/components/layout/Sidebar.tsx` - Role-specific navigation links.
- `frontend/src/components/layout/Topbar.tsx` - Top navigation bar with profile/notification affordances.
- `frontend/src/components/notifications/NotificationBell.tsx` - Notification bell with unread count.
- `frontend/src/components/notifications/NotificationPanel.tsx` - Notification list panel with read handling.
- `frontend/src/components/report/DuplicateWarningModal.tsx` - Duplicate upload confirmation modal.
- `frontend/src/components/report/FieldRow.tsx` - Single report-field row with value/status/verification controls.
- `frontend/src/components/report/FieldsTable.tsx` - Table of extracted/verified report fields.
- `frontend/src/components/report/ReportCard.tsx` - Compact report summary card.
- `frontend/src/components/report/ReportStatusBadge.tsx` - Lifecycle status badge.
- `frontend/src/components/report/UploadDropzone.tsx` - File upload dropzone with validation/progress callbacks.
- `frontend/src/components/ui/Badge.tsx` - Shared badge primitive.
- `frontend/src/components/ui/Button.tsx` - Shared button primitive.
- `frontend/src/components/ui/Card.tsx` - Shared card primitive.
- `frontend/src/components/ui/EmptyState.tsx` - Empty-state UI primitive.
- `frontend/src/components/ui/Modal.tsx` - Accessible modal primitive with focus management.
- `frontend/src/components/ui/Pagination.tsx` - Pagination controls.
- `frontend/src/components/ui/Skeleton.tsx` - Loading skeleton variants.
- `frontend/src/components/ui/Spinner.tsx` - Loading spinner.
- `frontend/src/components/ui/Table.tsx` - Shared table primitives.
- `frontend/src/components/ui/Toast.tsx` - Toast notification primitive.

### `frontend/src/hooks/`

React hooks wrapping API calls, cache keys, mutations, optimistic updates, and auth state.

- `frontend/src/hooks/useAssignments.ts` - Assignment query/mutation hooks.
- `frontend/src/hooks/useAuth.ts` - Login/signup/logout/profile hooks and auth normalization.
- `frontend/src/hooks/useIntelligence.ts` - Trend, analytics, doctor query, and patient chat hooks.
- `frontend/src/hooks/useNotifications.ts` - Notification query and mark-read hooks.
- `frontend/src/hooks/useRealtimeEvent.ts` - Browser event listener hook for realtime-style events.
- `frontend/src/hooks/useReports.ts` - Report list/detail/upload/reupload/raw-file/release hooks.
- `frontend/src/hooks/useVerification.ts` - Field/report verification, edit, unlock, and cache update hooks.

### `frontend/src/lib/`

Small frontend utilities.

- `frontend/src/lib/apiError.ts` - Normalizes Axios/backend errors into UI-friendly error objects.
- `frontend/src/lib/queryKeys.ts` - Central TanStack Query cache keys and stale-time values.
- `frontend/src/lib/reportName.ts` - Builds human-readable report display names.
- `frontend/src/lib/sanitize.ts` - Sanitizes filenames and display text.

### `frontend/src/pages/`

Route-level screens grouped by role.

- `frontend/src/pages/auth/LoginPage.tsx` - Login form and auth redirect flow.
- `frontend/src/pages/auth/SignupPage.tsx` - Signup form for patient/doctor onboarding.

#### `frontend/src/pages/patient/`

- `AccountPage.tsx` - Patient profile/account page.
- `MyReportsPage.tsx` - Patient report list/search/upload surface.
- `NotificationsPage.tsx` - Patient notifications page.
- `PatientChatPage.tsx` - Patient assistant/chat page with safety disclaimer and stored-report context.
- `PatientDashboard.tsx` - Patient dashboard summary page.
- `ReportViewPage.tsx` - Patient report detail and field view.
- `TrendsPage.tsx` - Patient trends/analytics page.

#### `frontend/src/pages/doctor/`

- `AccountPage.tsx` - Doctor account/profile page.
- `AnalyticsOverviewPage.tsx` - Doctor analytics patient selection/overview page.
- `AnalyticsPage.tsx` - Doctor patient-specific analytics page.
- `DoctorDashboard.tsx` - Doctor dashboard summary page.
- `HITLQueuePage.tsx` - Doctor HITL review queue.
- `NotificationsPage.tsx` - Doctor notifications page.
- `PatientDetailPage.tsx` - Doctor view of an assigned patient.
- `PatientListPage.tsx` - Doctor patient list/search page.
- `ReportDetailPage.tsx` - Doctor report detail, verification, and release page.
- `ReportsPage.tsx` - Doctor report list/search page.
- `UploadPage.tsx` - Doctor upload/reupload page with duplicate handling.
- `VerificationPendingPage.tsx` - Waiting page for unapproved doctor accounts.

#### `frontend/src/pages/admin/`

- `AdminDashboard.tsx` - Admin dashboard quick links and system stats.
- `AdminReportDetailPage.tsx` - Admin report detail and verification controls.
- `AdminUtils.tsx` - Shared admin page header, stats, and query-state helpers.
- `adminFormat.ts` - Admin date formatting helper.
- `AnalyticsPage.tsx` - Admin analytics metrics table page.
- `AssignmentsPage.tsx` - Admin doctor-patient assignment management.
- `AuditLogsPage.tsx` - Admin audit-log listing.
- `DoctorsPage.tsx` - Admin doctor list/verification surface.
- `FailedJobsPage.tsx` - Admin failed processing jobs page.
- `HITLOverviewPage.tsx` - Admin HITL queue overview.
- `HITLReportDetailPage.tsx` - Admin HITL report detail screen.
- `LogoutPage.tsx` - Logout side-effect route.
- `NotificationsPage.tsx` - Admin notifications page.
- `PatientsPage.tsx` - Admin patient list page.
- `ReportsPage.tsx` - Admin report listing/filtering page.
- `SettingsPage.tsx` - Admin settings page.
- `SystemHealthPage.tsx` - Admin system health page.
- `UsersPage.tsx` - Admin user list, activation, and password reset page.

### `frontend/src/providers/`

- `RealtimeProvider.tsx` - Polling/event provider that surfaces report, field, and assignment updates.

### `frontend/src/store/`

Zustand stores.

- `authStore.ts` - Persisted authentication state and user/session actions.
- `uiStore.ts` - UI modal/sidebar/toast state.

### `frontend/src/types/`

TypeScript DTOs shared across API, hooks, and pages.

- `admin.ts` - Admin stats, users, assignments, reports, HITL, audit, health, and settings types.
- `assignment.ts` - Assignment and profile types.
- `auth.ts` - User, token, signup, login, and specialization types.
- `common.ts` - Pagination params and paginated response helpers.
- `intelligence.ts` - Trend, reasoning, retrieval, chat, analytics, and assistant request/response types.
- `notification.ts` - Notification item/list types.
- `report.ts` - Report, field, upload, lifecycle, duplicate-warning, and status types.
- `verification.ts` - Field verification/edit/report verification types.

### `frontend/src/validation/`

Zod validation schemas.

- `authSchemas.ts` - Login and signup validation.
- `uploadSchemas.ts` - File type and upload-size validation.
- `verificationSchemas.ts` - Field verification/edit validation.

## `infra/`

Infrastructure helpers for local services and async workers.

- `infra/docker/Dockerfile` - Backend container image definition.
- `infra/docker/docker-compose.yml` - Local service composition, including backend/support services.
- `infra/queue/celery_config.py` - Celery app/broker configuration.
- `infra/scripts/migrate.sh` - Shell helper for applying database migrations.
- `infra/scripts/seed_data.sh` - Shell helper for seeding local data.

## `migrations/`

Ordered SQL migrations for the product database schema.

- `001_product_layer_schema.sql` - Initial product-layer schema.
- `002_remove_structured_text.sql` - Removes/changes structured-text schema elements.
- `003_fix_product_layer_schema_issues.sql` - Fixes early product schema issues.
- `004_file_storage_refs.sql` - Adds raw uploaded-file storage reference tracking.
- `005_file_storage_refs_version.sql` - Adds storage versioning/upload-count support.
- `006_allow_failed_report_lifecycle_status.sql` - Allows failed lifecycle status.
- `007_patient_profile_fields.sql` - Adds patient profile fields.
- `008_doctor_profile_verification.sql` - Adds doctor verification/profile fields.
- `009_allow_admin_field_verifier.sql` - Allows admin users to verify fields.

## `pipeline_a/`

Pipeline A converts uploaded PDFs/images into structured report data through ingestion, OCR, LLM extraction, normalization, matching, confidence scoring, conflict resolution, and HITL routing.

- `pipeline_a/__init__.py` - Python package marker.

### `pipeline_a/api/`

- `__init__.py` - Package marker.
- `routes.py` - Direct Pipeline A upload/status API routes.

### `pipeline_a/confidence/`

- `__init__.py` - Package marker.
- `scorer.py` - Combines OCR confidence, matching scores, and extraction signals into field confidence/status.

### `pipeline_a/conflict/`

- `__init__.py` - Package marker.
- `resolver.py` - Resolves scored fields into final Pipeline A output and persists job/report field data.

### `pipeline_a/hitl/`

Human-in-the-loop review support.

- `__init__.py` - Package marker.
- `api.py` - HITL-related API helpers/routes.
- `queue.py` - HITL queue primitives.
- `service.py` - HITL service logic for review states and field updates.

### `pipeline_a/ingestion/`

- `__init__.py` - Package marker.
- `loader.py` - File loading, MIME detection, document type detection, and ingestion object creation.

### `pipeline_a/llm_extraction/`

- `__init__.py` - Package marker.
- `extractor.py` - LLM extraction client/retry flow for clinical fields.
- `fallback.py` - Regex/rule fallback extraction when LLM output fails.
- `parser.py` - Parses/validates LLM responses into structured fields.
- `prompts/prescription_prompt.txt` - Prompt template for prescription extraction.

### `pipeline_a/matching/`

- `__init__.py` - Package marker.
- `matcher.py` - Matches normalized extracted fields back to OCR text using fuzzy/semantic scoring.

### `pipeline_a/normalization/`

- `__init__.py` - Package marker.
- `normalizer.py` - Normalizes field names, values, units, and dates.

### `pipeline_a/ocr/`

- `__init__.py` - Package marker.
- `client.py` - Google Vision/PDF-image OCR client logic.
- `confidence.py` - Aggregates OCR word confidence and low-confidence flags.
- `parser.py` - Parses OCR provider responses into raw text and word-level boxes.

### `pipeline_a/orchestrator/`

- `__init__.py` - Package marker.
- `process_document.py` - Runs all Pipeline A stages in order and records success/failure status.

### `pipeline_a/worker/`

- `__init__.py` - Package marker.
- `tasks.py` - Celery/background task entrypoints for Pipeline A processing.

## `pipeline_b/`

Pipeline B powers retrieval, trend analysis, analytics, cached responses, and doctor/patient intelligence features using Pipeline A outputs and report data.

- `pipeline_b/__init__.py` - Python package marker.

### `pipeline_b/adapters/`

- `__init__.py` - Package marker.
- `pipeline_a_adapter.py` - Adapts Pipeline A job/report output into query-friendly Pipeline B records.

### `pipeline_b/api/`

Legacy direct Pipeline B API routes.

- `__init__.py` - Package marker.
- `doctor_routes.py` - Direct doctor intelligence routes.
- `patient_routes.py` - Direct patient intelligence routes.

### `pipeline_b/cache/`

- `__init__.py` - Package marker.
- `response_cache.py` - In-memory/patient-scoped cache helpers and invalidation.

### `pipeline_b/chunking/`

- `__init__.py` - Package marker.
- `chunker.py` - Splits structured text into chunks for embedding/retrieval.

### `pipeline_b/embedding/`

- `__init__.py` - Package marker.
- `embedder.py` - Embedding helper for retrieval vectors.

### `pipeline_b/engines/`

- `__init__.py` - Package marker.
- `generator.py` - Generates natural-language responses from retrieved/structured data.
- `intent_parser.py` - Parses user text into field/date/filter intent.
- `query_classifier.py` - Classifies queries by persona and query type.
- `retriever.py` - Retrieves relevant patient/report chunks.
- `trend_analyzer.py` - Computes clinical trend direction and summary stats.

### `pipeline_b/ingestion/`

- `__init__.py` - Package marker.
- `ingest.py` - Ingests patient/report records into Pipeline B retrieval structures.

### `pipeline_b/schemas/`

- `__init__.py` - Package marker.
- `input.py` - Input DTOs for Pipeline B processing.
- `output.py` - Output DTOs for reasoning, retrieval, trends, analytics, and chat.
- `query.py` - Query classification/persona schema definitions.

### `pipeline_b/services/`

- `__init__.py` - Package marker.
- `analytics_service.py` - Patient/report analytics aggregation service.
- `patient_service.py` - Patient chat and simplified report answer service.
- `reasoning_service.py` - Doctor reasoning assistant service.
- `retrieval_service.py` - Retrieval orchestration service.
- `trend_service.py` - Trend analysis service wrapper.

### `pipeline_b/vector_db/`

- `__init__.py` - Package marker.
- `qdrant_client.py` - Qdrant vector database client/collection helper.

## `product/`

Product layer containing role-protected FastAPI routes, auth, schemas, services, and storage helpers used by the React app.

- `product/__init__.py` - Python package marker.

### `product/api/`

- `__init__.py` - Package marker.
- `admin_routes.py` - Admin routes for stats, users, assignments, reports, HITL, audit, notifications, health, verification, and password reset.
- `auth_routes.py` - Login, signup, logout, refresh, and current-user auth routes.
- `doctor_routes.py` - Approved-doctor routes for upload, reports, verification, assignments, notifications, analytics, and assistant queries.
- `patient_routes.py` - Patient routes for upload, report search/detail/EDA/verification, assignments, notifications, trends, analytics, and chat.
- `user_routes.py` - Shared current-user/profile routes.

### `product/auth/`

- `__init__.py` - Package marker.
- `jwt_handler.py` - JWT access/refresh token creation and decoding.
- `middleware.py` - Auth dependency/middleware utilities for current user extraction.
- `password.py` - Password hashing and verification.
- `rate_limit.py` - Upload/auth rate-limiting helpers.
- `role_guard.py` - Role and approved-doctor dependency guards.

### `product/schemas/`

- `__init__.py` - Package marker.
- `admin.py` - Admin response/request schemas.
- `assignment.py` - Assignment request/response schemas.
- `auth.py` - Auth request/token schemas.
- `notification.py` - Notification schemas.
- `report.py` - Report/upload/status schemas.
- `user.py` - User and profile schemas.
- `verification.py` - Field/report verification schemas.

### `product/services/`

- `__init__.py` - Package marker.
- `admin_service.py` - Admin business logic for users, reports, assignments, stats, audit, health, and settings.
- `assignment_service.py` - Doctor-patient assignment creation, acceptance/rejection, listing, and access verification.
- `auth_service.py` - Signup/login/refresh/logout/current-user business logic.
- `notification_service.py` - Notification listing, creation, and read-state logic.
- `report_service.py` - Report retrieval, search, EDA, release, raw-file access, and lifecycle helpers.
- `search_service.py` - Patient-facing report search filters.
- `upload_service.py` - Upload/reupload flow, MIME/size validation, duplicate detection, file storage, report creation, audit, notifications, background processing, and Pipeline B invalidation.
- `verification_service.py` - Field/report verification, edits, unlocks, audit, notification, and lifecycle updates.

### `product/utils/`

- `file_storage.py` - File hashing and upload file persistence helpers.

## `shared/`

Shared backend configuration, logging, database models/session helpers, schemas, and utilities used across product, Pipeline A, and Pipeline B.

- `shared/__init__.py` - Python package marker.
- `shared/config.py` - Pydantic settings loaded from environment variables.
- `shared/logger.py` - Structured logging configuration/helpers.

### `shared/db/`

- `__init__.py` - Package marker.
- `base.py` - SQLAlchemy declarative base.
- `session.py` - SQLAlchemy engine/session factory and FastAPI DB dependency.
- `upsert.py` - Cross-database upsert statement helper.

### `shared/db/models/`

- `__init__.py` - Package marker.
- `confidence.py` - ORM model(s) for confidence-scoring data.
- `document.py` - `document_jobs` ORM model and upsert helper for processing lifecycle.
- `extraction.py` - ORM model(s) for extraction/normalized field data.
- `hitl.py` - ORM model(s) for human-in-the-loop review data.
- `matching.py` - ORM model(s) for field matching scores.
- `ocr.py` - ORM model(s) for OCR text/word data.

### `shared/schemas/`

- `__init__.py` - Package marker.
- `document.py` - Ingested document schema used at Pipeline A input.
- `pipeline.py` - Pipeline context, upload response, and job status response schemas.
- `report.py` - Core Pipeline A enums and Pydantic models for OCR, extraction, normalization, matching, scoring, and final output.

### `shared/utils/`

- `__init__.py` - Package marker.
- `medical_dict.py` - Medical field synonyms, unit dictionaries, and normalization references.
- `text.py` - Shared text normalization/parsing helpers.
- `validators.py` - Shared validation helpers for values, fields, and clinical ranges.

## `tests/`

Backend test suite for Pipeline A, Pipeline B, product APIs/services, and inline unit checks.

- `tests/__init__.py` - Test package marker.
- `tests/test_llm_inline.py` - Inline LLM extraction/parser tests.
- `tests/test_matcher_inline.py` - Inline matcher tests.
- `tests/test_normalizer_inline.py` - Inline normalizer tests.

### `tests/pipeline_a/`

- `__init__.py` - Test package marker.
- `conftest.py` - Pipeline A test fixtures/config.
- `test_conflict.py` - Conflict resolver tests.
- `test_llm_extraction.py` - LLM extraction and fallback tests.
- `test_matching.py` - Field matching tests.
- `test_normalization.py` - Normalization tests.
- `fixtures/sample_lab_ocr.txt` - Sample OCR text fixture.

### `tests/pipeline_b/`

- `__init__.py` - Test package marker.
- `conftest.py` - Pipeline B test fixtures/config.
- `test_adapter.py` - Pipeline A adapter tests.
- `test_cache.py` - Response cache tests.
- `test_classifier.py` - Query classifier tests.
- `test_intent_parser.py` - Intent parser tests.
- `test_reasoning_service.py` - Reasoning service tests.
- `test_trend_service.py` - Trend service tests.
- `fixtures/__init__.py` - Fixture package marker.

### `tests/product/`

- `__init__.py` - Product test package marker.
- `conftest.py` - Product-layer test DB/client fixtures.
- `test_admin.py` - Admin service/API tests.
- `test_assignment.py` - Assignment workflow tests.
- `test_auth.py` - Auth/signup/login tests.
- `test_upload.py` - Upload validation, duplicate, storage, and processing tests.
- `test_upload_flow.py` - End-to-end upload flow tests.
- `test_verification.py` - Field/report verification and lifecycle tests.

## Reading Order

1. `README.md` for the system-level explanation.
2. `main.py` for mounted backend surfaces.
3. `product/api/*_routes.py` and `product/services/*.py` for product behavior.
4. `pipeline_a/orchestrator/process_document.py` for extraction flow.
5. `pipeline_b/services/*.py` and `pipeline_b/engines/*.py` for intelligence flow.
6. `frontend/src/App.tsx` for frontend route layout.
7. `frontend/src/api/`, `frontend/src/hooks/`, and role-specific pages for UI behavior.
