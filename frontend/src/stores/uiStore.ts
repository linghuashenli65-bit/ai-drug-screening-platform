import { create } from 'zustand';

interface UIState {
  sidebarCollapsed: boolean;
  notifications: Notification[];
  toggleSidebar: () => void;
  addNotification: (n: Omit<Notification, 'id' | 'timestamp'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;
}

export interface Notification {
  id: string;
  type: 'success' | 'error' | 'info' | 'warning';
  title: string;
  message?: string;
  timestamp: number;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarCollapsed: false,
  notifications: [],

  toggleSidebar: () =>
    set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  addNotification: (n) =>
    set((s) => ({
      notifications: [
        ...s.notifications,
        { ...n, id: Date.now().toString(), timestamp: Date.now() },
      ],
    })),

  removeNotification: (id) =>
    set((s) => ({
      notifications: s.notifications.filter((n) => n.id !== id),
    })),

  clearNotifications: () => set({ notifications: [] }),
}));
