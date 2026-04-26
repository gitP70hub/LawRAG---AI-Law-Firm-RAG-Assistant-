import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Scale, MessageSquare, FileText, Clock,
  Plus, Search, Loader2, X, AlertCircle,
  ArrowRight, Gavel, BookOpen,
} from 'lucide-react';
import CaseCard from '../components/CaseCard';
import { getCases, createCase } from '../api/client';

/* ─── New Case modal ────────────────────────────────────── */
const NewCaseModal = ({ onClose, onCreated }) => {
  const [form, setForm] = useState({
    title: '', description: '', client_name: '', status: 'open',
  });
  const [saving, setSaving] = useState(false);
  const [err,    setErr]    = useState(null);

  const set = (key) => (e) => setForm(f => ({ ...f, [key]: e.target.value }));

  const save = async () => {
    if (!form.title.trim() || !form.client_name.trim()) {
      setErr('Case title and client name are required.'); return;
    }
    setSaving(true); setErr(null);
    try {
      const { data } = await createCase(form);
      onCreated(data); onClose();
    } catch (e) {
      setErr(e.message || 'Failed to create case.');
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50
                    flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-card-lg w-full max-w-lg animate-scale-in">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center">
              <Gavel size={16} className="text-white" />
            </div>
            <div>
              <h2 className="font-bold text-slate-900">New Case</h2>
              <p className="text-[11px] text-slate-400">Create a new legal matter</p>
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost p-1.5">
            <X size={17} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {err && (
            <div className="flex items-center gap-2.5 p-3.5 rounded-xl border border-red-200
                            bg-red-50 text-sm text-red-700">
              <AlertCircle size={14} className="flex-shrink-0" /> {err}
            </div>
          )}

          {[
            { key: 'title',       label: 'Case Title *',   placeholder: 'e.g. Sharma v. ABC Corp — Property Dispute' },
            { key: 'client_name', label: 'Client Name *',  placeholder: 'e.g. Ravi Sharma'                          },
          ].map(({ key, label, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-semibold text-slate-600 mb-1.5">{label}</label>
              <input
                value={form[key]}
                onChange={set(key)}
                className="input"
                placeholder={placeholder}
              />
            </div>
          ))}

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Description</label>
            <textarea
              value={form.description}
              onChange={set('description')}
              className="input resize-none"
              rows={3}
              placeholder="Brief description of the legal matter…"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Status</label>
            <select value={form.status} onChange={set('status')} className="input">
              <option value="open">Open</option>
              <option value="in_review">In Review</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-2 px-6 pb-6">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Create Case
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Stat card ─────────────────────────────────────────── */
const StatCard = ({ label, value, icon: Icon, colorCls, bgCls }) => (
  <div className="card p-5 flex items-center gap-4">
    <div className={`w-11 h-11 rounded-2xl flex items-center justify-center flex-shrink-0 ${bgCls}`}>
      <Icon size={20} className={colorCls} />
    </div>
    <div>
      <p className="text-2xl font-black text-slate-800 leading-none">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{label}</p>
    </div>
  </div>
);

const STAT_DEFS = [
  { label: 'Total Cases', key: 'total',     icon: Scale,        colorCls: 'text-indigo-600', bgCls: 'bg-indigo-50' },
  { label: 'Open',        key: 'open',      icon: BookOpen,     colorCls: 'text-emerald-600', bgCls: 'bg-emerald-50' },
  { label: 'In Review',   key: 'in_review', icon: Clock,        colorCls: 'text-amber-600',  bgCls: 'bg-amber-50'  },
  { label: 'Closed',      key: 'closed',    icon: FileText,     colorCls: 'text-slate-500',  bgCls: 'bg-slate-100' },
];

/* ─── Main ClientDashboard ──────────────────────────────── */
export default function ClientDashboard() {
  const [cases,   setCases]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [search,  setSearch]  = useState('');
  const [showNew, setShowNew] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await getCases({ limit: 100 });
      setCases(data.items || []);
    } catch { setCases([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = cases.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    c.client_name.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total:     cases.length,
    open:      cases.filter(c => c.status === 'open').length,
    in_review: cases.filter(c => c.status === 'in_review').length,
    closed:    cases.filter(c => c.status === 'closed').length,
  };

  return (
    <div className="min-h-screen bg-surface">
      {/* ── Top nav ── */}
      <header className="sticky top-0 z-30 glass border-b border-slate-200/60">
        <div className="max-w-7xl mx-auto px-6 h-[60px] flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700
                            flex items-center justify-center shadow-sm">
              <Scale size={15} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-slate-900">LawRAG</span>
              <span className="text-[11px] text-slate-400 ml-2 border border-slate-200 rounded-full
                               px-2 py-0.5">Client Portal</span>
            </div>
          </div>

          {/* Nav actions */}
          <div className="flex items-center gap-2">
            <Link to="/lawyer" className="btn-secondary text-xs py-1.5">
              Lawyer View <ArrowRight size={12} />
            </Link>
            <button onClick={() => setShowNew(true)} className="btn-primary text-xs py-1.5">
              <Plus size={14} /> New Case
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Welcome banner */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-indigo-600
                        to-indigo-800 p-8 text-white shadow-card-lg">
          <div className="relative z-10">
            <p className="text-indigo-200 text-sm font-medium mb-1">Welcome back</p>
            <h1 className="text-2xl font-bold">Your Legal Matters</h1>
            <p className="text-indigo-200 text-sm mt-1 max-w-md">
              Manage your cases, upload documents, and get AI-powered legal insights.
            </p>
          </div>
          {/* Decorative circles */}
          <div className="absolute -right-10 -top-10 w-48 h-48 rounded-full bg-white/5" />
          <div className="absolute -right-4 top-8 w-32 h-32 rounded-full bg-white/5" />
          <div className="absolute right-24 -bottom-8 w-24 h-24 rounded-full bg-white/5" />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {STAT_DEFS.map(s => (
            <StatCard key={s.key} label={s.label} value={stats[s.key]}
              icon={s.icon} colorCls={s.colorCls} bgCls={s.bgCls} />
          ))}
        </div>

        {/* Cases section */}
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-4">
            <h2 className="font-bold text-slate-800">My Cases</h2>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search cases…"
                className="input pl-9 py-2 text-sm w-60"
              />
              {search && (
                <button
                  onClick={() => setSearch('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400
                             hover:text-slate-600"
                >
                  <X size={13} />
                </button>
              )}
            </div>
          </div>

          {loading && (
            <div className="flex justify-center py-20">
              <Loader2 size={28} className="animate-spin text-indigo-500" />
            </div>
          )}

          {!loading && filtered.length === 0 && (
            <div className="flex flex-col items-center py-24 text-slate-400 gap-4">
              <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center">
                <Scale size={28} className="text-slate-300" />
              </div>
              <div className="text-center">
                <p className="font-semibold text-slate-600">
                  {search ? 'No matching cases' : 'No cases yet'}
                </p>
                <p className="text-sm text-slate-400 mt-1">
                  {search ? 'Try a different search term' : 'Create your first case to get started'}
                </p>
              </div>
              {!search && (
                <button onClick={() => setShowNew(true)} className="btn-primary mt-2">
                  <Plus size={14} /> Create First Case
                </button>
              )}
            </div>
          )}

          {!loading && filtered.length > 0 && (
            <>
              <p className="text-xs text-slate-400">
                {filtered.length} case{filtered.length !== 1 ? 's' : ''}
                {search && ` matching "${search}"`}
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filtered.map(c => (
                  <Link key={c.id} to={`/case/${c.id}`} className="block">
                    <CaseCard caseData={c} />
                  </Link>
                ))}
              </div>
            </>
          )}
        </div>
      </main>

      {showNew && (
        <NewCaseModal
          onClose={() => setShowNew(false)}
          onCreated={(c) => { setCases(prev => [c, ...prev]); }}
        />
      )}
    </div>
  );
}
