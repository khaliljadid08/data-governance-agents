PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operateur TEXT NOT NULL,
    consigne TEXT NOT NULL,
    perimetre TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_attente'
        CHECK (statut IN ('en_attente', 'en_cours', 'a_valider', 'valide', 'rejete')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER NOT NULL,
    numero_iteration INTEGER NOT NULL CHECK (numero_iteration > 0),
    statut TEXT NOT NULL DEFAULT 'en_cours'
        CHECK (statut IN ('en_cours', 'a_valider', 'valide', 'rejete', 'echec')),
    started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT,
    UNIQUE (request_id, numero_iteration),
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS agent_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    agent TEXT NOT NULL
        CHECK (agent IN ('qualite', 'classification', 'securisation', 'lignage', 'documentation')),
    statut TEXT NOT NULL CHECK (statut IN ('succes', 'echec')),
    resume TEXT,
    details_json TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS quality_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT,
    type_anomalie TEXT NOT NULL
        CHECK (type_anomalie IN ('valeur_manquante', 'doublon', 'incoherence', 'regle_metier')),
    severite TEXT NOT NULL CHECK (severite IN ('faible', 'moyenne', 'elevee', 'critique')),
    nb_lignes INTEGER NOT NULL DEFAULT 0 CHECK (nb_lignes >= 0),
    exemple TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    categorie TEXT NOT NULL,
    confiance REAL CHECK (confiance >= 0.0 AND confiance <= 1.0),
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS security_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    niveau_sensibilite TEXT NOT NULL
        CHECK (niveau_sensibilite IN ('public', 'interne', 'confidentiel', 'sensible')),
    type_donnee TEXT NOT NULL,
    conforme_regle_acces INTEGER NOT NULL CHECK (conforme_regle_acces IN (0, 1)),
    recommandation TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS lineage_edges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    source_table TEXT NOT NULL,
    source_column TEXT,
    target_table TEXT NOT NULL,
    target_column TEXT,
    type_relation TEXT NOT NULL CHECK (type_relation IN ('fk', 'transformation', 'derive')),
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS data_dictionary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    column_name TEXT NOT NULL,
    description TEXT,
    type_sql TEXT,
    categorie TEXT,
    sensibilite TEXT,
    derniere_maj TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    run_id INTEGER,
    UNIQUE (table_name, column_name),
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS validations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    reviewer TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('data_steward', 'data_owner')),
    decision TEXT NOT NULL CHECK (decision IN ('valide', 'rejete')),
    commentaire TEXT,
    decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    acteur TEXT NOT NULL,
    action TEXT NOT NULL,
    entite TEXT NOT NULL,
    entite_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_runs_request_id ON runs(request_id);
CREATE INDEX IF NOT EXISTS idx_agent_results_run_id ON agent_results(run_id);
CREATE INDEX IF NOT EXISTS idx_quality_issues_run_id ON quality_issues(run_id);
CREATE INDEX IF NOT EXISTS idx_classifications_run_id ON classifications(run_id);
CREATE INDEX IF NOT EXISTS idx_security_findings_run_id ON security_findings(run_id);
CREATE INDEX IF NOT EXISTS idx_lineage_edges_run_id ON lineage_edges(run_id);
CREATE INDEX IF NOT EXISTS idx_data_dictionary_run_id ON data_dictionary(run_id);
CREATE INDEX IF NOT EXISTS idx_validations_run_id ON validations(run_id);
