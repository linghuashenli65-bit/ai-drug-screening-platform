import api from './api';
import type { ProjectItem } from '../types';

export const projectService = {
  async list(params?: { page?: number; page_size?: number }): Promise<ProjectItem[]> {
    const res = await api.get<ProjectItem[]>('/projects', { params });
    return res.data;
  },

  async create(data: { project_name: string; description?: string }): Promise<ProjectItem> {
    const res = await api.post<ProjectItem>('/projects', data);
    return res.data;
  },

  async get(projectId: number): Promise<ProjectItem> {
    const res = await api.get<ProjectItem>(`/projects/${projectId}`);
    return res.data;
  },
};
