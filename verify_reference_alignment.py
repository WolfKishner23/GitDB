import os
import sqlite3
import subprocess
import json
import time

DB_PATH = "verify_align.db"
ENV_PATH = ".env.verify"

def run_gitdb(args):
    env = os.environ.copy()
    env["GITDB_DATABASE_PATH"] = DB_PATH
    result = subprocess.run(["python", "gitdb.py"] + args, env=env, capture_output=True, text=True)
    return result

def setup_db():
    if os.path.exists(DB_PATH): os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO users (id, name) VALUES (1, 'Alice');")
    conn.commit()
    conn.close()

def main():
    print("--- Setting up test environment ---")
    setup_db()
    
    # Clean old metadata
    if os.path.exists(".gitdb"):
        import shutil
        shutil.rmtree(".gitdb")

    print("\n1. Initializing GitDB...")
    run_gitdb(["init", DB_PATH])
    
    print("\n2. Initial Commit...")
    run_gitdb(["commit", "-m", "Initial commit"])
    
    print("\n3. Verifying 'status' on clean tree...")
    res = run_gitdb(["status"])
    print(res.stdout)
    if "nothing to commit, working tree clean" not in res.stdout:
        print("FAILED: Clean status not detected")
    
    print("\n4. Modifying database (adding table and row)...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT);")
    conn.execute("INSERT INTO users (id, name) VALUES (2, 'Bob');")
    conn.commit()
    conn.close()
    
    print("\n5. Verifying 'status' detects uncommitted changes...")
    res = run_gitdb(["status"])
    print(res.stdout)
    if "+ posts" not in res.stdout or "insert: 1 rows" not in res.stdout.lower():
        print("FAILED: Uncommitted changes not fully detected")
    
    print("\n6. Committing changes...")
    run_gitdb(["commit", "-m", "Added posts table and Bob"])
    
    print("\n7. Verifying 'log'...")
    res = run_gitdb(["log", "--oneline"])
    print(res.stdout)
    lines = res.stdout.strip().split("\n")
    if len(lines) < 2:
        print("FAILED: Log should have at least 2 commits")
        
    head_hash = lines[0].split()[0]
    parent_hash = lines[1].split()[0]
    
    print(f"\n8. Checking out to parent commit {parent_hash}...")
    res = run_gitdb(["checkout", parent_hash])
    print(res.stdout)
    
    print("\n9. Verifying database state after checkout...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts';")
    if cursor.fetchone():
        print("FAILED: 'posts' table should have been dropped")
    else:
        print("SUCCESS: 'posts' table dropped")
        
    cursor.execute("SELECT COUNT(*) FROM users;")
    count = cursor.fetchone()[0]
    if count != 1:
        print(f"FAILED: 'users' table should have 1 row, found {count}")
    else:
        print("SUCCESS: 'users' table restored to 1 row")
    conn.close()

if __name__ == "__main__":
    main()
