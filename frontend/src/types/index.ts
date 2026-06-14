// ==================== User & Auth Types ====================

export type UserRole = 'RESEARCHER' | 'PI' | 'ADMIN' | 'VIEWER';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  avatar?: string;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// ==================== Task / Job Types ====================

export type JobStatus =
  | 'CREATED'
  | 'PREPARING'
  | 'DOCKING'
  | 'ANALYZING'
  | 'REPORTING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'WAIT_HUMAN';

export type AgentNodeState =
  | 'PENDING'
  | 'RUNNING'
  | 'SUCCESS'
  | 'FAILED'
  | 'RETRYING';

export interface AgentNode {
  id: number | string;
  name: string;
  label: string;
  state: AgentNodeState;
  start_time?: string;
  end_time?: string;
  duration_ms?: number;
  error_message?: string;
  logs?: string[];
  retry_count: number;
}

export interface Job {
  // 后端字段
  id: number;
  job_name: string;
  project_id: number;
  molecule_id?: number;
  receptor_id: number;
  status: JobStatus;
  progress: number;
  total_drugs: number;
  finished_drugs: number;
  created_by: number;
  created_at?: string;
  // 前端兼容字段
  job_id: number;
  smiles?: string;
  drug_db?: string;
  exhaustiveness?: number;
  cpu_count?: number;
  top_n?: number;
  nodes?: AgentNode[];
  updated_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface ScreeningJobItem {
  id: number;
  job_name: string;
  project_id: number;
  molecule_id?: number;
  receptor_id: number;
  status: JobStatus;
  progress: number;
  total_drugs: number;
  finished_drugs: number;
  created_by: number;
  created_at?: string;
}

export interface CreateJobRequest {
  project_id: number | string;
  smiles?: string;
  receptor_id: number | string;
  job_name?: string;
  drug_db?: 'fda_approved' | 'drugbank' | 'custom';
  exhaustiveness?: number;
  cpu_count?: number;
  top_n?: number;
}

export interface CreateJobResponse {
  job_id: number;
  job_name: string;
  status: string;
  message?: string;
}

export interface JobListParams {
  page?: number;
  page_size?: number;
  status?: JobStatus;
  sort_by?: string;
  search?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

// ==================== Docking Result Types ====================

export interface DockingResult {
  id: string;
  job_id: string;
  drug_name: string;
  drug_id: string;
  smiles: string;
  docking_score: number;
  binding_energy?: number;
  rank: number;
  interactions?: Interaction[];
  ai_analysis?: string;
}

export interface Interaction {
  type: 'hydrogen_bond' | 'salt_bridge' | 'hydrophobic';
  residues: string[];
  distance?: number;
}

// ==================== Project Types ====================

export interface ProjectItem {
  id: number;
  project_name: string;
  description?: string;
  owner_id: number;
  created_at?: string;
}

// ==================== Protein Types ====================

export interface Protein {
  protein_id: string;
  name: string;
  description?: string;
  pdb_file_url?: string;
  binding_site?: BindingSite;
  created_at: string;
}

export interface Receptor {
  id: number;
  receptor_name: string;
  pdb_code?: string;
  pdbqt_uri?: string;
  description?: string;
}

export interface BindingSite {
  center: [number, number, number];
  size: [number, number, number];
  residues: string[];
}

// ==================== Report Types ====================

export interface Report {
  report_id: string;
  job_id: string;
  title: string;
  type: 'pdf' | 'markdown';
  file_url: string;
  file_size?: number;
  created_at: string;
}

// ==================== Drug Library Types ====================

export interface Drug {
  id: number;
  drug_name: string;
  smiles: string;
  drugbank_id?: string;
  cas?: string;
  status?: string;
  indication?: string;
  molecular_weight?: number;
  logp?: number;
  hbd?: number;
  hba?: number;
  pdbqt_uri?: string;
}

export interface DrugLibStats {
  total_drugs: number;
  fda_approved: number;
  drugbank: number;
  custom: number;
}

// ==================== AI Analysis Types ====================

export interface AIAnalysis {
  analysis_id: string;
  job_id: string;
  candidate_analysis?: string;
  drug_repurposing?: string;
  risk_analysis?: string;
  experiment_suggestions?: string;
  created_at: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

// ==================== System Types ====================

export interface SystemStatus {
  api_status: 'healthy' | 'degraded' | 'down';
  redis_status: 'healthy' | 'degraded' | 'down';
  db_status: 'healthy' | 'degraded' | 'down';
  worker_count: number;
  active_jobs: number;
  queue_depth: number;
}

export interface DashboardStats {
  total_jobs: number;
  running_jobs: number;
  completed_jobs: number;
  failed_jobs: number;
}

// ==================== API Error Types ====================

export interface ApiError {
  code: number;
  message: string;
  detail?: unknown;
}

// ==================== Upload File Types ====================

export type AllowedFileType = 'sdf' | 'pdb' | 'mol2' | 'csv';

export interface ParsedFile {
  type: AllowedFileType;
  molecule_count?: number;
  preview?: string;
  valid: boolean;
  error?: string;
}
