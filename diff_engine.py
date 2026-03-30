import sqlglot
from sqlglot import exp, diff, parse_one
import json
import sqlite3
import os
import hashlib
from snapshot_engine import load_commit, Commit, extract_schema, dump_data, generate_hash

def diff_schema(old_ddl, new_ddl):
    """Uses sqlglot to take two DDL strings and returns categorized SQL statements."""
    old_exprs = sqlglot.parse(old_ddl, read="sqlite")
    new_exprs = sqlglot.parse(new_ddl, read="sqlite")
    
    categories = {
        "DROP": [],
        "CREATE": [],
        "ALTER": []
    }
    
    # Map table name to CREATE statement
    def get_table_map(exprs):
        tables = {}
        for expr in exprs:
            if isinstance(expr, exp.Create) and expr.args.get("kind") == "TABLE":
                name = expr.this.this.name
                tables[name] = expr
        return tables

    old_tables = get_table_map(old_exprs)
    new_tables = get_table_map(new_exprs)

    # Drops
    for name in old_tables:
        if name not in new_tables:
            categories["DROP"].append(f"DROP TABLE {name};")

    # Creates and Alters
    for name in new_tables:
        if name not in old_tables:
            categories["CREATE"].append(new_tables[name].sql(dialect="sqlite") + ";")
        else:
            # Check for changes. SQLite ALTER TABLE is limited, so we recreate for complex changes.
            if old_tables[name] != new_tables[name]:
                # Complex change: DROP then CREATE (categorized separately)
                categories["DROP"].append(f"DROP TABLE {name};")
                categories["CREATE"].append(new_tables[name].sql(dialect="sqlite") + ";")
                
    return categories

def diff_data(old_data, new_data, recreated_tables=None):
    """Compares two JSON row dumps and returns categorized list of (SQL, params)."""
    categories = {
        "DELETE": [],
        "UPDATE": [],
        "INSERT": []
    }
    recreated_tables = recreated_tables or set()
    
    for table_name in set(old_data.keys()).union(new_data.keys()):
        if table_name.startswith("__"): continue
        
        old_table = old_data.get(table_name, {})
        new_table = new_data.get(table_name, {})
        
        # Determine PK columns (simplified inference)
        sample_row = next(iter(new_table.values()), next(iter(old_table.values()), {}))
        pk_cols = []
        if sample_row:
            pk_cols = [k for k in sample_row.keys() if k.lower() == 'id']
            if not pk_cols: pk_cols = [list(sample_row.keys())[0]]

        if table_name in recreated_tables:
            # Force INSERT for all rows in new_table
            for pk_val in new_table:
                row = new_table[pk_val]
                cols = ", ".join(row.keys())
                placeholders = ", ".join(["?" for _ in row])
                categories["INSERT"].append((f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders});", list(row.values())))
            continue

        # Deletes
        for pk_val in old_table:
            if pk_val not in new_table:
                row = old_table[pk_val]
                where = " AND ".join([f"{col} = ?" for col in pk_cols])
                vals = [row[col] for col in pk_cols]
                categories["DELETE"].append((f"DELETE FROM {table_name} WHERE {where};", vals))

        # Updates
        for pk_val in new_table:
            if pk_val in old_table:
                if old_table[pk_val] != new_table[pk_val]:
                    row = new_table[pk_val]
                    old_row = old_table[pk_val]
                    updates = []
                    vals = []
                    for col, val in row.items():
                        if val != old_row.get(col):
                            updates.append(f"{col} = ?")
                            vals.append(val)
                    
                    if updates:
                        where = " AND ".join([f"{col} = ?" for col in pk_cols])
                        vals.extend([row[col] for col in pk_cols])
                        categories["UPDATE"].append((f"UPDATE {table_name} SET {', '.join(updates)} WHERE {where};", vals))

        # Inserts
        for pk_val in new_table:
            if pk_val not in old_table:
                row = new_table[pk_val]
                cols = ", ".join(row.keys())
                placeholders = ", ".join(["?" for _ in row])
                categories["INSERT"].append((f"INSERT INTO {table_name} ({cols}) VALUES ({placeholders});", list(row.values())))
                
    return categories

def apply_patch(db_path, patch_statements):
    """Applies a list of SQL patch statements to a SQLite database inside a single atomic transaction."""
    conn = sqlite3.connect(db_path)
    try:
        # Reference Requirement: PRAGMA foreign_keys = OFF is set for the duration of the patch
        conn.execute("PRAGMA foreign_keys = OFF;")
        conn.execute("BEGIN TRANSACTION;")
        
        for stmt in patch_statements:
            if isinstance(stmt, tuple):
                conn.execute(stmt[0], stmt[1])
            else:
                conn.execute(stmt)
                
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.close()

def get_full_patch(c1, c2):
    """Computes full schema and data patch between two commits in a safe ordered sequence."""
    s_cats = diff_schema(c1.schema_snapshot, c2.schema_snapshot)
    
    # Identify recreated tables to force full data insert
    recreated = set()
    for drop_stmt in s_cats["DROP"]:
        recreated.add(drop_stmt.replace("DROP TABLE ", "").replace(";", "").strip())
                
    d_cats = diff_data(json.loads(c1.data_snapshot), json.loads(c2.data_snapshot), recreated)
    
    # Safe Ordering: DROP -> CREATE -> ALTER -> DELETE -> UPDATE -> INSERT
    ordered_patch = (
        s_cats["DROP"] + 
        s_cats["CREATE"] + 
        s_cats["ALTER"] + 
        d_cats["DELETE"] + 
        d_cats["UPDATE"] + 
        d_cats["INSERT"]
    )
    return ordered_patch

def gitdb_diff(commit1_hash, commit2_hash, repo_path, schema_only=False, data_only=False):
    """Loads two commits, runs the schema diff and data diff, and prints the resulting SQL."""
    gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(repo_path)), ".gitdb")
    commits_dir = os.path.join(gitdb_dir, "commits")
    
    def get_commit(h):
        path = os.path.join(commits_dir, f"{h}.json")
        with open(path, "r") as f:
            return Commit.from_json(f.read())
            
    c1 = get_commit(commit1_hash)
    c2 = get_commit(commit2_hash)
    
    s_cats = diff_schema(c1.schema_snapshot, c2.schema_snapshot)
    recreated = set()
    for drop_stmt in s_cats["DROP"]:
        recreated.add(drop_stmt.replace("DROP TABLE ", "").replace(";", "").strip())
    d_cats = diff_data(json.loads(c1.data_snapshot), json.loads(c2.data_snapshot), recreated)
    
    print(f"-- Diff between {commit1_hash[:8]} and {commit2_hash[:8]}")
    
    if not data_only:
        for cat in ["DROP", "CREATE", "ALTER"]:
            for s in s_cats[cat]:
                print(s)
            
    if not schema_only:
        for cat in ["DELETE", "UPDATE", "INSERT"]:
            for stmt in d_cats[cat]:
                if isinstance(stmt, tuple):
                    s, params = stmt
                    p_str = ", ".join([repr(p) for p in params])
                    print(f"{s} -- Params: {p_str}")
                else:
                    print(stmt)
    
    # For API/internal use, return the combined patch
    return get_full_patch(c1, c2)

def gitdb_checkout(target_hash, repo_path):
    """Computes the diff between HEAD and a target commit hash, applies the patch atomically, and updates HEAD."""
    head_commit = load_commit(repo_path)
    if not head_commit:
        raise Exception("No HEAD commit found. Initialize and commit first.")
        
    gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(repo_path)), ".gitdb")
    target_path = os.path.join(gitdb_dir, "commits", f"{target_hash}.json")
    
    if not os.path.exists(target_path):
        raise Exception(f"Target commit {target_hash} not found.")
        
    with open(target_path, "r") as f:
        target_commit = Commit.from_json(f.read())
        
    full_patch = get_full_patch(head_commit, target_commit)
    
    print(f"Applying patch to reach commit {target_hash}...")
    apply_patch(repo_path, full_patch)
    
    # Update HEAD
    head_path = os.path.join(gitdb_dir, "HEAD")
    with open(head_path, "w") as f:
        f.write(target_hash)
    print("Checkout successful.")
