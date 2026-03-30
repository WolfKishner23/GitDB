import React, { useEffect, useState } from 'react';
import ReactFlow, { Background, Controls } from 'reactflow';
import 'reactflow/dist/style.css';

const CommitGraph = ({ commits, onNodeClick }) => {
  const [nodes, setNodes] = useState([]);
  const [edges, setEdges] = useState([]);

  useEffect(() => {
    if (!commits || commits.length === 0) return;
    
    const newNodes = commits.map((c, i) => ({
      id: c.hash,
      data: { label: (
        <div className="p-3 border rounded shadow-lg bg-slate-800 border-slate-600 text-left cursor-pointer hover:border-yellow-500 transition-colors">
          <div className="font-mono font-bold text-yellow-400 mb-1">{c.hash.substring(0, 8)}</div>
          <div className="text-sm font-medium mb-2">{c.message}</div>
          <div className="text-xs text-slate-400">By <span className="text-blue-400">{c.author}</span></div>
        </div>
      )},
      position: { x: 100, y: i * 140 },
    }));

    const newEdges = [];
    commits.forEach(c => {
      if (c.parent_hash) {
        // Find if parent exists in our nodes
        if (commits.find(pc => pc.hash === c.parent_hash)) {
            newEdges.push({
                id: `e-${c.hash}-${c.parent_hash}`,
                source: c.hash,
                target: c.parent_hash,
                animated: true,
                style: { stroke: '#fbbf24', strokeWidth: 2 },
            });
        }
      }
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [commits]);

  return (
    <div className="h-[600px] w-full border border-slate-700 rounded-xl overflow-hidden bg-slate-900/50 backdrop-blur-sm">
      <ReactFlow 
        nodes={nodes} 
        edges={edges}
        onNodeClick={(e, node) => onNodeClick(node.id)}
        fitView
      >
        <Background color="#1e293b" gap={24} size={1} />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default CommitGraph;
