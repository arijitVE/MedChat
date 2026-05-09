export const queryKeys = {
  reports: {
    all: ['reports'] as const,
    list: (filters?: object) => ['reports', filters] as const,
    detail: (id: string) => ['reports', id] as const,
    fields: (id: string) => ['reports', id, 'fields'] as const,
    rawFile: (id: string) => ['reports', id, 'raw-file'] as const,
    forPatient: (patientId: string) => ['reports', 'patient', patientId] as const,
    eda: (id: string) => ['reports', id, 'eda'] as const,
  },
  patients: {
    all: ['patients'] as const,
    search: (query: string) => ['patients', 'search', query] as const,
    detail: (id: string) => ['patients', id] as const,
    profile: (id: string) => ['patients', id, 'profile'] as const,
    analytics: (id: string) => ['patients', id, 'analytics'] as const,
    trend: (id: string, field: string) => ['patients', id, 'trend', field] as const,
  },
  doctor: {
    dashboard: ['doctor', 'dashboard'] as const,
  },
  assignments: {
    doctor: ['assignments', 'doctor'] as const,
    patient: ['assignments', 'patient'] as const,
  },
  notifications: {
    all: (role: string) => ['notifications', role] as const,
  },
  admin: {
    stats: ['admin', 'stats'] as const,
    usersAll: ['admin', 'users'] as const,
    users: (filters?: object) => ['admin', 'users', filters] as const,
    hitlQueue: ['admin', 'hitl'] as const,
  },
  hitlQueue: (myPatientsOnly: boolean) => ['hitl-queue', myPatientsOnly] as const,
} as const;

export const staleTime = {
  reportDetail: 30_000,
  reportFields: 30_000,
  notifications: 60_000,
  adminStats: 30_000,
  analytics: 300_000,
  trends: 300_000,
  patientList: 60_000,
  hitlQueue: 30_000,
  usersList: 60_000,
} as const;
