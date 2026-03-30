# GitDB User Guide

GitDB is a Git-like versioning engine for SQLite databases. This guide covers how to use the Snapshot Engine, the CLI, and the Web UI.

## Getting Started

### 1. Installation
Ensure you have the required dependencies:
```bash
pip install click rich python-dotenv sqlglot flask flask-marshmallow marshmallow-sqlalchemy flask-cors
```
For the frontend:
```bash
cd frontend
npm install
```

### 2. Configuration
Create a `.env` file in the project root with the path to your SQLite database:
```bash
GITDB_DATABASE_PATH=C:\path\to\your\database.db
```

### 3. Initialization
Initialize the GitDB metadata repository for your database:
```bash
python gitdb.py init
```

---

## Command Line Interface (CLI)

### Commit Changes
Capture the current state of the database:
```bash
python gitdb.py commit -m "Your commit message" --author "Your Name"
```

### View History
See the list of commits:
```bash
python gitdb.py log
# Or for a condensed view:
python gitdb.py log --oneline
```

### Compare States (Diff)
Show the SQL statements required to transform one state into another:
```bash
# Compare two specific commits
python gitdb.py diff <hash1> <hash2>

# Compare HEAD with a specific commit
python gitdb.py diff <hash1>
```

### Restore State (Checkout)
Revert the database to a previous commit:
```bash
python gitdb.py checkout <hash>
```

---

## Web UI

The Web UI provides a visual DAG of your commit history and a schema explorer.

### 1. Start the Backend API
```bash
python api.py
```

### 2. Start the Frontend
```bash
cd frontend
npm run dev
```
Open the provided URL (typically `http://localhost:5173` or `5174`) in your browser.

### Features:
- **Active DAG**: Visualize the lineage of your commits.
- **Schema Explorer**: View table definitions for any selected commit.
- **Diff Inspector**: Side-by-side SQL diffs between current and parent snapshots.
- **UI Checkout**: Revert state directly from the dashboard.
