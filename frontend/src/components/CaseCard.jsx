import { Calendar, User, ArrowUpRight, Dot } from 'lucide-react';

const STATUS_MAP = {
  open:      { badge: 'badge-open',      label: 'Open',      dot: 'bg-indigo-500' },
  in_review: { badge: 'badge-in_review', label: 'In Review', dot: 'bg-amber-500'  },
  closed:    { badge: 'badge-closed',    label: 'Closed',    dot: 'bg-slate-400'  },
  archived:  { badge: 'badge-archived',  label: 'Archived',  dot: 'bg-slate-300'  },
};

const STATUS_ACCENT = {
  open:      'from-indigo-500 to-indigo-400',
  in_review: 'from-amber-500  to-amber-400',
  closed:    'from-slate-400  to-slate-300',
  archived:  'from-slate-300  to-slate-200',
};

export default function CaseCard({ caseData, onClick, active = false }) {
  const { badge, label, dot } = STATUS_MAP[caseData.status] || STATUS_MAP.open;
  const accent = STATUS_ACCENT[caseData.status] || STATUS_ACCENT.open;

  const created = caseData.created_at
    ? new Date(caseData.created_at).toLocaleDateString('en-IN', {
        day: 'numeric', month: 'short', year: 'numeric',
      })
    : '—';

  const initials = (caseData.client_name || '?')
    .split(' ')
    .slice(0, 2)
    .map(w => w[0])
    .join('')
    .toUpperCase();

  return (
    <div
      onClick={() => onClick?.(caseData)}
      className={[
        'group relative cursor-pointer rounded-2xl border bg-white overflow-hidden',
        'transition-all duration-200 select-none',
        active
          ? 'border-indigo-400 shadow-glow shadow-indigo-100'
          : 'border-slate-200/80 hover:border-slate-300 hover:shadow-card-md',
      ].join(' ')}
    >
      {/* Accent gradient bar */}
      <div className={`h-0.5 w-full bg-gradient-to-r ${accent} opacity-80`} />

      <div className="p-4">
        {/* Title row */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <h3 className={[
            'font-semibold text-sm leading-snug line-clamp-2 flex-1',
            active ? 'text-indigo-800' : 'text-slate-800 group-hover:text-indigo-700',
            'transition-colors duration-150',
          ].join(' ')}>
            {caseData.title}
          </h3>
          <ArrowUpRight
            size={14}
            className={[
              'flex-shrink-0 mt-0.5 transition-all duration-200',
              'opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 group-hover:-translate-y-0.5',
              active ? 'opacity-100 text-indigo-500' : 'text-slate-400',
            ].join(' ')}
          />
        </div>

        {/* Status + client */}
        <div className="flex items-center justify-between gap-2 mb-3">
          <span className={badge}><span className={`w-1.5 h-1.5 rounded-full ${dot} inline-block`} />{label}</span>
        </div>

        {/* Footer meta */}
        <div className="flex items-center gap-3 pt-3 border-t border-slate-100">
          {/* Avatar */}
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-400 to-indigo-600 flex items-center justify-center flex-shrink-0">
            <span className="text-[9px] font-bold text-white leading-none">{initials}</span>
          </div>
          <span className="text-[11px] text-slate-500 font-medium truncate flex-1">{caseData.client_name}</span>
          <span className="text-[11px] text-slate-400 flex items-center gap-1 flex-shrink-0">
            <Calendar size={10} />
            {created}
          </span>
        </div>

        {caseData.description && (
          <p className="text-[11px] text-slate-400 mt-2.5 line-clamp-2 leading-relaxed">
            {caseData.description}
          </p>
        )}
      </div>
    </div>
  );
}
