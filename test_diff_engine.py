import sqlite3
import os
import json
import time
from snapshot_engine import (
    Commit, extract_schema, dump_data, generate_hash, 
    gitdb_init, save_commit, load_commit
)
from diff_engine import (
    diff_schema, diff_data, apply_patch, gitdb_diff, gitdb_checkout
)

def test_diff_engine():
    db_path = "test_p2.db"
    
    # 1. Setup initial database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO users (name) VALUES ('Alice')")
    conn.commit()
    conn.close()
    
    gitdb_init(db_path)
    
    # Commit 1
    schema1 = extract_schema(db_path)
    data1 = dump_data(db_path)
    hash1 = generate_hash(schema1, data1, "")
    c1 = Commit(hash1, "", "Commit 1", "Author", time.time(), schema1, json.dumps(data1))
    save_commit(c1, db_path)
    print(f"Commit 1: {hash1}")
    
    # 2. Modify database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
    cursor.execute("INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')")
    cursor.execute("UPDATE users SET email = 'alice@example.com' WHERE name = 'Alice'")
    conn.commit()
    conn.close()
    
    # Commit 2
    schema2 = extract_schema(db_path)
    data2 = dump_data(db_path)
    hash2 = generate_hash(schema2, data2, hash1)
    c2 = Commit(hash2, hash1, "Commit 2", "Author", time.time(), schema2, json.dumps(data2))
    save_commit(c2, db_path)
    print(f"Commit 2: {hash2}")
    
    # 3. Test gitdb_diff
    print("\n--- Running gitdb_diff ---")
    gitdb_diff(hash1, hash2, db_path)
    
    # 4. Test gitdb_checkout (Restore to Commit 1)
    print("\n--- Running gitdb_checkout to Commit 1 ---")
    gitdb_checkout(hash1, db_path)
    
    # 5. Verify restoration
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Let's check table info first to verify column existence
    cursor.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in cursor.fetchall()]
    print(f"Columns after checkout: {cols}")
    
    try:
        cursor.execute("SELECT name, email FROM users")
        rows = cursor.fetchall()
        print("Error: 'email' column still exists but should have been removed.")
    except sqlite3.OperationalError as e:
        print(f"Confirmed: {e}")

    cursor.execute("SELECT name FROM users")
    names = [row[0] for row in cursor.fetchall()]
    print(f"Names after checkout: {names}")
    
    assert 'email' not in cols
    assert names == ['Alice']
    print("\nRestoration successful!")
    
    assert 'email' not in cols
    assert names == ['Alice']
    print("\nRestoration successful!")
    
    conn.close()

if __name__ == "__main__":
    test_diff_engine()
    # Cleanup
    if os.path.exists("test_p2.db"): os.remove("test_p2.db")
    import shutil
    if os.path.exists(".gitdb"): shutil.rmtree(".gitdb")
