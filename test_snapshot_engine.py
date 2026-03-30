import sqlite3
import os
import json
from snapshot_engine import (
    Commit, extract_schema, dump_data, generate_hash, 
    gitdb_init, save_commit, load_commit
)

def test_snapshot_engine():
    db_path = "test.db"
    
    # 1. Create a sample SQLite database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    cursor.execute("INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')")
    cursor.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
    
    cursor.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT, author_id INTEGER, FOREIGN KEY(author_id) REFERENCES users(id))")
    cursor.execute("INSERT INTO posts (title, author_id) VALUES ('Hello World', 1)")
    
    conn.commit()
    conn.close()
    
    print("Created test database.")
    
    # 2. Initialize GitDB
    repo_path = os.path.abspath(db_path)
    gitdb_dir = gitdb_init(repo_path)
    print(f"Initialized GitDB at {gitdb_dir}")
    
    # 3. Extract schema and dump data
    schema = extract_schema(db_path)
    print("Extracted schema:")
    print(schema)
    
    data = dump_data(db_path)
    print("Dumped data:")
    print(json.dumps(data, indent=2))
    
    # 4. Create a commit
    parent_hash = "" # First commit
    commit_hash = generate_hash(schema, data, parent_hash)
    
    commit = Commit(
        hash=commit_hash,
        parent_hash=parent_hash,
        message="Initial commit",
        author="Test Author",
        timestamp=123456789.0, # Example timestamp
        schema_snapshot=schema,
        data_snapshot=json.dumps(data)
    )
    
    # 5. Save the commit
    save_commit(commit, db_path)
    print(f"Saved commit: {commit.hash}")
    
    # 6. Load the commit and verify
    loaded_commit = load_commit(db_path)
    if loaded_commit:
        print(f"Loaded commit: {loaded_commit.hash}")
        print(f"Message: {loaded_commit.message}")
        print(f"Author: {loaded_commit.author}")
        
        # Verify data
        loaded_data = json.loads(loaded_commit.data_snapshot)
        assert loaded_data == data
        assert loaded_commit.schema_snapshot == schema
        print("Verification successful!")
    else:
        print("Failed to load commit!")

if __name__ == "__main__":
    test_snapshot_engine()
