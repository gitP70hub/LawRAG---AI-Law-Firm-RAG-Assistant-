import { useState } from 'react';
import { Search, Scale, Star, Loader2, BookOpen, AlertCircle, ExternalLink, TrendingUp } from 'lucide-react';
import { findPrecedents } from '../api/client';

/* ─── Relevance helpers ─────────────────────────────────── */
const scoreColor = (score) => {
  if (score >= 0.75) return { bg: 'bg-emerald-100', text: 'text-emerald-700', bar: 'bg-emerald-500' };
  if (score >= 0.50) return { bg: 'bg-amber-100',   text: 'text-amber-700',   bar: 'bg-amber-500'   };
  return                     { bg: 'bg-slate-100',   text: 'text-slate-600',   bar: 'bg-slate-400'   };
};

/* ─── Single precedent card ─────────────────────────────── */
const PrecedentCard = ({ p, index }) => {
  const { bg, text, bar } = scoreColor(p.relevance_score);
  const pct = (p.relevance_score * 100).toFixed(0);
  const stars = Math.round(p.relevance_score * 5);

  return (
    <div
      className="card-hover p-5 animate-slide-up"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Top row */}
      <div className="flex items-start gap-3 mb-4">
        {/* Court avatar */}
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-100 to-indigo-50
                        border border-indigo-200 flex items-center justify-center flex-shrink-0">
          <Scale size={15} className="text-indigo-600" />
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-slate-800 text-sm leading-snug">{p.case_name}</h4>
          <p className="text-[11px] text-slate-500 mt-0.5">{p.court} · {p.year}</p>
          {p.citation && (
            <p className="text-[11px] font-mono text-indigo-600 mt-0.5 truncate">{p.citation}</p>
          )}
        </div>

        {/* Relevance badge */}
        <div className={`flex-shrink-0 flex flex-col items-center gap-1 px-3 py-1.5
                         rounded-xl border ${bg} border-current/20`}>
          <span className={`text-base font-black leading-none ${text}`}>{pct}%</span>
          <span className={`text-[9px] font-bold uppercase tracking-widest ${text}`}>match</span>
        </div>
      </div>

      {/* Star rating */}
      <div className="flex items-center gap-1 mb-3">
        {[1,2,3,4,5].map(s => (
          <Star
            key={s}
            size={11}
            className={s <= stars ? 'text-amber-400 fill-amber-400' : 'text-slate-200 fill-slate-200'}
          />
        ))}
        <span className="text-[10px] text-slate-400 ml-1.5">{p.relevance_score.toFixed(2)}</span>
      </div>

      {/* Relevance bar */}
      <div className="w-full h-1 bg-slate-100 rounded-full mb-4 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Summary */}
      <p className="text-xs text-slate-600 leading-relaxed mb-4 line-clamp-3">{p.summary}</p>

      {/* Key ruling */}
      <div className="bg-slate-50 rounded-xl border border-slate-200/80 px-3 py-2.5 mb-3">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-1">Key Ruling</p>
        <p className="text-xs text-slate-700 leading-relaxed">{p.key_ruling}</p>
      </div>

      {/* Relevance reason */}
      {p.relevance_reason && (
        <div className="flex items-start gap-2 px-3 py-2.5 bg-indigo-50 border border-indigo-100 rounded-xl">
          <TrendingUp size={12} className="text-indigo-500 flex-shrink-0 mt-0.5" />
          <p className="text-[11px] text-indigo-700 leading-relaxed">{p.relevance_reason}</p>
        </div>
      )}
    </div>
  );
};

/* ─── Example queries ───────────────────────────────────── */
const EXAMPLES = [
  'Employee terminated without notice period',
  'Property dispute adverse possession',
  'Breach of contract damages claim',
  'Cheque dishonour under Section 138',
];

/* ─── Main PrecedentFinder ──────────────────────────────── */
export default function PrecedentFinder() {
  const [query,    setQuery]    = useState('');
  const [topK,     setTopK]     = useState(5);
  const [results,  setResults]  = useState([]);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);
  const [searched, setSearched] = useState(false);

  const search = async (overrideQuery) => {
    const q = (overrideQuery ?? query).trim();
    if (!q || loading) return;
    if (overrideQuery) setQuery(overrideQuery);
    setLoading(true); setError(null); setSearched(true);
    try {
      const { data } = await findPrecedents({ legal_issue: q, top_k: topK });
      setResults(data.precedents || []);
    } catch (err) {
      setError(err.message || 'Search failed. Please try again.');
      setResults([]);
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-5">
      {/* Section header */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
          <Scale size={16} className="text-indigo-600" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-800 text-sm">Precedent Finder</h3>
          <p className="text-[11px] text-slate-400">Indian Supreme Court & High Court · AI-powered</p>
        </div>
      </div>

      {/* Search bar */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            placeholder="Describe your legal issue in plain English…"
            className="input pl-10 pr-3"
          />
        </div>
        <select
          value={topK}
          onChange={e => setTopK(Number(e.target.value))}
          className="input w-24 flex-shrink-0"
        >
          {[3,5,7,10].map(n => <option key={n} value={n}>Top {n}</option>)}
        </select>
        <button
          onClick={() => search()}
          disabled={loading || !query.trim()}
          className="btn-primary flex-shrink-0"
        >
          {loading ? <Loader2 size={14} className="animate-spin" /> : <Search size={14} />}
          Search
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2.5 p-3.5 rounded-2xl border border-red-200
                        bg-red-50 text-sm text-red-700">
          <AlertCircle size={15} className="flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center py-16 gap-4">
          <div className="relative w-12 h-12">
            <div className="absolute inset-0 rounded-full border-4 border-indigo-100" />
            <div className="absolute inset-0 rounded-full border-4 border-indigo-500
                            border-t-transparent animate-spin" />
            <div className="absolute inset-3 rounded-full bg-indigo-50 flex items-center justify-center">
              <Scale size={12} className="text-indigo-500" />
            </div>
          </div>
          <p className="text-sm text-slate-500">Searching Indian case law…</p>
        </div>
      )}

      {/* Empty searched state */}
      {!loading && searched && results.length === 0 && !error && (
        <div className="flex flex-col items-center py-14 gap-3">
          <BookOpen size={32} className="text-slate-300" />
          <p className="font-medium text-slate-500 text-sm">No matching precedents found</p>
          <p className="text-xs text-slate-400">Try rephrasing your legal issue</p>
        </div>
      )}

      {/* Initial state */}
      {!loading && !searched && (
        <div className="space-y-4">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
            Try an example
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                onClick={() => search(ex)}
                className="text-left text-xs px-4 py-3 rounded-xl bg-white border border-slate-200
                           text-slate-600 hover:border-indigo-300 hover:text-indigo-700
                           hover:bg-indigo-50 transition-all duration-150 leading-relaxed"
              >
                {ex}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-xs text-slate-500">
              <span className="font-bold text-slate-800">{results.length}</span>{' '}
              precedent{results.length !== 1 ? 's' : ''} found
            </p>
            <button onClick={() => search()} className="text-xs text-indigo-600 hover:underline">
              Re-search
            </button>
          </div>
          {results.map((p, i) => <PrecedentCard key={i} p={p} index={i} />)}
        </div>
      )}
    </div>
  );
}
