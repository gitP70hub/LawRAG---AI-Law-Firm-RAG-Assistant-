import { useState, useEffect, useCallback } from 'react';
import {
  Clock, RefreshCw, Trash2, ChevronDown, ChevronUp,
  Calendar, Zap, AlertCircle,
} from 'lucide-react';
import { getTimeline, clearTimeline } from '../api/client';

/* ─── Event type configuration ─────────────────────────── */
const EVENT_CFG = {
  contract:  { color: '#6366f1', bg: '#eef2ff', label: 'Contract',  icon: '📄' },
  payment:   { color: '#10b981', bg: '#ecfdf5', label: 'Payment',   icon: '💰' },
  notice:    { color: '#f59e0b', bg: '#fffbeb', label: 'Notice',    icon: '📬' },
  fir:       { color: '#ef4444', bg: '#fef2f2', label: 'FIR',       icon: '🚨' },
  arrest:    { color: '#dc2626', bg: '#fef2f2', label: 'Arrest',    icon: '⚖️' },
  filing:    { color: '#8b5cf6', bg: '#f5f3ff', label: 'Filing',    icon: '📁' },
  hearing:   { color: '#3b82f6', bg: '#eff6ff', label: 'Hearing',   icon: '🏛️' },
  order:     { color: '#64748b', bg: '#f8fafc', label: 'Order',     icon: '📜' },
  judgment:  { color: '#7c3aed', bg: '#f5f3ff', label: 'Judgment',  icon: '⚖️' },
  appeal:    { color: '#ea580c', bg: '#fff7ed', label: 'Appeal',    icon: '📋' },
  other:     { color: '#94a3b8', bg: '#f8fafc', label: 'Event',     icon: 'ℹ️'  },
};

/* ─── Single timeline event card ───────────────────────── */
const TimelineItem = ({ event, index, total }) => {
  const [expanded, setExpanded] = useState(false);
  const cfg   = EVENT_CFG[event.event_type] || EVENT_CFG.other;
  const isLast = index === total - 1;

  return (
    <div className="flex gap-0 animate-slide-up" style={{ animationDelay: `${index * 40}ms` }}>
      {/* Left: date column */}
      <div className="w-28 flex-shrink-0 text-right pr-5 pt-3">
        <p className="text-sm font-semibold text-slate-700 leading-tight">{event.date}</p>
        {event.date_precision && event.date_precision !== 'exact' && (
          <p className="text-[10px] text-slate-400 capitalize mt-0.5">
            {event.date_precision.replace('_', ' ')}
          </p>
        )}
      </div>

      {/* Centre: spine */}
      <div className="flex flex-col items-center flex-shrink-0 w-10">
        {/* dot */}
        <div
          className="w-4 h-4 rounded-full border-2 border-white shadow-md z-10 flex-shrink-0 mt-3"
          style={{ backgroundColor: cfg.color, boxShadow: `0 0 0 3px ${cfg.color}22` }}
        />
        {/* line */}
        {!isLast && (
          <div
            className="w-0.5 flex-1 min-h-[48px] mt-1 rounded-full opacity-30"
            style={{ backgroundColor: cfg.color }}
          />
        )}
      </div>

      {/* Right: event card */}
      <div className="flex-1 pb-6 min-w-0">
        <div
          className="rounded-2xl border overflow-hidden cursor-pointer transition-all duration-200
                     hover:shadow-card-md group"
          style={{ borderColor: cfg.color + '33', backgroundColor: cfg.bg }}
          onClick={() => setExpanded(e => !e)}
        >
          <div className="px-4 py-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2.5 flex-1 min-w-0">
                <span className="text-lg leading-none flex-shrink-0 mt-0.5">{event.icon || cfg.icon}</span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span
                      className="text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
                      style={{ color: cfg.color, backgroundColor: cfg.color + '22' }}
                    >
                      {cfg.label}
                    </span>
                  </div>
                  <p className="text-sm font-medium leading-snug" style={{ color: cfg.color }}>
                    {event.description}
                  </p>
                </div>
              </div>
              {(event.parties_involved?.length > 0 || event.legal_significance) && (
                <button
                  className="flex-shrink-0 opacity-50 group-hover:opacity-80 transition-opacity"
                  style={{ color: cfg.color }}
                >
                  {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                </button>
              )}
            </div>
          </div>

          {/* Expanded detail */}
          {expanded && (
            <div
              className="px-4 pt-3 pb-4 space-y-3 border-t animate-fade-in"
              style={{ borderColor: cfg.color + '22' }}
            >
              {event.parties_involved?.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest mb-1.5"
                     style={{ color: cfg.color + 'aa' }}>
                    Parties Involved
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {event.parties_involved.map((p, i) => (
                      <span
                        key={i}
                        className="text-xs px-2.5 py-1 rounded-full font-medium bg-white/70"
                        style={{ color: cfg.color }}
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {event.legal_significance && (
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-widest mb-1"
                     style={{ color: cfg.color + 'aa' }}>
                    Legal Significance
                  </p>
                  <p className="text-xs leading-relaxed text-slate-600">
                    {event.legal_significance}
                  </p>
                </div>
              )}

              {event.document_source?.filename && (
                <p className="text-[11px] text-slate-400 flex items-center gap-1">
                  📄 {event.document_source.filename}
                  {event.document_source.page_num && `, p.${event.document_source.page_num}`}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

/* ─── Main CaseTimeline ─────────────────────────────────── */
export default function CaseTimeline({ caseId }) {
  const [events,  setEvents]  = useState([]);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const [meta,    setMeta]    = useState(null);

  const load = useCallback(async (force = false) => {
    if (!caseId) return;
    setLoading(true); setError(null);
    try {
      const { data } = await getTimeline(caseId, force);
      setEvents(data.events || []);
      setMeta({
        generated_at: data.generated_at,
        cached: data.cached,
        total: data.total_events,
      });
    } catch (err) {
      setError(err.message || 'Failed to load timeline.');
    } finally { setLoading(false); }
  }, [caseId]);

  useEffect(() => { load(); }, [load]);

  const handleClear = async () => {
    if (!window.confirm('Invalidate cached timeline? Next load will re-generate.')) return;
    await clearTimeline(caseId).catch(() => {});
    setEvents([]); setMeta(null);
  };

  return (
    <div className="space-y-5">
      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-indigo-50 flex items-center justify-center">
            <Clock size={16} className="text-indigo-600" />
          </div>
          <div>
            <h3 className="font-semibold text-slate-800 text-sm">Case Timeline</h3>
            {meta && (
              <p className="text-[11px] text-slate-400">
                {meta.total} events · {meta.cached ? 'cached' : 'generated now'} ·{' '}
                {new Date(meta.generated_at).toLocaleDateString()}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => load(true)}
            disabled={loading}
            className="btn-secondary text-xs py-1.5"
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Regenerate
          </button>
          {events.length > 0 && (
            <button onClick={handleClear} className="btn-ghost text-red-400 hover:text-red-600 text-xs">
              <Trash2 size={12} /> Clear
            </button>
          )}
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="flex flex-col items-center py-20 gap-4">
          <div className="relative w-14 h-14">
            <div className="absolute inset-0 rounded-full border-4 border-indigo-100" />
            <div className="absolute inset-0 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
            <div className="absolute inset-3 rounded-full bg-indigo-50 flex items-center justify-center">
              <Zap size={14} className="text-indigo-500" />
            </div>
          </div>
          <div className="text-center">
            <p className="font-medium text-slate-700 text-sm">Generating Timeline</p>
            <p className="text-[11px] text-slate-400 mt-1">
              AI is analysing your documents — this can take 30–90 seconds
            </p>
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <div className="flex items-start gap-3 p-4 rounded-2xl bg-red-50 border border-red-200">
          <AlertCircle size={16} className="text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-800">Failed to load timeline</p>
            <p className="text-xs text-red-600 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && events.length === 0 && (
        <div className="flex flex-col items-center py-20 gap-3">
          <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center">
            <Calendar size={24} className="text-slate-400" />
          </div>
          <div className="text-center">
            <p className="font-medium text-slate-600 text-sm">No timeline generated yet</p>
            <p className="text-xs text-slate-400 mt-1">
              Upload documents first, then click Regenerate
            </p>
          </div>
        </div>
      )}

      {/* Timeline */}
      {!loading && events.length > 0 && (
        <div className="relative">
          {events.map((ev, i) => (
            <TimelineItem key={i} event={ev} index={i} total={events.length} />
          ))}
        </div>
      )}
    </div>
  );
}
