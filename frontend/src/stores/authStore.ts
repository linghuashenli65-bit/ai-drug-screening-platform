import { create } from 'zustand';
import type { User, LoginRequest, RegisterRequest } from '../types';
import { authService } from '../services/authService';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => void;
  clearError: () => void;
  hasRole: (roles: string[]) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false, // verified via fetchUser, not trust localStorage alone
  isLoading: false,
  error: null,

  login: async (data: LoginRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.login(data);
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('refresh_token', res.refresh_token);
      set({ user: res.user, isAuthenticated: true, isLoading: false });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || '登录失败，请检查用户名和密码';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  register: async (data: RegisterRequest) => {
    set({ isLoading: true, error: null });
    try {
      const res = await authService.register(data);
      localStorage.setItem('access_token', res.access_token);
      localStorage.setItem('refresh_token', res.refresh_token);
      set({ user: res.user, isAuthenticated: true, isLoading: false });
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message || '注册失败';
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  fetchUser: async () => {
    try {
      const user = await authService.getMe();
      set({ user, isAuthenticated: true });
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({ user: null, isAuthenticated: false });
    }
  },

  logout: () => {
    authService.logout();
    set({ user: null, isAuthenticated: false });
  },

  clearError: () => set({ error: null }),

  hasRole: (roles: string[]) => {
    const user = get().user;
    if (!user) return false;
    return roles.includes(user.role);
  },
}));
