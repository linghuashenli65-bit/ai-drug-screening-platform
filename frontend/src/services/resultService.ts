import api from './api';
import type { DockingResult, PaginatedResponse } from '../types';

interface TopHitsResponse {
  job_id: number;
  total_hits: number;
  top_hits: DockingResult[];
}

export const resultService = {
  async getJobResults(
    jobId: string,
    params?: { page?: number; page_size?: number; sort_by?: string; search?: string }
  ): Promise<PaginatedResponse<DockingResult>> {
    const res = await api.get<TopHitsResponse>(
      `/screenings/${jobId}/results`,
      { params, _silent: true } as Record<string, unknown>
    );
    const data = res.data;
    return {
      items: data.top_hits || [],
      total: data.total_hits || 0,
      page: params?.page || 1,
      page_size: params?.page_size || 20,
    };
  },

  async getTopHits(jobId: string, topN?: number): Promise<DockingResult[]> {
    const res = await api.get<TopHitsResponse>(`/screenings/${jobId}/results`, {
      params: { n: topN || 20 },
      _silent: true,
    } as Record<string, unknown>);
    return res.data.top_hits || [];
  },

  async getDrugDetail(jobId: string, drugId: string): Promise<DockingResult> {
    const res = await api.get<DockingResult>(
      `/screenings/${jobId}/results/${drugId}`
    );
    return res.data;
  },
};
