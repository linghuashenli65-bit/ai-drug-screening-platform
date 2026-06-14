import api from './api';
import type { Report, PaginatedResponse } from '../types';

export const reportService = {
  async listReports(params?: {
    page?: number;
    page_size?: number;
  }): Promise<PaginatedResponse<Report>> {
    return { items: [], total: 0, page: params?.page || 1, page_size: params?.page_size || 10 };
  },

  async getJobReport(jobId: string): Promise<Report> {
    const res = await api.get<Report>(`/reports/${jobId}`);
    return res.data;
  },

  async downloadReport(jobId: string, format: 'pdf' | 'markdown'): Promise<Blob> {
    const res = await api.get(`/reports/${jobId}/download`, {
      params: { format },
      responseType: 'blob',
    });
    return res.data;
  },

  getReportPreviewUrl(jobId: string): string {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    return `${baseUrl}/reports/${jobId}/preview`;
  },
};
