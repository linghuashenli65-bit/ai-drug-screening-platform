import api from './api';
import type { Drug, DrugLibStats, PaginatedResponse } from '../types';

export const drugLibService = {
  async getStats(): Promise<DrugLibStats> {
    const res = await api.get<DrugLibStats>('/libraries/stats');
    return res.data;
  },

  async listDrugs(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    source?: string;
  }): Promise<PaginatedResponse<Drug>> {
    const res = await api.get<PaginatedResponse<Drug>>('/libraries/drugs', { params });
    return res.data;
  },

  async getDrug(drugId: number | string): Promise<Drug> {
    const res = await api.get<Drug>(`/libraries/drugs/${drugId}`);
    return res.data;
  },

  async uploadDrugCsv(formData: FormData): Promise<{ imported: number; errors: string[] }> {
    const res = await api.post('/libraries/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    });
    return res.data;
  },
};
