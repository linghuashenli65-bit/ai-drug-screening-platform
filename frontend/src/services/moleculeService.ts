import api from './api';

export interface MoleculeItem {
  id: number;
  project_id: number;
  smiles: string;
  molecular_weight?: number;
  logp?: number;
  tpsa?: number;
  source_file_uri?: string;
  created_at?: string;
}

export const moleculeService = {
  async upload(data: { project_id: number; smiles: string }): Promise<MoleculeItem> {
    const res = await api.post<MoleculeItem>('/molecules/upload', data);
    return res.data;
  },

  async list(params?: { project_id?: number; page?: number; page_size?: number }): Promise<MoleculeItem[]> {
    const res = await api.get<MoleculeItem[]>('/molecules', { params });
    return res.data;
  },

  async get(moleculeId: number): Promise<MoleculeItem> {
    const res = await api.get<MoleculeItem>(`/molecules/${moleculeId}`);
    return res.data;
  },
};
