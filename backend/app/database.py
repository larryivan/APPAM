import sqlite3
import os

DATABASE_FILE = 'app_database.db'
DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    creator TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    password_hash TEXT,
    has_password BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS process_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
);
'''

def get_db_connection():
    """Creates a database connection."""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with schema."""
    if not os.path.exists(DATABASE_FILE):
        print("Creating database...")
    else:
        print("Database already exists, running migrations...")
        
    conn = get_db_connection()
    conn.executescript(DB_SCHEMA)
    conn.close()
    migrate_db()

def migrate_db():
    """Run database migrations to update existing schema."""
    conn = get_db_connection()
    
    # Check if description column exists
    cursor = conn.execute("PRAGMA table_info(projects)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'description' not in columns:
        print("Adding description column...")
        conn.execute("ALTER TABLE projects ADD COLUMN description TEXT")
    
    if 'creator' not in columns:
        print("Adding creator column...")
        conn.execute("ALTER TABLE projects ADD COLUMN creator TEXT")
    
    if 'created_at' not in columns:
        print("Adding created_at column...")
        conn.execute("ALTER TABLE projects ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    if 'last_accessed' not in columns:
        print("Adding last_accessed column...")
        conn.execute("ALTER TABLE projects ADD COLUMN last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    # Add password-related columns
    if 'password_hash' not in columns:
        print("Adding password_hash column...")
        conn.execute("ALTER TABLE projects ADD COLUMN password_hash TEXT")
    
    if 'has_password' not in columns:
        print("Adding has_password column...")
        conn.execute("ALTER TABLE projects ADD COLUMN has_password BOOLEAN DEFAULT FALSE")
    
    # Check if process_history table exists
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='process_history'")
    if not cursor.fetchone():
        print("Creating process_history table...")
        conn.execute('''
        CREATE TABLE process_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )''')
    
    conn.commit()
    conn.close()
