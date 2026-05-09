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
  isOffline: boolean;
  setSidebarOpen: (open: boolean) => void;
  openModal: (modal: ModalType, payload?: Record<string, unknown>) => void;
  closeModal: () => void;
  setOffline: (offline: boolean) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  activeModal: null,
  modalPayload: null,
  isOffline: false,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  openModal: (modal, payload) =>
    set({ activeModal: modal, modalPayload: payload ?? null }),
  closeModal: () => set({ activeModal: null, modalPayload: null }),
  setOffline: (offline) => set({ isOffline: offline }),
}));
