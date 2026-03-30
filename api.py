from flask import Flask, jsonify, request
from flask_marshmallow import Marshmallow
from flask_cors import CORS
from marshmallow import Schema, fields
import os
import json
from dotenv import load_dotenv
from snapshot_engine import Commit, load_commit
from diff_engine import get_full_patch, gitdb_checkout

load_dotenv()
DB_PATH = os.getenv("GITDB_DATABASE_PATH")
app = Flask(__name__)
ma = Marshmallow(app)
CORS(app, resources={r"/*": {"origins": "*"}})

class CommitSchema(ma.Schema):
    hash = fields.Str()
    parent_hash = fields.Str()
    message = fields.Str()
    author = fields.Str()
    timestamp = fields.Float()
    schema_snapshot = fields.Str()
    data_snapshot = fields.Str()

commit_schema = CommitSchema()
commits_schema = CommitSchema(many=True)

def get_all_commits():
    gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), ".gitdb")
    commits_dir = os.path.join(gitdb_dir, "commits")
    commits = []
    if os.path.exists(commits_dir):
        for f in os.listdir(commits_dir):
            if f.endswith(".json"):
                with open(os.path.join(commits_dir, f), "r") as file:
                    commits.append(Commit.from_json(file.read()))
    return sorted(commits, key=lambda x: x.timestamp, reverse=True)

@app.route('/commits', methods=['GET'])
def get_commits():
    commits = get_all_commits()
    return jsonify(commits_schema.dump(commits))

@app.route('/commits/<hash>', methods=['GET'])
def get_commit_by_hash(hash):
    gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), ".gitdb")
    path = os.path.join(gitdb_dir, "commits", f"{hash}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            c = Commit.from_json(f.read())
            return jsonify(commit_schema.dump(c))
    return jsonify({"error": "Commit not found"}), 404

@app.route('/diff/<hash1>/<hash2>', methods=['GET'])
def get_diff(hash1, hash2):
    try:
        gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), ".gitdb")
        commits_dir = os.path.join(gitdb_dir, "commits")
        
        def load_c(h):
            path = os.path.join(commits_dir, f"{h}.json")
            if not os.path.exists(path):
                # Try to resolve short hash
                for f in os.listdir(commits_dir):
                    if f.startswith(h) and f.endswith(".json"):
                        path = os.path.join(commits_dir, f)
                        break
            with open(path, "r") as f:
                return Commit.from_json(f.read())
                
        c1 = load_c(hash1)
        c2 = load_c(hash2)
        s_diff, d_diff = get_full_patch(c1, c2)
        
        # Format d_diff for JSON
        data_diff_serializable = []
        for stmt in d_diff:
            if isinstance(stmt, tuple):
                data_diff_serializable.append({"sql": stmt[0], "params": stmt[1]})
            else:
                data_diff_serializable.append({"sql": stmt, "params": []})
            
        return jsonify({
            "schema_diff": s_diff,
            "data_diff": data_diff_serializable,
            "old_schema": c1.schema_snapshot,
            "new_schema": c2.schema_snapshot
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/checkout/<hash>', methods=['POST'])
def checkout(hash):
    try:
        # Full hash resolution might be needed
        gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(DB_PATH)), ".gitdb")
        commits_dir = os.path.join(gitdb_dir, "commits")
        full_hash = hash
        for f in os.listdir(commits_dir):
            if f.startswith(hash) and f.endswith(".json"):
                full_hash = f.replace(".json", "")
                break
                
        gitdb_checkout(full_hash, DB_PATH)
        return jsonify({"message": f"Successfully checked out to {full_hash}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)
