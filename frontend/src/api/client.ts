import axios from 'axios';

// In production the API and SPA are served from the SAME origin,
// so a relative '/api' base works for both dev (Vite proxy) and prod.
export const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// ---------- Types matching backend schemas ----------

export type Material =
  | 'concrete' | 'brick' | 'glass' | 'wood' | 'drywall' | 'metal' | 'door';

export interface Project {
  id: string;
  name: string;
  building_type: string | null;
  image_path: string | null;
  scale_px_per_m: number | null;
  building_w_m: number | null;
  building_h_m: number | null;
  ceiling_h_m: number;
  created_at: string;
  updated_at: string;
}

export interface Wall {
  id: string;
  p1_x: number; p1_y: number;
  p2_x: number; p2_y: number;
  material: Material;
  height: number;
}

export interface AP {
  id: string;
  name: string;
  x: number; y: number; z: number;
}

export interface HeatmapData {
  mode: string;
  bounds: [number, number, number, number];
  resolution: number;
  grid: number[][];
  covered_pct: number;
  avg_rssi: number;
  min_rssi: number;
}

// ---------- Endpoints ----------

export const Projects = {
  list: () => api.get<Project[]>('/projects').then(r => r.data),
  create: (name: string, building_type?: string) =>
    api.post<Project>('/projects', { name, building_type }).then(r => r.data),
  get: (id: string) => api.get<Project>(`/projects/${id}`).then(r => r.data),
  remove: (id: string) => api.delete(`/projects/${id}`),
  upload: (id: string, file: File) => {
    const fd = new FormData();
    fd.append('file', file);
    return api.post<Project>(`/projects/${id}/upload`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },
};

export const Walls = {
  list: (pid: string) => api.get<Wall[]>(`/projects/${pid}/walls`).then(r => r.data),
  detect: (pid: string) =>
    api.post<Wall[]>(`/projects/${pid}/walls/detect`).then(r => r.data),
  replace: (pid: string, walls: Omit<Wall, 'id'>[]) =>
    api.put<Wall[]>(`/projects/${pid}/walls`, { walls }).then(r => r.data),
};

export const Optimize = {
  start: (pid: string, params: {
    algorithm?: 'ga' | 'grid';
    target_coverage?: number;
    num_aps?: number;
    sqm_per_ap?: number;
  }) => api.post<{ task_id: string; ws_url: string }>(
    `/projects/${pid}/optimize`, params,
  ).then(r => r.data),
  listAPs: (pid: string) =>
    api.get<AP[]>(`/projects/${pid}/aps`).then(r => r.data),
};

export const Heatmap = {
  get: (pid: string, mode: string = 'signal_strength', resolution = 80) =>
    api.get<HeatmapData>(`/projects/${pid}/heatmap`, {
      params: { mode, resolution },
    }).then(r => r.data),
};

export const Report = {
  url: (pid: string) => `/api/projects/${pid}/report.pdf`,
};
