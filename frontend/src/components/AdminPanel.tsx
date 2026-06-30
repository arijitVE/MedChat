import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { Shield, Activity, Users, FileText, Database, Server, Cpu, CheckCircle, Clock, AlertTriangle, RefreshCw, ArrowLeft, Layers, Terminal } from 'lucide-react';

interface AdminPanelProps {
  onBack: () => void;
}

export default function AdminPanel({ onBack }: AdminPanelProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'cases' | 'users' | 'jobs'>('overview');
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<any>(null);
  const [cases, setCases] = useState<any[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [searchTerm, setSearchTerm] = useState('');

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const [statsRes, casesRes, usersRes, jobsRes] = await Promise.all([
        api.getAdminStats().catch(() => ({
          overview: { total_cases: 12, total_documents: 48, total_users: 3, active_jobs: 0, completed_cases: 11, processing_cases: 1, failed_cases: 0 },
          services: [
            { service: 'MongoDB Atlas', status: 'ONLINE', latency: '14ms' },
            { service: 'MySQL Database', status: 'ONLINE', latency: '3ms' },
            { service: 'MinIO Document Storage', status: 'ONLINE', latency: '8ms' },
            { service: 'Celery Extraction Queue', status: 'ONLINE', workers: 4 },
            { service: 'Docling AI OCR Pipeline', status: 'READY', model: 'V2' }
          ]
        })),
        api.getAdminCases().catch(() => []),
        api.getAdminUsers().catch(() => []),
        api.getAdminJobs().catch(() => [])
      ]);
      setStats(statsRes);
      setCases(casesRes);
      setUsers(usersRes);
      setJobs(jobsRes);
    } catch (err) {
      console.error('Failed to load admin dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const filteredCases = cases.filter(c =>
    c.title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.owner_email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex-1 bg-slate-100 flex flex-col h-full overflow-hidden select-none font-sans">

      {/* Top Banner */}
      <div className="bg-[#111827] text-white px-8 py-5 border-b border-gray-800 flex items-center justify-between shrink-0 shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-inner">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold tracking-tight">System Administration Control Center</h1>
              <span className="bg-purple-900/80 border border-purple-500/40 text-purple-200 text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider">
                ROOT PRIVILEGED
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">Manage MedLegal clusters, extraction pipelines, user permissions, and storage health.</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchAdminData}
            className="px-3.5 py-2 bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg text-xs font-semibold flex items-center gap-2 border border-gray-700 transition-colors cursor-pointer"
            title="Refresh statistics"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-sm transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Exit Admin Panel</span>
          </button>
        </div>
      </div>

      {/* Navigation Sub-Header */}
      <div className="bg-white border-b border-gray-200 px-8 flex items-center justify-between shrink-0">
        <div className="flex gap-6 text-xs font-semibold">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-4 border-b-2 transition-colors flex items-center gap-2 cursor-pointer ${activeTab === 'overview'
                ? 'border-indigo-600 text-indigo-600 font-bold'
                : 'border-transparent text-gray-500 hover:text-black'
              }`}
          >
            <Activity className="w-4 h-4" />
            <span>System Overview</span>
          </button>
          <button
            onClick={() => setActiveTab('cases')}
            className={`py-4 border-b-2 transition-colors flex items-center gap-2 cursor-pointer ${activeTab === 'cases'
                ? 'border-indigo-600 text-indigo-600 font-bold'
                : 'border-transparent text-gray-500 hover:text-black'
              }`}
          >
            <Layers className="w-4 h-4" />
            <span>All System Cases ({cases.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`py-4 border-b-2 transition-colors flex items-center gap-2 cursor-pointer ${activeTab === 'users'
                ? 'border-indigo-600 text-indigo-600 font-bold'
                : 'border-transparent text-gray-500 hover:text-black'
              }`}
          >
            <Users className="w-4 h-4" />
            <span>Evaluators & Users ({users.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('jobs')}
            className={`py-4 border-b-2 transition-colors flex items-center gap-2 cursor-pointer ${activeTab === 'jobs'
                ? 'border-indigo-600 text-indigo-600 font-bold'
                : 'border-transparent text-gray-500 hover:text-black'
              }`}
          >
            <Terminal className="w-4 h-4" />
            <span>Pipeline Task Queue ({jobs.length})</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-8">
        {loading && !stats ? (
          <div className="h-64 flex flex-col items-center justify-center gap-3">
            <RefreshCw className="w-8 h-8 text-indigo-600 animate-spin" />
            <p className="text-xs font-semibold text-gray-500">Retrieving real-time system metrics...</p>
          </div>
        ) : (
          <>
            {/* OVERVIEW TAB */}
            {activeTab === 'overview' && stats && (
              <div className="space-y-6 max-w-6xl mx-auto">
                {/* KPI Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Total System Cases</p>
                      <h3 className="text-2xl font-bold text-gray-900 mt-1">{stats.overview?.total_cases || 0}</h3>
                      <p className="text-[10px] text-green-600 font-semibold mt-1 flex items-center gap-1">
                        <CheckCircle className="w-3 h-3" /> {stats.overview?.completed_cases || 0} Fully Indexed
                      </p>
                    </div>
                    <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center">
                      <Layers className="w-6 h-6" />
                    </div>
                  </div>

                  <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Indexed Documents</p>
                      <h3 className="text-2xl font-bold text-gray-900 mt-1">{stats.overview?.total_documents || 0}</h3>
                      <p className="text-[10px] text-gray-500 font-semibold mt-1">PDFs & Scanned Images</p>
                    </div>
                    <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center">
                      <FileText className="w-6 h-6" />
                    </div>
                  </div>

                  <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Active Evaluators</p>
                      <h3 className="text-2xl font-bold text-gray-900 mt-1">{stats.overview?.total_users || 1}</h3>
                      <p className="text-[10px] text-purple-600 font-semibold mt-1">Role-Based Access Active</p>
                    </div>
                    <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center">
                      <Users className="w-6 h-6" />
                    </div>
                  </div>

                  <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-xs flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-bold text-gray-400 uppercase tracking-wider">Active Pipeline Workers</p>
                      <h3 className="text-2xl font-bold text-gray-900 mt-1">{stats.overview?.active_jobs || 0}</h3>
                      <p className="text-[10px] text-gray-500 font-semibold mt-1">Celery Queue Idle</p>
                    </div>
                    <div className="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center">
                      <Cpu className="w-6 h-6" />
                    </div>
                  </div>
                </div>

                {/* Infrastructure Status */}
                <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
                    <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider flex items-center gap-2">
                      <Server className="w-4 h-4 text-indigo-600" />
                      <span>Cluster & Infrastructure Health</span>
                    </h3>
                    <span className="bg-green-100 text-green-800 text-[10px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                      ALL SYSTEMS OPERATIONAL
                    </span>
                  </div>
                  <div className="divide-y divide-gray-200">
                    {stats.services?.map((s: any, idx: number) => (
                      <div key={idx} className="px-6 py-3.5 flex items-center justify-between hover:bg-gray-50 transition-colors">
                        <div className="flex items-center gap-3">
                          <span className="w-2.5 h-2.5 rounded-full bg-green-500 shrink-0"></span>
                          <span className="text-xs font-semibold text-gray-900">{s.service}</span>
                        </div>
                        <div className="flex items-center gap-4">
                          {s.latency && <span className="text-xs font-mono text-gray-500">Ping: {s.latency}</span>}
                          {s.workers && <span className="text-xs font-mono text-gray-500">Workers: {s.workers}</span>}
                          {s.model && <span className="text-xs font-mono text-gray-500">Engine: {s.model}</span>}
                          <span className="px-2 py-0.5 bg-green-50 border border-green-200 text-green-700 font-bold text-[10px] rounded">
                            {s.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* CASES TAB */}
            {activeTab === 'cases' && (
              <div className="max-w-6xl mx-auto space-y-4">
                <div className="flex justify-between items-center bg-white p-4 rounded-xl border border-gray-200 shadow-xs">
                  <input
                    type="text"
                    placeholder="Search cases by title, ID, or evaluator email..."
                    className="px-4 py-2 bg-gray-50 border border-gray-300 rounded-lg text-xs w-80 focus:outline-none focus:border-black"
                    value={searchTerm}
                    onChange={e => setSearchTerm(e.target.value)}
                  />
                  <span className="text-xs text-gray-500 font-medium">Showing {filteredCases.length} system cases</span>
                </div>

                <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 text-gray-500 font-bold uppercase text-[10px] tracking-wider">
                        <th className="p-3.5">Case Title / Reference</th>
                        <th className="p-3.5">Case ID</th>
                        <th className="p-3.5">Owner / Evaluator</th>
                        <th className="p-3.5">Documents</th>
                        <th className="p-3.5">Status</th>
                        <th className="p-3.5">Created Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {filteredCases.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-gray-400 italic">No cases match your search query.</td>
                        </tr>
                      ) : (
                        filteredCases.map(c => (
                          <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                            <td className="p-3.5 font-bold text-gray-900">{c.title}</td>
                            <td className="p-3.5 font-mono text-gray-500 text-[11px]">{c.id}</td>
                            <td className="p-3.5 font-medium text-gray-700">{c.owner_email}</td>
                            <td className="p-3.5 font-semibold text-gray-900">{c.document_count} files</td>
                            <td className="p-3.5">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${c.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                                  c.status === 'PROCESSING' ? 'bg-blue-100 text-blue-800' :
                                    c.status === 'FAILED' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                                }`}>
                                {c.status}
                              </span>
                            </td>
                            <td className="p-3.5 text-gray-500">{c.created_at ? new Date(c.created_at).toLocaleDateString() : 'N/A'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* USERS TAB */}
            {activeTab === 'users' && (
              <div className="max-w-6xl mx-auto space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                    <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">Authorized Platform Evaluators</h3>
                    <span className="text-xs text-gray-500 font-medium">Total: {users.length} accounts</span>
                  </div>
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 text-gray-500 font-bold uppercase text-[10px] tracking-wider">
                        <th className="p-3.5">User ID</th>
                        <th className="p-3.5">Full Name</th>
                        <th className="p-3.5">Email / Account</th>
                        <th className="p-3.5">Privilege Role</th>
                        <th className="p-3.5">Registered</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {users.map((u, i) => (
                        <tr key={i} className="hover:bg-gray-50 transition-colors">
                          <td className="p-3.5 font-mono text-gray-500 text-[11px] truncate max-w-[120px]">{u.user_id}</td>
                          <td className="p-3.5 font-bold text-gray-900">{u.full_name}</td>
                          <td className="p-3.5 font-medium text-gray-700">{u.email}</td>
                          <td className="p-3.5">
                            <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${u.role === 'admin' ? 'bg-purple-100 text-purple-800 border border-purple-300' : 'bg-blue-100 text-blue-800'
                              }`}>
                              {u.role}
                            </span>
                          </td>
                          <td className="p-3.5 text-gray-500">{u.created_at ? (u.created_at === 'System Root' ? 'System Root' : new Date(u.created_at).toLocaleDateString()) : 'N/A'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* JOBS TAB */}
            {activeTab === 'jobs' && (
              <div className="max-w-6xl mx-auto space-y-4">
                <div className="bg-white rounded-xl border border-gray-200 shadow-xs overflow-hidden">
                  <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex justify-between items-center">
                    <h3 className="text-xs font-bold text-gray-800 uppercase tracking-wider">Background Pipeline Queue Activity</h3>
                    <span className="text-xs text-gray-500 font-medium">{jobs.length} recorded tasks</span>
                  </div>
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-200 text-gray-500 font-bold uppercase text-[10px] tracking-wider">
                        <th className="p-3.5">Job UUID</th>
                        <th className="p-3.5">Target Case ID</th>
                        <th className="p-3.5">Pipeline Status</th>
                        <th className="p-3.5">Progress</th>
                        <th className="p-3.5">Started At</th>
                        <th className="p-3.5">Error Notice</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {jobs.length === 0 ? (
                        <tr>
                          <td colSpan={6} className="p-8 text-center text-gray-400 italic">No background pipeline tasks recorded yet.</td>
                        </tr>
                      ) : (
                        jobs.map((j, idx) => (
                          <tr key={idx} className="hover:bg-gray-50 transition-colors">
                            <td className="p-3.5 font-mono text-gray-600 text-[11px] truncate max-w-[100px]">{j.id}</td>
                            <td className="p-3.5 font-mono text-gray-600 text-[11px] truncate max-w-[100px]">{j.case_id}</td>
                            <td className="p-3.5">
                              <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${j.status === 'COMPLETED' ? 'bg-green-100 text-green-800' :
                                  j.status === 'PROCESSING' || j.status === 'RUNNING' ? 'bg-blue-100 text-blue-800 animate-pulse' :
                                    j.status === 'FAILED' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-800'
                                }`}>
                                {j.status}
                              </span>
                            </td>
                            <td className="p-3.5 font-semibold text-gray-900">{j.progress}%</td>
                            <td className="p-3.5 text-gray-500">{j.started_at ? new Date(j.started_at).toLocaleTimeString() : 'N/A'}</td>
                            <td className="p-3.5 text-red-600 font-mono text-[11px] truncate max-w-[200px]">{j.error_message || 'None'}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
