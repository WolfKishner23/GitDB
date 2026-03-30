import React from 'react';
import ReactDiffViewer from 'react-diff-viewer';

const DiffViewer = ({ oldCode, newCode, title }) => {
  return (
    <div className="border border-slate-700 rounded-xl overflow-hidden bg-white shadow-2xl">
      <div className="bg-slate-100 p-4 border-b border-slate-200 flex justify-between items-center">
        <h3 className="text-slate-800 font-bold font-mono text-sm">{title}</h3>
        <div className="flex gap-2">
            <span className="px-2 py-0.5 rounded bg-red-100 text-red-700 text-xs font-bold">- OLD</span>
            <span className="px-2 py-0.5 rounded bg-green-100 text-green-700 text-xs font-bold">+ NEW</span>
        </div>
      </div>
      <ReactDiffViewer 
        oldValue={oldCode || ""} 
        newValue={newCode || ""} 
        splitView={true}
        useDarkTheme={false}
        styles={{
            variables: {
                diffViewerBackground: '#fff',
                diffViewerTitleBackground: '#f1f5f9',
                diffViewerTitleColor: '#1e293b',
                addedBackground: '#f0fdf4',
                addedColor: '#166534',
                removedBackground: '#fef2f2',
                removedColor: '#991b1b',
                wordAddedBackground: '#dcfce7',
                wordRemovedBackground: '#fee2e2',
            },
            lineNumber: {
                color: '#94a3b8',
            }
        }}
      />
    </div>
  );
};

export default DiffViewer;
