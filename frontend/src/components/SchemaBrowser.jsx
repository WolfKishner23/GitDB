import React from 'react';

const SchemaBrowser = ({ schema }) => {
  if (!schema) return <div>No schema snapshot available.</div>;

  // Simple parsing of DDL to get tables and columns (naive for display)
  const tables = schema.split(';').filter(s => s.trim().startsWith('CREATE TABLE')).map(s => {
    const nameMatch = s.match(/CREATE TABLE (\w+)/);
    const tableName = nameMatch ? nameMatch[1] : 'Unknown';
    const columnsMatch = s.match(/\((.*)\)/s);
    const columns = columnsMatch ? columnsMatch[1].split(',').map(c => c.trim()) : [];
    return { name: tableName, columns };
  });

  return (
    <div className="space-y-6">
      {tables.map((table, i) => (
        <div key={i} className="border border-slate-700 rounded-xl overflow-hidden bg-slate-800/50 shadow-lg">
          <div className="bg-slate-700/50 p-3 flex items-center gap-2 border-b border-slate-600">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <h3 className="font-bold text-slate-200">{table.name}</h3>
          </div>
          <table className="w-full text-left text-sm text-slate-300">
            <thead>
              <tr className="bg-slate-900/30">
                <th className="p-3 border-b border-slate-700">Definition</th>
              </tr>
            </thead>
            <tbody>
              {table.columns.map((col, ci) => (
                <tr key={ci} className="hover:bg-slate-700/30 transition-colors border-b border-slate-700/50">
                  <td className="p-3 font-mono text-xs">{col}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
};

export default SchemaBrowser;
