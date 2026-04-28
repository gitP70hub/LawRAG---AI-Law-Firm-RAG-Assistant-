import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Scale, MessageSquare, FileText, Clock,
  Plus, Search, Loader2, X, AlertCircle,
  ChevronRight, Sparkles, FolderOpen, Upload,
  CheckCircle2, ArrowRight, Shield,
} from 'lucide-react';
import { getCases, createCase } from '../api/client';

/* ─── Status config ─────────────────────────────────────── */
const STATUS_CFG = {
  open:      { label: 'Active',    cls: 'bg-emerald-100 text-emerald-700' },
  in_review: { label: 'In Review', cls: 'bg-amber-100  text-amber-700'   },
  closed:    { label: 'Closed',    cls: 'bg-slate-100  text-slate-500'   },
  archived:  { label: 'Archived',  cls: 'bg-slate-100  text-slate-400'   },
};

const formatDate = (iso) => iso
  ? new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
  : '—';

/* ─── Welcome Screen (shown when no matters exist yet) ──── */
const WelcomeScreen = ({ onStart }) => (
  <div className="flex flex-col items-center text-center py-8 px-4 max-w-xl mx-auto">
    {/* Animated icon */}
    <div className="relative mb-6">
      <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500 to-violet-600
                      flex items-center justify-center shadow-xl shadow-indigo-200">
        <Scale size={36} className="text-white" />
      </div>
      <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-emerald-400
                      flex items-center justify-center shadow-sm animate-bounce">
        <Sparkles size={12} className="text-white" />
      </div>
    </div>

    <h2 className="text-2xl font-bold text-slate-900 mb-2">Welcome to LawRAG</h2>
    <p className="text-slate-500 text-sm leading-relaxed max-w-sm">
      Your personal AI legal assistant. Upload your legal documents and get clear,
      plain-English answers — no lawyer jargon.
    </p>

    {/* Steps */}
    <div className="mt-8 w-full space-y-3">
      {[
        {
          icon: FolderOpen,
          color: 'bg-indigo-100 text-indigo-600',
          title: 'Create a Matter',
          desc: 'Give your legal issue a name — e.g. "Property dispute with neighbour"',
        },
        {
          icon: Upload,
          color: 'bg-violet-100 text-violet-600',
          title: 'Upload Your Documents',
          desc: 'Add any PDF — court notices, contracts, agreements, or FIR copies',
        },
        {
          icon: MessageSquare,
          color: 'bg-emerald-100 text-emerald-600',
          title: 'Ask Questions in Plain English',
          desc: 'Ask anything. AI reads your documents and explains them simply',
        },
      ].map(({ icon: Icon, color, title, desc }, i) => (
        <div key={i} className="flex items-start gap-4 p-4 bg-white rounded-2xl border border-slate-200 text-left">
          <div className={`w-10 h-10 rounded-xl ${color} flex items-center justify-center flex-shrink-0 mt-0.5`}>
            <Icon size={18} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold text-slate-400">STEP {i + 1}</span>
            </div>
            <p className="font-semibold text-slate-800 text-sm">{title}</p>
            <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{desc}</p>
          </div>
        </div>
      ))}
    </div>

    {/* Privacy note */}
    <div className="mt-5 flex items-center gap-2 text-xs text-slate-400">
      <Shield size={12} />
      <span>Your documents are processed securely and never shared.</span>
    </div>

    <button
      onClick={onStart}
      className="mt-6 btn-primary px-8 py-3 text-sm shadow-lg shadow-indigo-200"
    >
      <Plus size={15} />
      Create My First Matter
    </button>
  </div>
);

/* ─── New Matter Modal ──────────────────────────────────── */
const NewMatterModal = ({ onClose, onCreated }) => {
  const [form, setForm]     = useState({ title: '', description: '', client_name: '', status: 'open' });
  const [saving, setSaving] = useState(false);
  const [err, setErr]       = useState(null);
  const set = (k) => (e) => setForm(f => ({ ...f, [k]: e.target.value }));

  const save = async () => {
    if (!form.title.trim() || !form.client_name.trim()) {
      setErr('Matter title and your name are required.'); return;
    }
    setSaving(true); setErr(null);
    try {
      const { data } = await createCase(form);
      onCreated(data); onClose();
    } catch (e) { setErr(e.message || 'Failed to create matter.'); }
    finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md animate-scale-in">
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700
                            flex items-center justify-center shadow-sm">
              <Scale size={16} className="text-white" />
            </div>
            <div>
              <h2 className="font-bold text-slate-900">New Matter</h2>
              <p className="text-[11px] text-slate-400">Describe your legal issue</p>
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost p-2 rounded-xl"><X size={16} /></button>
        </div>

        <div className="p-6 space-y-4">
          {err && (
            <div className="flex items-center gap-2.5 p-3 rounded-xl border border-red-200 bg-red-50 text-sm text-red-700">
              <AlertCircle size={14} className="flex-shrink-0" /> {err}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              What is your legal issue? *
            </label>
            <input value={form.title} onChange={set('title')} className="input"
              placeholder="e.g. Property dispute with neighbour" />
            <p className="text-[11px] text-slate-400 mt-1">Give it a short, clear title</p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">Your Name *</label>
            <input value={form.client_name} onChange={set('client_name')} className="input"
              placeholder="e.g. Ravi Sharma" />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              More Details <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <textarea value={form.description} onChange={set('description')}
              className="input resize-none" rows={3}
              placeholder="Briefly describe what happened and what help you need…" />
          </div>
        </div>

        <div className="flex justify-end gap-2 px-6 pb-6">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={save} disabled={saving} className="btn-primary">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
            Create Matter
          </button>
        </div>
      </div>
    </div>
  );
};

/* ─── Matter Card ───────────────────────────────────────── */
const MatterCard = ({ c }) => {
  const sc = STATUS_CFG[c.status] || STATUS_CFG.open;
  const initials = (c.client_name || '?').split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase();

  return (
    <Link to={`/case/${c.id}`}
      className="group flex items-center gap-4 p-4 bg-white rounded-2xl border border-slate-200
                 hover:border-indigo-300 hover:shadow-md transition-all duration-200 cursor-pointer">
      <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-700
                      flex items-center justify-center flex-shrink-0 shadow-sm">
        <span className="text-sm font-bold text-white">{initials}</span>
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="font-semibold text-slate-900 text-sm truncate group-hover:text-indigo-700 transition-colors">
            {c.title}
          </p>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${sc.cls}`}>
            {sc.label}
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-0.5 truncate">{c.client_name}</p>
        <p className="text-[11px] text-slate-400 mt-1">{formatDate(c.created_at)}</p>
      </div>
      <ChevronRight size={16} className="text-slate-300 group-hover:text-indigo-500 flex-shrink-0 transition-colors" />
    </Link>
  );
};

/* ─── Main Dashboard ────────────────────────────────────── */
export default function Dashboard() {
  const [matters,  setMatters]  = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [search,   setSearch]   = useState('');
  const [showNew,  setShowNew]  = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await getCases({ limit: 100 });
      setMatters(data.items || []);
    } catch { setMatters([]); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = matters.filter(c =>
    c.title.toLowerCase().includes(search.toLowerCase()) ||
    c.client_name.toLowerCase().includes(search.toLowerCase())
  );

  const hasMatters = !loading && matters.length > 0;

  return (
    <div className="min-h-screen bg-[#f5f6fa]">
      {/* ── Header ── */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-slate-200/80">
        <div className="max-w-4xl mx-auto px-5 h-[60px] flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700
                            flex items-center justify-center shadow-sm">
              <Scale size={16} className="text-white" />
            </div>
            <div>
              <span className="font-bold text-slate-900 text-[15px]">LawRAG</span>
              <span className="ml-2 text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
                AI Legal Assistant
              </span>
            </div>
          </div>
          {hasMatters && (
            <button onClick={() => setShowNew(true)} className="btn-primary text-sm py-2 px-4">
              <Plus size={14} /> New Matter
            </button>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-5 py-8">
        {/* ── Loading ── */}
        {loading && (
          <div className="flex justify-center py-32">
            <Loader2 size={28} className="animate-spin text-indigo-500" />
          </div>
        )}

        {/* ── WELCOME SCREEN — no matters yet ── */}
        {!loading && matters.length === 0 && (
          <WelcomeScreen onStart={() => setShowNew(true)} />
        )}

        {/* ── DASHBOARD — has matters ── */}
        {hasMatters && (
          <div className="space-y-6">
            {/* Mini hero strip */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-indigo-600
                            to-violet-600 px-6 py-5 text-white shadow-lg">
              <div className="relative z-10 flex items-center justify-between">
                <div>
                  <p className="text-indigo-200 text-xs font-medium mb-0.5">Welcome back</p>
                  <h1 className="text-lg font-bold">Your Legal Matters</h1>
                  <p className="text-indigo-200 text-xs mt-0.5">
                    {matters.length} matter{matters.length !== 1 ? 's' : ''} ·{' '}
                    {matters.filter(c => c.status === 'open').length} active
                  </p>
                </div>
                <div className="hidden sm:flex items-center gap-2">
                  <div className="flex items-center gap-1.5 bg-white/15 rounded-xl px-3 py-2 text-xs font-medium">
                    <CheckCircle2 size={13} className="text-emerald-300" />
                    AI Ready
                  </div>
                </div>
              </div>
              <div className="absolute -right-6 -top-6 w-36 h-36 rounded-full bg-white/5" />
              <div className="absolute right-16 -bottom-8 w-24 h-24 rounded-full bg-white/5" />
            </div>

            {/* Search + list */}
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-bold text-slate-800">My Matters</h2>
                <div className="relative">
                  <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input value={search} onChange={e => setSearch(e.target.value)}
                    placeholder="Search…" className="input pl-9 py-2 text-sm w-44" />
                  {search && (
                    <button onClick={() => setSearch('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600">
                      <X size={12} />
                    </button>
                  )}
                </div>
              </div>

              {filtered.length === 0 ? (
                <div className="flex flex-col items-center py-16 text-slate-400 gap-3">
                  <Search size={28} className="text-slate-300" />
                  <p className="text-sm text-slate-500">No matters match "{search}"</p>
                  <button onClick={() => setSearch('')} className="text-xs text-indigo-500 hover:underline">
                    Clear search
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  {filtered.map(c => <MatterCard key={c.id} c={c} />)}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {showNew && (
        <NewMatterModal
          onClose={() => setShowNew(false)}
          onCreated={(c) => { setMatters(prev => [c, ...prev]); }}
        />
      )}
    </div>
  );
}
