import api from './api';
import type { Receptor } from '../types';

export const receptorService = {
  async list(params?: {
    search?: string;
    page?: number;
    page_size?: number;
  }): Promise<Receptor[]> {
    const res = await api.get<Receptor[]>('/receptors', { params });
    return res.data;
  },

  async get(receptorId: number): Promise<Receptor> {
    const res = await api.get<Receptor>(`/receptors/${receptorId}`);
    return res.data;
  },

  async create(data: {
    receptor_name: string;
    pdb_code?: string;
    description?: string;
  }): Promise<Receptor> {
    const res = await api.post<Receptor>('/receptors', data);
    return res.data;
  },
};
