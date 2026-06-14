import api from './api';
import type {
  CreateJobRequest,
  CreateJobResponse,
  DashboardStats,
  Job,
  JobListParams,
  PaginatedResponse,
  AgentNode,
} from '../types';

export const taskService = {
  async createJob(data: CreateJobRequest): Promise<CreateJobResponse> {
    const res = await api.post<CreateJobResponse>('/screenings', data);
    return res.data;
  },

  async createJobWithFiles(formData: FormData): Promise<CreateJobResponse> {
    const res = await api.post<CreateJobResponse>('/screenings', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return res.data;
  },

  async getJob(jobId: number | string): Promise<Job> {
    const res = await api.get<Job>(`/screenings/${jobId}`);
    const job = res.data;
    // 填充兼容字段
    return { ...job, job_id: job.id };
  },

  async listJobs(params?: JobListParams): Promise<PaginatedResponse<Job>> {
    const res = await api.get<PaginatedResponse<Job>>('/screenings', { params });
    const data = res.data;
    const items = (data.items || []).map(j => ({ ...j, job_id: j.id }));
    return { items, total: data.total, page: data.page, page_size: data.page_size };
  },

  async getStats(): Promise<DashboardStats> {
    const res = await api.get<DashboardStats>('/screenings/stats');
    return res.data;
  },

  async cancelJob(jobId: number | string): Promise<void> {
    await api.post(`/screenings/${jobId}/cancel`);
  },

  async getJobNodes(jobId: string): Promise<AgentNode[]> {
    try {
      const res = await api.get<AgentNode[]>(`/screenings/${jobId}/nodes`, { _silent: true } as Record<string, unknown>);
      return res.data || [];
    } catch {
      return [];
    }
  },

  async getNodeLogs(jobId: string, nodeId: string): Promise<string[]> {
    try {
      const res = await api.get<string[]>(`/screenings/${jobId}/nodes/${nodeId}/logs`, { _silent: true } as Record<string, unknown>);
      return res.data || [];
    } catch {
      return [];
    }
  },

  getJobProgressSSEUrl(jobId: string): string {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    return `${baseUrl}/screenings/${jobId}/events`;
  },
};
