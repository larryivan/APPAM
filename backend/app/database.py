from __future__ import annotations

import os
import sqlite3


DATABASE_FILE = os.getenv('APPAM_DB_PATH', 'app_database.db')

DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    creator TEXT,
    owner_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS project_members (
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'viewer',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS auth_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    username TEXT,
    event_type TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0,
    ip_address TEXT,
    user_agent TEXT,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS process_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT UNIQUE,
    project_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    command TEXT,
    status TEXT NOT NULL,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    duration REAL,
    exit_code INTEGER,
    error_message TEXT,
    logs TEXT,
    submitted_by TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    command TEXT NOT NULL,
    command_spec_json TEXT,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    claimed_at TIMESTAMP,
    claimed_by TEXT,
    heartbeat_at TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration REAL,
    exit_code INTEGER,
    error_message TEXT,
    log_path TEXT,
    output_path TEXT,
    work_dir TEXT,
    pid INTEGER,
    pgid INTEGER,
    host TEXT,
    cancel_requested INTEGER DEFAULT 0,
    submitted_by TEXT,
    execution_mode TEXT NOT NULL DEFAULT 'command',
    backend TEXT NOT NULL DEFAULT 'local',
    workflow_id TEXT,
    workflow_run_id TEXT,
    is_dry_run INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    job_id TEXT UNIQUE,
    project_id TEXT NOT NULL,
    workflow_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    status TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 0,
    backend TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration REAL,
    exit_code INTEGER,
    error_message TEXT,
    submitted_by TEXT,
    parent_run_id TEXT,
    preflight_id TEXT,
    params_json TEXT,
    config_path TEXT,
    manifest_path TEXT,
    run_dir TEXT,
    work_dir TEXT,
    results_dir TEXT,
    output_root TEXT,
    log_path TEXT,
    current_stage_id TEXT,
    current_stage_title TEXT,
    current_rule TEXT,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL,
    FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE SET NULL,
    FOREIGN KEY (parent_run_id) REFERENCES workflow_runs (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workflow_preflights (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    workflow_id TEXT,
    tool_name TEXT NOT NULL,
    ok INTEGER NOT NULL DEFAULT 0,
    params_hash TEXT,
    checks_json TEXT,
    preview_json TEXT,
    submitted_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
    FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS workflow_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    metric_group TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_text TEXT,
    unit TEXT,
    sample_id TEXT,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workflow_stage_states (
    run_id TEXT NOT NULL,
    stage_id TEXT NOT NULL,
    stage_title TEXT NOT NULL,
    stage_order INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    optional INTEGER NOT NULL DEFAULT 0,
    current_rule TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    completed_rules INTEGER NOT NULL DEFAULT 0,
    total_rules INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (run_id, stage_id),
    FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workflow_run_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    stage_id TEXT,
    rule_name TEXT,
    message TEXT,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS workflow_artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    label TEXT NOT NULL,
    path TEXT NOT NULL,
    kind TEXT NOT NULL,
    size_bytes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members (user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_username_created_at ON auth_audit_log (username, created_at);
CREATE INDEX IF NOT EXISTS idx_auth_audit_ip_created_at ON auth_audit_log (ip_address, created_at);
CREATE INDEX IF NOT EXISTS idx_jobs_project_created_at ON jobs (project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_process_history_project_start_time ON process_history (project_id, start_time);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_project_created_at ON workflow_runs (project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_project_status ON workflow_runs (project_id, workflow_id, status);
CREATE INDEX IF NOT EXISTS idx_workflow_preflights_project_created_at ON workflow_preflights (project_id, created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_metrics_run_group ON workflow_metrics (run_id, metric_group);
CREATE INDEX IF NOT EXISTS idx_workflow_stage_states_run_order ON workflow_stage_states (run_id, stage_order);
CREATE INDEX IF NOT EXISTS idx_workflow_run_events_run_created_at ON workflow_run_events (run_id, created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_artifacts_run_created_at ON workflow_artifacts (run_id, created_at);
'''


def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(DATABASE_FILE, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,)
    ).fetchone()
    return bool(row)


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    if not table_exists(conn, table_name):
        return False
    columns = [column[1] for column in conn.execute(f"PRAGMA table_info({table_name})").fetchall()]
    return column_name in columns


def init_db():
    """Initialize the database with schema."""
    db_dir = os.path.dirname(os.path.abspath(DATABASE_FILE))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    if not os.path.exists(DATABASE_FILE):
        print("Creating database...")
    else:
        print("Database already exists, running migrations...")

    conn = get_db_connection()
    try:
        conn.executescript(DB_SCHEMA)
        migrate_db(conn)
        conn.commit()
    finally:
        conn.close()


def migrate_db(conn: sqlite3.Connection | None = None):
    """Run database migrations to update existing schema."""
    owns_connection = conn is None
    connection = conn or get_db_connection()

    try:
        _migrate_users_table(connection)
        _migrate_projects_table(connection)
        _migrate_project_members_table(connection)
        _migrate_auth_audit_table(connection)
        _migrate_process_history_table(connection)
        _migrate_jobs_table(connection)
        _migrate_workflow_runs_table(connection)
        _migrate_workflow_preflights_table(connection)
        _migrate_workflow_metrics_table(connection)
        _migrate_workflow_stage_states_table(connection)
        _migrate_workflow_run_events_table(connection)
        _migrate_workflow_artifacts_table(connection)
        _backfill_owner_memberships(connection)
        _backfill_process_history_submitters(connection)
        connection.commit()
    finally:
        if owns_connection:
            connection.close()


def _migrate_users_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'users'):
        conn.execute(
            '''
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
            '''
        )
        return

    if not column_exists(conn, 'users', 'display_name'):
        conn.execute("ALTER TABLE users ADD COLUMN display_name TEXT")
    if not column_exists(conn, 'users', 'role'):
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    if not column_exists(conn, 'users', 'status'):
        conn.execute("ALTER TABLE users ADD COLUMN status TEXT NOT NULL DEFAULT 'active'")
    if not column_exists(conn, 'users', 'last_login_at'):
        conn.execute("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP")


def _migrate_projects_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'projects'):
        conn.execute(
            '''
            CREATE TABLE projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                creator TEXT,
                owner_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES users (id) ON DELETE SET NULL
            )
            '''
        )
        return

    if not column_exists(conn, 'projects', 'description'):
        conn.execute("ALTER TABLE projects ADD COLUMN description TEXT")
    if not column_exists(conn, 'projects', 'creator'):
        conn.execute("ALTER TABLE projects ADD COLUMN creator TEXT")
    if not column_exists(conn, 'projects', 'created_at'):
        conn.execute("ALTER TABLE projects ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    if not column_exists(conn, 'projects', 'last_accessed'):
        conn.execute("ALTER TABLE projects ADD COLUMN last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    if not column_exists(conn, 'projects', 'owner_id'):
        conn.execute("ALTER TABLE projects ADD COLUMN owner_id TEXT")


def _migrate_project_members_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'project_members'):
        conn.execute(
            '''
            CREATE TABLE project_members (
                project_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                PRIMARY KEY (project_id, user_id),
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE SET NULL
            )
            '''
        )
    else:
        if not column_exists(conn, 'project_members', 'created_at'):
            conn.execute("ALTER TABLE project_members ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        if not column_exists(conn, 'project_members', 'created_by'):
            conn.execute("ALTER TABLE project_members ADD COLUMN created_by TEXT")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_project_members_user ON project_members (user_id)")


def _migrate_auth_audit_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'auth_audit_log'):
        conn.execute(
            '''
            CREATE TABLE auth_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                event_type TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 0,
                ip_address TEXT,
                user_agent TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('user_id', "ALTER TABLE auth_audit_log ADD COLUMN user_id TEXT"),
            ('username', "ALTER TABLE auth_audit_log ADD COLUMN username TEXT"),
            ('event_type', "ALTER TABLE auth_audit_log ADD COLUMN event_type TEXT NOT NULL DEFAULT 'unknown'"),
            ('success', "ALTER TABLE auth_audit_log ADD COLUMN success INTEGER NOT NULL DEFAULT 0"),
            ('ip_address', "ALTER TABLE auth_audit_log ADD COLUMN ip_address TEXT"),
            ('user_agent', "ALTER TABLE auth_audit_log ADD COLUMN user_agent TEXT"),
            ('details', "ALTER TABLE auth_audit_log ADD COLUMN details TEXT"),
            ('created_at', "ALTER TABLE auth_audit_log ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ):
            if not column_exists(conn, 'auth_audit_log', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_username_created_at ON auth_audit_log (username, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_audit_ip_created_at ON auth_audit_log (ip_address, created_at)")


def _migrate_process_history_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'process_history'):
        conn.execute(
            '''
            CREATE TABLE process_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT UNIQUE,
                project_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                command TEXT,
                status TEXT NOT NULL,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                exit_code INTEGER,
                error_message TEXT,
                logs TEXT,
                submitted_by TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('job_id', "ALTER TABLE process_history ADD COLUMN job_id TEXT"),
            ('command', "ALTER TABLE process_history ADD COLUMN command TEXT"),
            ('logs', "ALTER TABLE process_history ADD COLUMN logs TEXT"),
            ('submitted_by', "ALTER TABLE process_history ADD COLUMN submitted_by TEXT"),
        ):
            if not column_exists(conn, 'process_history', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_process_history_project_start_time ON process_history (project_id, start_time)")


def _migrate_jobs_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'jobs'):
        conn.execute(
            '''
            CREATE TABLE jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                command TEXT NOT NULL,
                command_spec_json TEXT,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                claimed_at TIMESTAMP,
                claimed_by TEXT,
                heartbeat_at TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                duration REAL,
                exit_code INTEGER,
                error_message TEXT,
                log_path TEXT,
                output_path TEXT,
                work_dir TEXT,
                pid INTEGER,
                pgid INTEGER,
                host TEXT,
                cancel_requested INTEGER DEFAULT 0,
                submitted_by TEXT,
                execution_mode TEXT NOT NULL DEFAULT 'command',
                backend TEXT NOT NULL DEFAULT 'local',
                workflow_id TEXT,
                workflow_run_id TEXT,
                is_dry_run INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL
            )
            '''
        )
        return

    for column_name, column_sql in (
        ('command_spec_json', "ALTER TABLE jobs ADD COLUMN command_spec_json TEXT"),
        ('log_path', "ALTER TABLE jobs ADD COLUMN log_path TEXT"),
        ('output_path', "ALTER TABLE jobs ADD COLUMN output_path TEXT"),
        ('work_dir', "ALTER TABLE jobs ADD COLUMN work_dir TEXT"),
        ('claimed_at', "ALTER TABLE jobs ADD COLUMN claimed_at TIMESTAMP"),
        ('claimed_by', "ALTER TABLE jobs ADD COLUMN claimed_by TEXT"),
        ('heartbeat_at', "ALTER TABLE jobs ADD COLUMN heartbeat_at TIMESTAMP"),
        ('pid', "ALTER TABLE jobs ADD COLUMN pid INTEGER"),
        ('pgid', "ALTER TABLE jobs ADD COLUMN pgid INTEGER"),
        ('host', "ALTER TABLE jobs ADD COLUMN host TEXT"),
        ('cancel_requested', "ALTER TABLE jobs ADD COLUMN cancel_requested INTEGER DEFAULT 0"),
        ('submitted_by', "ALTER TABLE jobs ADD COLUMN submitted_by TEXT"),
        ('execution_mode', "ALTER TABLE jobs ADD COLUMN execution_mode TEXT NOT NULL DEFAULT 'command'"),
        ('backend', "ALTER TABLE jobs ADD COLUMN backend TEXT NOT NULL DEFAULT 'local'"),
        ('workflow_id', "ALTER TABLE jobs ADD COLUMN workflow_id TEXT"),
        ('workflow_run_id', "ALTER TABLE jobs ADD COLUMN workflow_run_id TEXT"),
        ('is_dry_run', "ALTER TABLE jobs ADD COLUMN is_dry_run INTEGER NOT NULL DEFAULT 0"),
    ):
        if not column_exists(conn, 'jobs', column_name):
            conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_project_created_at ON jobs (project_id, created_at)")


def _migrate_workflow_runs_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'workflow_runs'):
        conn.execute(
            '''
            CREATE TABLE workflow_runs (
                id TEXT PRIMARY KEY,
                job_id TEXT UNIQUE,
                project_id TEXT NOT NULL,
                workflow_id TEXT NOT NULL,
                tool_name TEXT NOT NULL,
                status TEXT NOT NULL,
                dry_run INTEGER NOT NULL DEFAULT 0,
                backend TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                duration REAL,
                exit_code INTEGER,
                error_message TEXT,
                submitted_by TEXT,
                preflight_id TEXT,
                config_path TEXT,
                run_dir TEXT,
                work_dir TEXT,
                results_dir TEXT,
                output_root TEXT,
                log_path TEXT,
                current_stage_id TEXT,
                current_stage_title TEXT,
                current_rule TEXT,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL,
                FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE SET NULL
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('job_id', "ALTER TABLE workflow_runs ADD COLUMN job_id TEXT"),
            ('project_id', "ALTER TABLE workflow_runs ADD COLUMN project_id TEXT"),
            ('workflow_id', "ALTER TABLE workflow_runs ADD COLUMN workflow_id TEXT"),
            ('tool_name', "ALTER TABLE workflow_runs ADD COLUMN tool_name TEXT"),
            ('status', "ALTER TABLE workflow_runs ADD COLUMN status TEXT"),
            ('dry_run', "ALTER TABLE workflow_runs ADD COLUMN dry_run INTEGER NOT NULL DEFAULT 0"),
            ('backend', "ALTER TABLE workflow_runs ADD COLUMN backend TEXT"),
            ('created_at', "ALTER TABLE workflow_runs ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
            ('started_at', "ALTER TABLE workflow_runs ADD COLUMN started_at TIMESTAMP"),
            ('finished_at', "ALTER TABLE workflow_runs ADD COLUMN finished_at TIMESTAMP"),
            ('duration', "ALTER TABLE workflow_runs ADD COLUMN duration REAL"),
            ('exit_code', "ALTER TABLE workflow_runs ADD COLUMN exit_code INTEGER"),
            ('error_message', "ALTER TABLE workflow_runs ADD COLUMN error_message TEXT"),
            ('submitted_by', "ALTER TABLE workflow_runs ADD COLUMN submitted_by TEXT"),
            ('parent_run_id', "ALTER TABLE workflow_runs ADD COLUMN parent_run_id TEXT"),
            ('preflight_id', "ALTER TABLE workflow_runs ADD COLUMN preflight_id TEXT"),
            ('params_json', "ALTER TABLE workflow_runs ADD COLUMN params_json TEXT"),
            ('config_path', "ALTER TABLE workflow_runs ADD COLUMN config_path TEXT"),
            ('manifest_path', "ALTER TABLE workflow_runs ADD COLUMN manifest_path TEXT"),
            ('run_dir', "ALTER TABLE workflow_runs ADD COLUMN run_dir TEXT"),
            ('work_dir', "ALTER TABLE workflow_runs ADD COLUMN work_dir TEXT"),
            ('results_dir', "ALTER TABLE workflow_runs ADD COLUMN results_dir TEXT"),
            ('output_root', "ALTER TABLE workflow_runs ADD COLUMN output_root TEXT"),
            ('log_path', "ALTER TABLE workflow_runs ADD COLUMN log_path TEXT"),
            ('current_stage_id', "ALTER TABLE workflow_runs ADD COLUMN current_stage_id TEXT"),
            ('current_stage_title', "ALTER TABLE workflow_runs ADD COLUMN current_stage_title TEXT"),
            ('current_rule', "ALTER TABLE workflow_runs ADD COLUMN current_rule TEXT"),
        ):
            if not column_exists(conn, 'workflow_runs', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_runs_project_created_at ON workflow_runs (project_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_runs_project_status ON workflow_runs (project_id, workflow_id, status)")


def _migrate_workflow_preflights_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'workflow_preflights'):
        conn.execute(
            '''
            CREATE TABLE workflow_preflights (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                workflow_id TEXT,
                tool_name TEXT NOT NULL,
                ok INTEGER NOT NULL DEFAULT 0,
                params_hash TEXT,
                checks_json TEXT,
                preview_json TEXT,
                submitted_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                FOREIGN KEY (submitted_by) REFERENCES users (id) ON DELETE SET NULL
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('workflow_id', "ALTER TABLE workflow_preflights ADD COLUMN workflow_id TEXT"),
            ('tool_name', "ALTER TABLE workflow_preflights ADD COLUMN tool_name TEXT"),
            ('ok', "ALTER TABLE workflow_preflights ADD COLUMN ok INTEGER NOT NULL DEFAULT 0"),
            ('params_hash', "ALTER TABLE workflow_preflights ADD COLUMN params_hash TEXT"),
            ('checks_json', "ALTER TABLE workflow_preflights ADD COLUMN checks_json TEXT"),
            ('preview_json', "ALTER TABLE workflow_preflights ADD COLUMN preview_json TEXT"),
            ('submitted_by', "ALTER TABLE workflow_preflights ADD COLUMN submitted_by TEXT"),
            ('created_at', "ALTER TABLE workflow_preflights ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ):
            if not column_exists(conn, 'workflow_preflights', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_preflights_project_created_at ON workflow_preflights (project_id, created_at)")


def _migrate_workflow_metrics_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'workflow_metrics'):
        conn.execute(
            '''
            CREATE TABLE workflow_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                metric_group TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                metric_text TEXT,
                unit TEXT,
                sample_id TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('metric_group', "ALTER TABLE workflow_metrics ADD COLUMN metric_group TEXT NOT NULL DEFAULT 'general'"),
            ('metric_name', "ALTER TABLE workflow_metrics ADD COLUMN metric_name TEXT NOT NULL DEFAULT 'metric'"),
            ('metric_value', "ALTER TABLE workflow_metrics ADD COLUMN metric_value REAL"),
            ('metric_text', "ALTER TABLE workflow_metrics ADD COLUMN metric_text TEXT"),
            ('unit', "ALTER TABLE workflow_metrics ADD COLUMN unit TEXT"),
            ('sample_id', "ALTER TABLE workflow_metrics ADD COLUMN sample_id TEXT"),
            ('payload', "ALTER TABLE workflow_metrics ADD COLUMN payload TEXT"),
            ('created_at', "ALTER TABLE workflow_metrics ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ):
            if not column_exists(conn, 'workflow_metrics', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_metrics_run_group ON workflow_metrics (run_id, metric_group)")


def _migrate_workflow_stage_states_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'workflow_stage_states'):
        conn.execute(
            '''
            CREATE TABLE workflow_stage_states (
                run_id TEXT NOT NULL,
                stage_id TEXT NOT NULL,
                stage_title TEXT NOT NULL,
                stage_order INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                optional INTEGER NOT NULL DEFAULT 0,
                current_rule TEXT,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                completed_rules INTEGER NOT NULL DEFAULT 0,
                total_rules INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (run_id, stage_id),
                FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('stage_title', "ALTER TABLE workflow_stage_states ADD COLUMN stage_title TEXT"),
            ('stage_order', "ALTER TABLE workflow_stage_states ADD COLUMN stage_order INTEGER NOT NULL DEFAULT 0"),
            ('status', "ALTER TABLE workflow_stage_states ADD COLUMN status TEXT"),
            ('optional', "ALTER TABLE workflow_stage_states ADD COLUMN optional INTEGER NOT NULL DEFAULT 0"),
            ('current_rule', "ALTER TABLE workflow_stage_states ADD COLUMN current_rule TEXT"),
            ('started_at', "ALTER TABLE workflow_stage_states ADD COLUMN started_at TIMESTAMP"),
            ('finished_at', "ALTER TABLE workflow_stage_states ADD COLUMN finished_at TIMESTAMP"),
            ('completed_rules', "ALTER TABLE workflow_stage_states ADD COLUMN completed_rules INTEGER NOT NULL DEFAULT 0"),
            ('total_rules', "ALTER TABLE workflow_stage_states ADD COLUMN total_rules INTEGER NOT NULL DEFAULT 0"),
        ):
            if not column_exists(conn, 'workflow_stage_states', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_stage_states_run_order ON workflow_stage_states (run_id, stage_order)")


def _migrate_workflow_run_events_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'workflow_run_events'):
        conn.execute(
            '''
            CREATE TABLE workflow_run_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                stage_id TEXT,
                rule_name TEXT,
                message TEXT,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('stage_id', "ALTER TABLE workflow_run_events ADD COLUMN stage_id TEXT"),
            ('rule_name', "ALTER TABLE workflow_run_events ADD COLUMN rule_name TEXT"),
            ('message', "ALTER TABLE workflow_run_events ADD COLUMN message TEXT"),
            ('payload', "ALTER TABLE workflow_run_events ADD COLUMN payload TEXT"),
            ('created_at', "ALTER TABLE workflow_run_events ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ):
            if not column_exists(conn, 'workflow_run_events', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_run_events_run_created_at ON workflow_run_events (run_id, created_at)")


def _migrate_workflow_artifacts_table(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'workflow_artifacts'):
        conn.execute(
            '''
            CREATE TABLE workflow_artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                label TEXT NOT NULL,
                path TEXT NOT NULL,
                kind TEXT NOT NULL,
                size_bytes INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES workflow_runs (id) ON DELETE CASCADE
            )
            '''
        )
    else:
        for column_name, column_sql in (
            ('size_bytes', "ALTER TABLE workflow_artifacts ADD COLUMN size_bytes INTEGER"),
            ('created_at', "ALTER TABLE workflow_artifacts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ):
            if not column_exists(conn, 'workflow_artifacts', column_name):
                conn.execute(column_sql)

    conn.execute("CREATE INDEX IF NOT EXISTS idx_workflow_artifacts_run_created_at ON workflow_artifacts (run_id, created_at)")


def _backfill_owner_memberships(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        '''
        SELECT id, owner_id
        FROM projects
        WHERE owner_id IS NOT NULL AND owner_id != ''
        '''
    ).fetchall()

    for row in rows:
        conn.execute(
            '''
            INSERT INTO project_members (project_id, user_id, role, created_by)
            VALUES (?, ?, 'owner', ?)
            ON CONFLICT(project_id, user_id) DO UPDATE SET role = 'owner'
            ''',
            (row['id'], row['owner_id'], row['owner_id'])
        )


def _backfill_process_history_submitters(conn: sqlite3.Connection) -> None:
    if not table_exists(conn, 'process_history') or not table_exists(conn, 'jobs'):
        return

    if column_exists(conn, 'process_history', 'submitted_by') and column_exists(conn, 'process_history', 'job_id'):
        conn.execute(
            '''
            UPDATE process_history
            SET submitted_by = (
                SELECT jobs.submitted_by
                FROM jobs
                WHERE jobs.id = process_history.job_id
            )
            WHERE submitted_by IS NULL
              AND job_id IS NOT NULL
            '''
        )
