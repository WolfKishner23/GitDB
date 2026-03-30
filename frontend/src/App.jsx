import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { GitBranch, FileDiff, Database, RefreshCw, Layers } from 'lucide-react';
import { fetchCommits, checkoutCommit, fetchDiff } from './services/api';
import CommitGraph from './components/CommitGraph';
import DiffViewer from './components/DiffViewer';
import SchemaBrowser from './components/SchemaBrowser';

function App() {
  const [commits, setCommits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedCommit, setSelectedCommit] = useState(null);
  const [diffData, setDiffData] = useState(null);

  useEffect(() => {
    loadCommits();
  }, []);

  const loadCommits = async () => {
    setLoading(true);
    try {
        const data = await fetchCommits();
        setCommits(data);
        if (data.length > 0 && !selectedCommit) {
            handleNodeClick(data[0].hash, data);
        }
    } catch (e) {
        console.error("Failed to load commits", e);
    }
    setLoading(false);
  };

  const handleNodeClick = async (hash, currentCommits = commits) => {
    const commit = currentCommits.find(c => c.hash === hash);
    setSelectedCommit(commit);
    
    if (commit.parent_hash) {
      try {
        const diff = await fetchDiff(commit.parent_hash, commit.hash);
        setDiffData(diff);
      } catch (e) {
        setDiffData(null);
      }
    } else {
      setDiffData({
        old_schema: '',
        new_schema: commit.schema_snapshot,
        schema_diff: ['Initial Creation']
      });
    }
  };

  const handleCheckout = async (hash) => {
    if (window.confirm(`Checkout commit ${hash.substring(0, 8)}?`)) {
      try {
        await checkoutCommit(hash);
        alert('Checkout successful!');
        loadCommits();
      } catch (e) {
        alert('Checkout failed: ' + e.message);
      }
    }
  };

  return (
    <Router>
      <div className="min-h-screen flex flex-col font-sans">
        {/* Navbar */}
        <nav className="bg-[#0f172a] border-b border-slate-800 p-4 sticky top-0 z-50 shadow-xl backdrop-blur-md bg-opacity-90">
          <div className="container mx-auto flex justify-between items-center">
            <div className="flex items-center gap-3 group">
              <div className="bg-yellow-500 p-2 rounded-xl group-hover:rotate-12 transition-transform shadow-[0_0_15px_rgba(234,179,8,0.3)]">
                <Database className="text-slate-900" size={24} />
              </div>
              <div>
                <h1 className="text-xl font-black tracking-tight text-white uppercase italic">GitDB</h1>
                <p className="text-[10px] text-slate-500 font-bold tracking-[0.2em] uppercase flex items-center gap-1">Versioning Engine</p>
              </div>
            </div>
            
            <div className="flex gap-8">
              <Link to="/" className="flex items-center gap-2 text-slate-400 hover:text-yellow-500 font-bold text-sm transition-all"><GitBranch size={16} /> LOG</Link>
              <Link to="/diff" className="flex items-center gap-2 text-slate-400 hover:text-yellow-500 font-bold text-sm transition-all"><FileDiff size={16} /> DIFFS</Link>
              <Link to="/schema" className="flex items-center gap-2 text-slate-400 hover:text-yellow-500 font-bold text-sm transition-all"><Database size={16} /> SCHEMA</Link>
            </div>
          </div>
        </nav>

        {/* Content */}
        <main className="container mx-auto p-8 flex-grow">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-[60vh] gap-6">
              <RefreshCw className="animate-spin text-yellow-500" size={64} strokeWidth={3} />
              <div className="text-center">
                <p className="text-white text-xl font-bold">Synchronizing index...</p>
                <p className="text-slate-500 text-sm mt-1">Fetching latest snapshot from GitDB instance</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-12 gap-10">
              <div className="col-span-12 lg:col-span-7 space-y-8">
                <section className="space-y-4">
                  <div className="flex justify-between items-end">
                    <div>
                        <h2 className="text-3xl font-black text-white uppercase tracking-tight">Active DAG</h2>
                        <p className="text-slate-500 text-sm font-medium">Visualization of commit lineage</p>
                    </div>
                    <button onClick={loadCommits} className="bg-slate-800 p-2 rounded-lg text-slate-400 hover:text-white transition-colors"><RefreshCw size={20} /></button>
                  </div>
                  <CommitGraph commits={commits} onNodeClick={(h) => handleNodeClick(h)} />
                </section>
                
                {selectedCommit && (
                  <section className="p-8 bg-[#1e293b]/60 backdrop-blur-xl rounded-[2rem] border border-slate-700/50 shadow-2xl space-y-6 relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-500/5 blur-3xl rounded-full -mr-16 -mt-16" />
                    
                    <div className="flex justify-between items-start relative z-10">
                      <div>
                        <div className="flex items-center gap-3 mb-2">
                            <span className="px-3 py-1 rounded-full bg-yellow-500/10 text-yellow-500 text-[10px] font-black tracking-widest uppercase">Node Selected</span>
                            <span className="text-slate-600 text-xs font-mono">{selectedCommit.hash}</span>
                        </div>
                        <h3 className="text-4xl font-black text-white leading-tight uppercase tracking-tight">{selectedCommit.message}</h3>
                      </div>
                      <button 
                        onClick={() => handleCheckout(selectedCommit.hash)}
                        className="px-6 py-3 bg-yellow-500 hover:bg-yellow-400 text-slate-900 font-black rounded-2xl shadow-[0_0_20px_rgba(234,179,8,0.3)] active:scale-95 transition-all text-sm flex items-center gap-2 uppercase tracking-wide"
                      >
                        <RefreshCw size={18} strokeWidth={3} /> Checkout
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-6 relative z-10">
                      <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-700/30">
                        <p className="text-slate-500 uppercase text-[10px] font-black tracking-[0.2em] mb-2">Author</p>
                        <p className="text-blue-400 text-lg font-bold">{selectedCommit.author}</p>
                      </div>
                      <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-700/30">
                        <p className="text-slate-500 uppercase text-[10px] font-black tracking-[0.2em] mb-2">Committed At</p>
                        <p className="text-slate-300 text-lg font-bold">{new Date(selectedCommit.timestamp * 1000).toLocaleString()}</p>
                      </div>
                    </div>
                  </section>
                )}
              </div>

              <div className="col-span-12 lg:col-span-5 space-y-8">
                <Routes>
                  <Route path="/" element={
                      selectedCommit ? (
                        <div className="space-y-6">
                            <div className="px-2">
                                <h2 className="text-2xl font-black text-white uppercase tracking-tight">Schema Explorer</h2>
                                <p className="text-slate-500 text-sm font-medium">Structure at this snapshot</p>
                            </div>
                           <SchemaBrowser schema={selectedCommit.schema_snapshot} />
                        </div>
                      ) : null
                    } 
                  />
                  <Route path="/diff" element={
                      diffData ? (
                        <div className="space-y-6">
                          <div className="px-2">
                                <h2 className="text-2xl font-black text-white uppercase tracking-tight">Diff Inspector</h2>
                                <p className="text-slate-500 text-sm font-medium">Comparison with parent node</p>
                          </div>
                          <DiffViewer 
                            oldCode={diffData.old_schema} 
                            newCode={diffData.new_schema} 
                            title={`DDL Delta: ${selectedCommit?.hash?.substring(0,8)}`} 
                          />
                        </div>
                      ) : <div className="p-20 text-center text-slate-700 font-bold uppercase tracking-widest text-sm">Select a node to inspect diffs</div>
                    } 
                  />
                  <Route path="/schema" element={
                     selectedCommit ? (
                        <div className="space-y-6">
                           <div className="px-2">
                                <h2 className="text-2xl font-black text-white uppercase tracking-tight">Full Schema</h2>
                                <p className="text-slate-500 text-sm font-medium">Relational model details</p>
                           </div>
                           <SchemaBrowser schema={selectedCommit.schema_snapshot} />
                        </div>
                      ) : null
                    } 
                  />
                </Routes>
              </div>
            </div>
          )}
        </main>

        <footer className="bg-[#0f172a] border-t border-slate-800 py-8 px-4 text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-slate-800 bg-slate-900/50">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-slate-500 text-[10px] font-black uppercase tracking-[0.3em]">System Operational • GitDB Core v1.0.4</span>
            </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
