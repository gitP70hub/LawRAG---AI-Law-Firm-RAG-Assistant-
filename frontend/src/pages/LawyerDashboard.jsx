import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Scale, Users, FileText, Clock, BarChart3, Search,
  Plus, Loader2, ChevronRight, Filter, TrendingUp,
  Gavel, BookOpen, ArrowUpRight, Home,
} from 'lucide-react';
import CaseCard from '../components/CaseCard';
import { getCases, updateStatus } from '../api/client';

const STATUS_OPTIONS = [
  { value: '',          label: 'All Cases'  },
  { value: 'open',      label: 'Open'       },
  { value: 'in_review', label: 'In Review'  },
  { value: 'closed',    label: 'Closed'     },
  { value: 'archived',  label: 'Archived'   },
];

const NAV = [
  { icon: BarChart3, label: 'Overview',      path: '/lawyer' },
  { icon: Scale,     label: 'All Cases',     path: '/lawyer' },
  { icon: Users,     label: 'Client Portal', path: '/'       },
];

/* ─── Sidebar stat line ─────────────────────────────────── */
const SidebarStat = ({ label, value, color }) => (
  <div className="flex items-center justify-between px-3 py-1.5">
    <span className="text-xs text-sidebar-muted">{label}</span>
    <span className={`text-sm font-bold ${color}`}>{value}</span>
  </div>
);

/* ─── Overview metric card ──────────────────────────────── */
const MetricCard = ({ label, value, icon: Icon, delta, colorCls, bgCls }) => (
  <div className="card p-5">
    <div className="flex items-start justify-between">
      <div className={`w-10 h-10 rounded-xl ${bgCls} flex items-center justify-center`}>
        <Icon size={18} className={colorCls} />
      </div>
      {delta != null && (
        <span className="text-[10px] font-semibold text-emerald-600 bg-emerald-50
                         border border-emerald-200 rounded-full px-2 py-0.5">
          ↑ {delta}
        </span>
      )}
    </div>
    <p className="text-3xl font-black text-slate-800 mt-3 leading-none">{value}</p>
    <p className="text-xs text-slate-500 mt-1">{label}</p>
  </div>
);

export default function LawyerDashboard() {
  const [cases,   setCases]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [search,  setSearch]  = useState('');
  const [statusF, setStatusF] = useState('');
  const [sortBy,  setSortBy]  = useState('newest');
  const [activeNav, setActiveNav] = useState('/lawyer');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 200 };
      if (statusF) params.status = statusF;
      const { data } = await getCases(params);
      setCases(data.items || []);
    } catch { setCases([]); }
    finally { setLoading(false); }
  }, [statusF]);

  useEffect(() => { load(); }, [load]);

  const handleStatusChange = async (caseId, status) => {
    try {
      await updateStatus(caseId, status);
      setCases(prev => prev.map(c => c.id === caseId ? { ...c, status } : c));
    } catch {}
  };

  let filtered = cases.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    c.client_name.toLowerCase().includes(search.toLowerCase())
  );

  if (sortBy === 'newest') filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  if (sortBy === 'oldest') filtered.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  if (sortBy === 'az')     filtered.sort((a, b) => a.title.localeCompare(b.title));

  const stats = {
    total:     cases.length,
    open:      cases.filter(c => c.status === 'open').length,
    in_review: cases.filter(c => c.status === 'in_review').length,
    closed:    cases.filter(c => c.status === 'closed').length,
  };

  const recent = [...cases]
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
    .slice(0, 5);

  return (
    <div className="min-h-screen bg-surface flex">
      {/* ── Sidebar ── */}
      <aside className="w-sidebar min-h-screen bg-sidebar flex flex-col fixed left-0 top-0 z-20">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-sidebar-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-sm">
              <Scale size={16} className="text-white" />
            </div>
            <div>
              <p className="font-bold text-white text-sm">LawRAG</p>
              <p className="text-[10px] text-sidebar-muted">Practice Management</p>
            </div>
          </div>
        </div>

        {/* Badge */}
        <div className="mx-4 mt-4 px-3 py-2 rounded-xl bg-indigo-600/10 border border-indigo-600/20">
          <p className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest">Lawyer View</p>
          <p className="text-[11px] text-indigo-300/70 mt-0.5">Full admin access</p>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-5 space-y-0.5">
          <p className="section-title px-3 mb-3">Navigation</p>
          {NAV.map(({ icon: Icon, label, path }) => (
            <Link
              key={label}
              to={path}
              onClick={() => setActiveNav(path)}
              className={`sidebar-link ${activeNav === path && path !== '/' ? 'active' : ''}`}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </nav>

        {/* Sidebar stats */}
        <div className="mx-3 mb-3 rounded-xl bg-sidebar-hover border border-sidebar-border overflow-hidden">
          <p className="section-title px-3 pt-3 pb-2">Case Summary</p>
          <SidebarStat label="Open"      value={stats.open}      color="text-emerald-400" />
          <SidebarStat label="In Review" value={stats.in_review} color="text-amber-400"   />
          <SidebarStat label="Closed"    value={stats.closed}    color="text-slate-500"   />
          <SidebarStat label="Total"     value={stats.total}     color="text-indigo-400"  />
          <div className="pb-2" />
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="ml-sidebar flex-1 min-h-screen">
        {/* Top bar */}
        <header className="sticky top-0 z-10 glass border-b border-slate-200/60">
          <div className="px-8 h-[60px] flex items-center justify-between">
            <div>
              <h1 className="font-bold text-slate-900">Case Management</h1>
              <p className="text-[11px] text-slate-500">
                {stats.total} matters · {stats.open} open · {stats.in_review} in review
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link to="/" className="btn-secondary text-xs py-1.5">
                <Home size={13} /> Client Portal
              </Link>
              <Link to="/" className="btn-primary text-xs py-1.5">
                <Plus size={13} /> New Case
              </Link>
            </div>
          </div>
        </header>

        <div className="p-8 space-y-8">
          {/* Metric cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard label="Total Matters" value={stats.total}     icon={Scale}    colorCls="text-indigo-600" bgCls="bg-indigo-50" />
            <MetricCard label="Open"          value={stats.open}      icon={BookOpen} colorCls="text-emerald-600" bgCls="bg-emerald-50" delta={stats.open > 0 ? stats.open : null} />
            <MetricCard label="In Review"     value={stats.in_review} icon={Clock}    colorCls="text-amber-600"  bgCls="bg-amber-50"  />
            <MetricCard label="Closed"        value={stats.closed}    icon={Gavel}    colorCls="text-slate-600"  bgCls="bg-slate-100" />
          </div>

          {/* Recent matters panel */}
          {recent.length > 0 && (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-2">
                  <TrendingUp size={16} className="text-indigo-500" />
                  <h2 className="font-semibold text-slate-800">Recent Activity</h2>
                </div>
                <span className="text-[11px] text-slate-400">Latest {recent.length} cases</span>
              </div>

              <div className="divide-y divide-slate-100">
                {recent.map(c => {
                  const initials = (c.client_name || '?')
                    .split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();
                  return (
                    <div key={c.id} className="flex items-center gap-4 py-3 group">
                      {/* Avatar */}
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-400
                                      to-indigo-600 flex items-center justify-center flex-shrink-0">
                        <span className="text-[10px] font-bold text-white">{initials}</span>
                      </div>

                      <Link to={`/case/${c.id}`}
                        className="flex-1 min-w-0 hover:text-indigo-700 transition-colors">
                        <p className="text-sm font-medium truncate">{c.title}</p>
                        <p className="text-xs text-slate-500 truncate">{c.client_name}</p>
                      </Link>

                      <div className="flex items-center gap-2 flex-shrink-0">
                        <select
                          value={c.status}
                          onChange={e => handleStatusChange(c.id, e.target.value)}
                          onClick={e => e.stopPropagation()}
                          className="text-xs border border-slate-200 rounded-lg px-2 py-1
                                     bg-white focus:outline-none focus:ring-2 focus:ring-indigo-400/30"
                        >
                          <option value="open">Open</option>
                          <option value="in_review">In Review</option>
                          <option value="closed">Closed</option>
                          <option value="archived">Archived</option>
                        </select>
                        <Link to={`/case/${c.id}`}>
                          <ChevronRight size={15}
                            className="text-slate-300 group-hover:text-indigo-500 transition-colors" />
                        </Link>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Filters + full grid */}
          <div className="space-y-4">
            <div className="flex flex-wrap gap-3 items-center">
              <div className="relative flex-1 min-w-48">
                <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Search by title or client…"
                  className="input pl-10 py-2 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <Filter size={14} className="text-slate-400" />
                <select value={statusF} onChange={e => setStatusF(e.target.value)}
                  className="input py-2 text-sm w-36">
                  {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
                <select value={sortBy} onChange={e => setSortBy(e.target.value)}
                  className="input py-2 text-sm w-32">
                  <option value="newest">Newest</option>
                  <option value="oldest">Oldest</option>
                  <option value="az">A → Z</option>
                </select>
              </div>
            </div>

            {loading ? (
              <div className="flex justify-center py-20">
                <Loader2 size={28} className="animate-spin text-indigo-500" />
              </div>
            ) : (
              <>
                <p className="text-xs text-slate-400">
                  {filtered.length} case{filtered.length !== 1 ? 's' : ''}
                </p>
                {filtered.length === 0 ? (
                  <div className="flex flex-col items-center py-20 text-slate-400 gap-3">
                    <Search size={32} className="text-slate-300" />
                    <p className="font-medium text-slate-500">No matching cases</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                    {filtered.map(c => (
                      <Link key={c.id} to={`/case/${c.id}`} className="block">
                        <CaseCard caseData={c} />
                      </Link>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
