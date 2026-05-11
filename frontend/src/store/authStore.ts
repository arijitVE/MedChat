import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { User } from '../types/auth';

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
  logout: () => void;
}

function clearRefreshToken() {
  localStorage.removeItem('refresh_token');
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      isAuthenticated: false,
      setAuth: (token, user) => set({ token, user, isAuthenticated: true }),
      clearAuth: () => {
        clearRefreshToken();
        set({ token: null, user: null, isAuthenticated: false });
      },
      logout: () => {
        clearRefreshToken();
        set({ token: null, user: null, isAuthenticated: false });
      },
    }),
    {
      name: 'hdmis-auth',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
