import { useState } from 'react';
import {
  FileSearch, Loader2, AlertCircle, ChevronDown, ChevronUp,
  Shield, AlertTriangle, CheckCircle2, MinusCircle,
} from 'lucide-react';
import { analyzeClauses, analyzeRawText } from '../api/client';

/* ─── Risk configuration ────────────────────────────────── */
const RISK = {
  high:   { badge: 'badge-high',   bar: 'bg-red-500',     label: 'High Risk',   dot: 'bg-red-500',     icon: <AlertTriangle size={12} /> },
  medium: { badge: 'badge-medium', bar: 'bg-amber-400',   label: 'Medium Risk', dot: 'bg-amber-400',   icon: <MinusCircle   size={12} /> },
  low:    { badge: 'badge-low',    bar: 'bg-emerald-500', label: 'Low Risk',    dot: 'bg-emerald-500', icon: <CheckCircle2  size={12} /> },
};

const REC = {
  remove:    { cls: 'bg-red-100 text-red-700 border-red-200',         label: 'Remove'    },
  negotiate: { cls: 'bg-amber-100 text-amber-700 border-amber-200',   label: 'Negotiate' },
  keep:      { cls: 'bg-emerald-100 text-emerald-700 border-emerald-200', label: 'Keep'  },
};

/* ─── Stat card ─────────────────────────────────────────── */
const Stat = ({ label, value, cls }) => (
  <div className={`rounded-2xl border p-3.5 text-center ${cls}`}>
    <p className="text-2xl font-black leading-none">{value}</p>
    <p className="text-[10px] font-semibold uppercase tracking-wide mt-1 opacity-70">{label}</p>
  </div>
);

/* ─── Clause row ────────────────────────────────────────── */
const ClauseRow = ({ clause }) => {
  const [exp, setExp] = useState(false);
  const risk = RISK[clause.risk_level] || RISK.medium;
  const rec  = REC[clause.recommendation] || REC.negotiate;

  return (
    <>
      <tr
        className="border-b border-slate-100 hover:bg-slate-50/70 cursor-pointer
                   transition-colors duration-100 group"
        onClick={() => setExp(e => !e)}
      >
        <td className="px-4 py-3 text-xs font-mono text-slate-400">{clause.clause_number}</td>
        <td className="px-4 py-3">
          <p className="text-sm font-medium text-slate-800 leading-snug">
            {clause.clause_heading || clause.clause_type_label}
          </p>
          <p className="text-[11px] text-slate-400 mt-0.5">{clause.clause_type_label}</p>
        </td>
        <td className="px-4 py-3">
          <span className={`${risk.badge} flex items-center gap-1 w-fit`}>
            {risk.icon} {risk.label}
          </span>
        </td>
        <td className="px-4 py-3">
          <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border ${rec.cls}`}>
            {rec.label}
          </span>
        </td>
        <td className="px-4 py-3 text-slate-300 group-hover:text-slate-500 transition-colors">
          {exp ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
        </td>
      </tr>

      {exp && (
        <tr className="bg-slate-50/60 border-b border-slate-100">
          <td colSpan={5} className="px-4 py-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-fade-in">
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Original Clause Text
                </p>
                <p className="text-xs text-slate-700 italic bg-white border border-slate-200
                              rounded-xl p-3 leading-relaxed">
                  "{clause.original_text}"
                </p>
              </div>
              <div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                  Plain English
                </p>
                <p className="text-xs text-slate-700 bg-white border border-slate-200
                              rounded-xl p-3 leading-relaxed">
                  {clause.plain_english}
                </p>
              </div>
              {clause.risk_reason && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                    Why It's Risky
                  </p>
                  <p className="text-xs text-slate-700 leading-relaxed">{clause.risk_reason}</p>
                </div>
              )}
              {clause.recommendation_note && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-2">
                    Recommendation
                  </p>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {clause.recommendation_note}
                  </p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
};

/* ─── Main ClauseAnalyzer ───────────────────────────────── */
export default function ClauseAnalyzer({ caseId, documents = [] }) {
  const [mode,     setMode]     = useState('document');
  const [docName,  setDocName]  = useState('');
  const [rawText,  setRawText]  = useState('');
  const [analysis, setAnalysis] = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);

  const analyze = async () => {
    if (loading) return;
    setLoading(true); setError(null); setAnalysis(null);
    try {
      let data;
      if (mode === 'document') {
        ({ data } = await analyzeClauses({ case_id: caseId, document_name: docName }));
      } else {
        ({ data } = await analyzeRawText({ document_text: rawText, document_name: 'Pasted Contract' }));
      }
      setAnalysis(data);
    } catch (err) {
      setError(err.message || 'Analysis failed. Please try again.');
    } finally { setLoading(false); }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
          <Shield size={16} className="text-indigo-600" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-800 text-sm">Clause Analyzer</h3>
          <p className="text-[11px] text-slate-400">AI-powered contract risk assessment</p>
        </div>
      </div>

      {/* Mode tabs */}
      <div className="flex bg-slate-100 rounded-xl p-1 gap-0.5 w-fit">
        {[
          { id: 'document', label: '📄 Case Document' },
          { id: 'raw',      label: '📋 Paste Text'    },
        ].map(m => (
          <button
            key={m.id}
            onClick={() => setMode(m.id)}
            className={[
              'px-4 py-1.5 rounded-xl text-sm font-medium transition-all duration-150',
              mode === m.id
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700',
            ].join(' ')}
          >
            {m.label}
          </button>
        ))}
      </div>

      {/* Input controls */}
      {mode === 'document' ? (
        <div className="flex gap-2">
          <select
            value={docName}
            onChange={e => setDocName(e.target.value)}
            className="input flex-1"
            disabled={!caseId || documents.length === 0}
          >
            <option value="">
              {documents.length === 0 ? 'No documents uploaded' : 'Select a document…'}
            </option>
            {documents.map(d => (
              <option key={d.id} value={d.filename}>{d.filename}</option>
            ))}
          </select>
          <button
            onClick={analyze}
            disabled={loading || !caseId || !docName}
            className="btn-primary"
          >
            {loading ? <Loader2 size={14} className="animate-spin" /> : <FileSearch size={14} />}
            Analyze
          </button>
        </div>
      ) : (
        <div className="space-y-2">
          <textarea
            value={rawText}
            onChange={e => setRawText(e.target.value)}
            placeholder="Paste contract text here (minimum 50 characters)…"
            rows={7}
            className="input resize-y leading-relaxed"
          />
          <div className="flex items-center justify-between">
            <p className="text-[11px] text-slate-400">{rawText.length.toLocaleString()} chars</p>
            <button
              onClick={analyze}
              disabled={loading || rawText.trim().length < 50}
              className="btn-primary"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <FileSearch size={14} />}
              Analyze Clauses
            </button>
          </div>
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
              <Shield size={12} className="text-indigo-500" />
            </div>
          </div>
          <p className="text-sm text-slate-500">Analysing contract clauses…</p>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-red-50 border border-red-200">
          <AlertCircle size={15} className="text-red-500 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Results */}
      {analysis && !loading && (
        <div className="space-y-5 animate-fade-in">
          {/* Summary stats */}
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-2.5">
            <Stat label="Total"    value={analysis.total_clauses}    cls="border-slate-200 text-slate-700" />
            <Stat label="High"     value={analysis.high_risk_count}  cls="border-red-200 bg-red-50 text-red-700" />
            <Stat label="Medium"   value={analysis.medium_risk_count} cls="border-amber-200 bg-amber-50 text-amber-700" />
            <Stat label="Low"      value={analysis.low_risk_count}   cls="border-emerald-200 bg-emerald-50 text-emerald-700" />
            <Stat label="Remove"   value={analysis.remove_count}     cls="border-red-100 bg-red-50 text-red-600" />
            <Stat label="Negotiate" value={analysis.negotiate_count} cls="border-amber-100 bg-amber-50 text-amber-600" />
          </div>

          {/* Risk bar chart */}
          <div className="bg-white rounded-2xl border border-slate-200 p-4">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">
              Risk Distribution
            </p>
            <div className="flex h-2.5 rounded-full overflow-hidden gap-px">
              {analysis.high_risk_count > 0 && (
                <div
                  className="bg-red-500 transition-all"
                  style={{ width: `${(analysis.high_risk_count / analysis.total_clauses) * 100}%` }}
                  title={`High: ${analysis.high_risk_count}`}
                />
              )}
              {analysis.medium_risk_count > 0 && (
                <div
                  className="bg-amber-400 transition-all"
                  style={{ width: `${(analysis.medium_risk_count / analysis.total_clauses) * 100}%` }}
                  title={`Medium: ${analysis.medium_risk_count}`}
                />
              )}
              {analysis.low_risk_count > 0 && (
                <div
                  className="bg-emerald-500 transition-all"
                  style={{ width: `${(analysis.low_risk_count / analysis.total_clauses) * 100}%` }}
                  title={`Low: ${analysis.low_risk_count}`}
                />
              )}
            </div>
            <div className="flex gap-4 mt-2">
              {[
                { label: 'High Risk',   color: 'bg-red-500'     },
                { label: 'Medium Risk', color: 'bg-amber-400'   },
                { label: 'Low Risk',    color: 'bg-emerald-500' },
              ].map(l => (
                <div key={l.label} className="flex items-center gap-1.5">
                  <div className={`w-2 h-2 rounded-full ${l.color}`} />
                  <span className="text-[10px] text-slate-500">{l.label}</span>
                </div>
              ))}
            </div>
          </div>

          {analysis.truncated && (
            <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-amber-50
                            border border-amber-200 text-[11px] text-amber-700">
              <AlertTriangle size={13} />
              Document was truncated to 60,000 characters for analysis.
            </div>
          )}

          {/* Clauses table */}
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="bg-slate-50/80 border-b border-slate-200">
                    {['#', 'Clause', 'Risk', 'Action', ''].map((h, i) => (
                      <th key={i} className="px-4 py-3 text-[10px] font-bold text-slate-400
                                             uppercase tracking-widest whitespace-nowrap">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {analysis.clauses.map(c => <ClauseRow key={c.clause_number} clause={c} />)}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
