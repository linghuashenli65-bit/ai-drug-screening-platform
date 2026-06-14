-- MySQL init script — creates all tables for AI Drug Screening Platform
-- Executed automatically on first container startup
-- Synced with SQLAlchemy models as of 2026-06-13

USE drug_screening;

-- Users
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(128) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'RESEARCHER',
    status SMALLINT NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username),
    INDEX idx_email (email),
    INDEX idx_role (role)
);

-- Projects
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT NOT NULL,
    project_name VARCHAR(128) NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_owner (owner_id)
);

-- Project members
CREATE TABLE IF NOT EXISTS project_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    user_id INT NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'RESEARCHER',
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_project_user (project_id, user_id),
    INDEX idx_project (project_id),
    INDEX idx_user (user_id)
);

-- Receptors (target proteins)
CREATE TABLE IF NOT EXISTS receptors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    receptor_name VARCHAR(128) NOT NULL,
    pdb_code VARCHAR(32),
    pdbqt_uri VARCHAR(512),
    description TEXT,
    INDEX idx_pdb_code (pdb_code)
);

-- Molecules
CREATE TABLE IF NOT EXISTS molecules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    smiles TEXT NOT NULL,
    molecular_weight NUMERIC(10,3),
    logp NUMERIC(6,2),
    tpsa NUMERIC(6,2),
    source_file_uri VARCHAR(512),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    INDEX idx_project (project_id)
);

-- Molecule files (one molecule can have multiple SDF/PDBQT files)
CREATE TABLE IF NOT EXISTS molecule_files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    molecule_id INT NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    file_uri VARCHAR(512) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE,
    INDEX idx_molecule (molecule_id)
);

-- Drug library (pre-loaded drugs)
CREATE TABLE IF NOT EXISTS drug_library (
    id INT AUTO_INCREMENT PRIMARY KEY,
    drug_name VARCHAR(255) NOT NULL,
    smiles TEXT NOT NULL,
    drugbank_id VARCHAR(64),
    cas VARCHAR(64),
    indication TEXT,
    molecular_weight NUMERIC(10,3),
    logp NUMERIC(6,2),
    milvus_vector_id INT,
    pdbqt_uri VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT '正常',
    INDEX idx_drug_name (drug_name),
    INDEX idx_drugbank_id (drugbank_id),
    INDEX idx_cas (cas)
);

-- Screening jobs
CREATE TABLE IF NOT EXISTS screening_jobs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    molecule_id INT DEFAULT NULL,
    receptor_id INT NOT NULL,
    job_name VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'CREATED',
    progress INT NOT NULL DEFAULT 0,
    total_drugs INT NOT NULL DEFAULT 0,
    finished_drugs INT NOT NULL DEFAULT 0,
    created_by INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (molecule_id) REFERENCES molecules(id) ON DELETE CASCADE,
    FOREIGN KEY (receptor_id) REFERENCES receptors(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_project (project_id),
    INDEX idx_molecule (molecule_id),
    INDEX idx_receptor (receptor_id),
    INDEX idx_status (status),
    INDEX idx_created_by (created_by)
);

-- Docking tasks (per drug)
CREATE TABLE IF NOT EXISTS docking_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    drug_id INT NOT NULL,
    affinity_score NUMERIC(8,3),
    docking_result_uri VARCHAR(512),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    retry_count INT NOT NULL DEFAULT 0,
    started_at DATETIME,
    finished_at DATETIME,
    FOREIGN KEY (job_id) REFERENCES screening_jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (drug_id) REFERENCES drug_library(id) ON DELETE CASCADE,
    INDEX idx_job (job_id),
    INDEX idx_drug (drug_id),
    INDEX idx_status (status)
);

-- Interaction analyses (PLIP)
CREATE TABLE IF NOT EXISTS interaction_analyses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    drug_id INT NOT NULL,
    hydrogen_bonds INT NOT NULL DEFAULT 0,
    hydrophobic_contacts INT NOT NULL DEFAULT 0,
    salt_bridges INT NOT NULL DEFAULT 0,
    pi_interactions INT NOT NULL DEFAULT 0,
    analysis_json JSON,
    FOREIGN KEY (job_id) REFERENCES screening_jobs(id) ON DELETE CASCADE,
    INDEX idx_job (job_id)
);

-- AI analysis results
CREATE TABLE IF NOT EXISTS ai_analysis_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    drug_id INT NOT NULL,
    llm_model VARCHAR(64) NOT NULL,
    summary TEXT,
    recommendation TEXT,
    risk_analysis TEXT,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES screening_jobs(id) ON DELETE CASCADE,
    INDEX idx_job (job_id)
);

-- Reports
CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    report_type VARCHAR(32) NOT NULL,
    report_uri VARCHAR(512) NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES screening_jobs(id) ON DELETE CASCADE,
    INDEX idx_job (job_id)
);

-- Agent runs (LangGraph)
CREATE TABLE IF NOT EXISTS agent_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    agent_name VARCHAR(128) NOT NULL,
    state_before VARCHAR(64),
    state_after VARCHAR(64),
    input_json JSON,
    output_json JSON,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    started_at DATETIME,
    finished_at DATETIME,
    FOREIGN KEY (job_id) REFERENCES screening_jobs(id) ON DELETE CASCADE,
    INDEX idx_job (job_id)
);

-- Tool calls (agent observability)
CREATE TABLE IF NOT EXISTS tool_calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    agent_run_id INT NOT NULL,
    tool_name VARCHAR(128) NOT NULL,
    input_json JSON,
    output_json JSON,
    duration_ms INT NOT NULL DEFAULT 0,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    FOREIGN KEY (agent_run_id) REFERENCES agent_runs(id) ON DELETE CASCADE,
    INDEX idx_agent_run (agent_run_id)
);

-- Audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action VARCHAR(128) NOT NULL,
    resource_type VARCHAR(64),
    resource_id INT,
    ip_address VARCHAR(64),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user (user_id),
    INDEX idx_action (action),
    INDEX idx_created (created_at)
);
