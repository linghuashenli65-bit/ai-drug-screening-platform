import { create } from 'zustand';
import type { Job, JobStatus } from '../types';
import { taskService } from '../services/taskService';

interface TaskState {
  currentJob: Job | null;
  isPolling: boolean;
  pollingRate: number;

  setCurrentJob: (job: Job | null) => void;
  fetchJob: (jobId: string) => Promise<void>;
  startPolling: (jobId: string) => () => void;
  updateJobFromSSE: (data: Partial<Job>) => void;
  cancelJob: (jobId: string) => Promise<void>;
}

export const useTaskStore = create<TaskState>((set, get) => ({
  currentJob: null,
  isPolling: false,
  pollingRate: 2000,

  setCurrentJob: (job) => set({ currentJob: job }),

  fetchJob: async (jobId: string) => {
    const job = await taskService.getJob(jobId);
    set({ currentJob: job });
  },

  startPolling: (jobId: string) => {
    set({ isPolling: true });
    const interval = setInterval(async () => {
      try {
        const job = await taskService.getJob(jobId);
        set({ currentJob: job });
        const terminalStatuses: JobStatus[] = [
          'COMPLETED',
          'FAILED',
          'CANCELLED',
        ];
        if (terminalStatuses.includes(job.status)) {
          clearInterval(interval);
          set({ isPolling: false });
        }
      } catch {
        // Silently retry
      }
    }, get().pollingRate);

    return () => {
      clearInterval(interval);
      set({ isPolling: false });
    };
  },

  updateJobFromSSE: (data) => {
    set((state) => ({
      currentJob: state.currentJob
        ? { ...state.currentJob, ...data }
        : (data as Job),
    }));
  },

  cancelJob: async (jobId: string) => {
    await taskService.cancelJob(jobId);
    const job = await taskService.getJob(jobId);
    set({ currentJob: job });
  },
}));
