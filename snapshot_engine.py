import sqlite3
import json
import hashlib
import os
import time
from dataclasses import dataclass, asdict

@dataclass
class Commit:
    hash: str
    parent_hash: str
    message: str
    author: str
    timestamp: float
    schema_snapshot: str
    data_snapshot: str

    def to_json(self):
        return json.dumps(asdict(self), indent=4)

    @classmethod
    def from_json(cls, json_str):
        data = json.loads(json_str)
        return cls(**data)

def extract_schema(db_path):
    """Connects to a SQLite database and extracts the full schema as DDL using sqlite_master."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # Get all tables, indexes, triggers, and views
    cursor.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name")
    schema = "\n".join([row[0] + ";" for row in cursor.fetchall()])
    conn.close()
    return schema

def get_primary_keys(cursor, table_name):
    """Returns a list of column names that make up the primary key for a given table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    # row[5] is the pk flag (1 if PK, 0 otherwise)
    pks = [row[1] for row in columns if row[5] > 0]
    return pks

def dump_data(db_path):
    """Dumps all table data from a SQLite database into a JSON dictionary keyed by primary key."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row['name'] for row in cursor.fetchall()]
    
    db_dump = {}
    for table in tables:
        pks = get_primary_keys(cursor, table)
        if not pks:
            print(f"Warning: Table '{table}' has no primary key. Skipping.")
            continue
            
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        
        table_data = {}
        for row in rows:
            row_dict = dict(row)
            # Use a single value if one PK, otherwise a tuple-like string
            if len(pks) == 1:
                key = str(row_dict[pks[0]])
            else:
                key = "|".join(str(row_dict[pk]) for pk in pks)
            
            table_data[key] = row_dict
        
        db_dump[table] = table_data
        
    conn.close()
    return db_dump

def generate_hash(schema_content, data_content, parent_hash):
    """Generates a SHA-256 hash from schema content, data content and a parent hash string."""
    data_str = json.dumps(data_content, sort_keys=True)
    combined = f"{schema_content}{data_str}{parent_hash}"
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()

def gitdb_init(repo_path):
    """Creates a .gitdb metadata directory for a given SQLite database path."""
    # Ensure repo_path is absolute
    repo_path = os.path.abspath(repo_path)
    gitdb_dir = os.path.join(os.path.dirname(repo_path), ".gitdb")
    commits_dir = os.path.join(gitdb_dir, "commits")
    
    if not os.path.exists(gitdb_dir):
        os.makedirs(gitdb_dir)
    if not os.path.exists(commits_dir):
        os.makedirs(commits_dir)
        
    # Initialize HEAD if it doesn't exist
    head_path = os.path.join(gitdb_dir, "HEAD")
    if not os.path.exists(head_path):
        with open(head_path, "w") as f:
            f.write("") # Empty HEAD initially
            
    return gitdb_dir

def save_commit(commit, repo_path):
    """Saves a Commit object to a JSON file in a .gitdb directory and updates the HEAD pointer."""
    repo_path = os.path.abspath(repo_path)
    gitdb_dir = os.path.join(os.path.dirname(repo_path), ".gitdb")
    commits_dir = os.path.join(gitdb_dir, "commits")
    
    if not os.path.exists(commits_dir):
        os.makedirs(commits_dir)
        
    commit_file = os.path.join(commits_dir, f"{commit.hash}.json")
    
    with open(commit_file, "w") as f:
        f.write(commit.to_json())
        
    head_path = os.path.join(gitdb_dir, "HEAD")
    with open(head_path, "w") as f:
        f.write(commit.hash)

def load_commit(repo_path):
    """Reads the current HEAD commit from .gitdb and loads the full commit object from the commit store."""
    repo_path = os.path.abspath(repo_path)
    gitdb_dir = os.path.join(os.path.dirname(repo_path), ".gitdb")
    head_path = os.path.join(gitdb_dir, "HEAD")
    
    if not os.path.exists(head_path):
        return None
        
    with open(head_path, "r") as f:
        commit_hash = f.read().strip()
        
    if not commit_hash:
        return None
        
    commit_file = os.path.join(gitdb_dir, "commits", f"{commit_hash}.json")
    if not os.path.exists(commit_file):
        return None
        
    with open(commit_file, "r") as f:
        return Commit.from_json(f.read())
