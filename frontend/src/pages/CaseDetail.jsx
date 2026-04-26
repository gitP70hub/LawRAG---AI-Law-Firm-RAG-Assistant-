import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Scale, MessageSquare, FileText, Clock,
  Shield, Search, Loader2, Trash2, CheckCircle,
  AlertCircle, UploadCloud, Info,
} from 'lucide-react';
import ChatWindow     from '../components/ChatWindow';
import DocumentUpload from '../components/DocumentUpload';
import CaseTimeline   from '../components/CaseTimeline';
import PrecedentFinder from '../components/PrecedentFinder';
import ClauseAnalyzer  from '../components/ClauseAnalyzer';
import { getCase, getDocuments, deleteDocument } from '../api/client';

/* ─── Tab configuration ─────────────────────────────────── */
const TABS = [
  { id: 'chat',      label: 'AI Chat',    icon: MessageSquare, desc: 'RAG-powered Q&A' },
  { id: 'documents', label: 'Documents',  icon: FileText,      desc: 'Upload & manage'  },
  { id: 'timeline',  label: 'Timeline',   icon: Clock,         desc: 'AI-generated'     },
  { id: 'precedent', label: 'Precedents', icon: Search,        desc: 'Case law search'  },
  { id: 'clauses',   label: 'Clauses',    icon: Shield,        desc: 'Risk analysis'    },
];

const STATUS_CFG = {
  open:      { cls: 'bg-indigo-50 text-indigo-700 border-indigo-200', label: 'Open'      },
  in_review: { cls: 'bg-amber-50  text-amber-700  border-amber-200',  label: 'In Review' },
  closed:    { cls: 'bg-slate-100 text-slate-500  border-slate-200',  label: 'Closed'    },
  archived:  { cls: 'bg-slate-100 text-slate-400  border-slate-200',  label: 'Archived'  },
};

const formatBytes = (b) => {
  if (!b) return '—';
  const k = 1024, s = ['B', 'KB', 'MB'];
  const i = Math.floor(Math.log(b) / Math.log(k));
  return `${(b / Math.pow(k, i)).toFixed(1)} ${s[i]}`;
};

/* ─── Main CaseDetail ───────────────────────────────────── */
export default function CaseDetail() {
  const { id } = useParams();
  const [caseData,  setCaseData]  = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading,   setLoading]   = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const [deleteId,  setDeleteId]  = useState(null);

  const loadCase = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [{ data: c }, docsRes] = await Promise.all([
        getCase(id),
        getDocuments(id).catch(() => ({ data: { items: [] } })),
      ]);
      setCaseData(c);
      setDocuments(docsRes.data?.items || []);
    } catch { setCaseData(null); }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => { loadCase(); }, [loadCase]);

  const loadDocs = useCallback(async () => {
    try {
      const { data } = await getDocuments(id);
      setDocuments(data.items || []);
    } catch {}
  }, [id]);

  const handleDeleteDoc = async (docId) => {
    if (!window.confirm('Delete this document and remove it from the vector index?')) return;
    setDeleteId(docId);
    try {
      await deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
    } catch {}
    finally { setDeleteId(null); }
  };

  /* Loading skeleton */
  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative w-14 h-14">
            <div className="absolute inset-0 rounded-full border-4 border-indigo-100" />
            <div className="absolute inset-0 rounded-full border-4 border-indigo-500
                            border-t-transparent animate-spin" />
          </div>
          <p className="text-slate-500 text-sm">Loading case…</p>
        </div>
      </div>
    );
  }

  /* 404 */
  if (!caseData) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <Scale size={28} className="text-slate-400" />
          </div>
          <p className="font-semibold text-slate-700">Case not found</p>
          <p className="text-sm text-slate-400 mt-1 mb-5">
            This case may have been deleted or the ID is invalid.
          </p>
          <Link to="/" className="btn-primary">← Back to Dashboard</Link>
        </div>
      </div>
    );
  }

  const sc = STATUS_CFG[caseData.status] || STATUS_CFG.open;

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      {/* ── Sticky header ── */}
      <header className="sticky top-0 z-30 glass border-b border-slate-200/60">
        {/* Case info row */}
        <div className="max-w-7xl mx-auto px-6 h-[60px] flex items-center gap-4">
          <Link to="/" className="btn-ghost p-2 rounded-xl flex-shrink-0">
            <ArrowLeft size={17} />
          </Link>

          <div className="w-px h-6 bg-slate-200 flex-shrink-0" />

          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700
                          flex items-center justify-center flex-shrink-0 shadow-sm">
            <Scale size={16} className="text-white" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-bold text-slate-900 text-[15px] truncate">{caseData.title}</h1>
              <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${sc.cls}`}>
                {sc.label}
              </span>
            </div>
            <p className="text-xs text-slate-500 truncate">
              {caseData.client_name}
              {' · '}
              <span className={documents.length > 0 ? 'text-emerald-600' : 'text-slate-400'}>
                {documents.length} document{documents.length !== 1 ? 's' : ''}
              </span>
              {caseData.created_at && (
                <> · Created {new Date(caseData.created_at).toLocaleDateString('en-IN', {
                  day: 'numeric', month: 'short', year: 'numeric',
                })}</>
              )}
            </p>
          </div>

          {/* Case ID */}
          <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-lg
                          bg-slate-100 text-[10px] font-mono text-slate-400 flex-shrink-0">
            <Info size={10} />
            {id.slice(0, 8)}…
          </div>
        </div>

        {/* Tab bar */}
        <div className="max-w-7xl mx-auto px-6 flex gap-0 border-t border-slate-100
                        overflow-x-auto">
          {TABS.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab-btn ${activeTab === tab.id ? 'active' : 'inactive'}`}
              >
                <Icon size={14} />
                {tab.label}
                {tab.id === 'documents' && documents.length > 0 && (
                  <span className="ml-1 text-[10px] bg-indigo-100 text-indigo-600
                                   rounded-full px-1.5 py-0.5 font-bold">
                    {documents.length}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </header>

      {/* ── Tab content ── */}
      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">

        {/* CHAT */}
        {activeTab === 'chat' && (
          <div className="h-[calc(100vh-145px)] min-h-[500px]">
            {documents.length === 0 && (
              <div className="mb-4 flex items-center gap-3 px-4 py-3 rounded-2xl bg-amber-50
                              border border-amber-200 text-sm text-amber-700">
                <AlertCircle size={15} className="flex-shrink-0" />
                <span>
                  No documents uploaded yet —{' '}
                  <button
                    onClick={() => setActiveTab('documents')}
                    className="underline underline-offset-2 font-medium hover:text-amber-900"
                  >
                    upload PDFs first
                  </button>{' '}
                  for RAG-powered answers.
                </span>
              </div>
            )}
            <ChatWindow caseId={id} />
          </div>
        )}

        {/* DOCUMENTS */}
        {activeTab === 'documents' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Upload panel */}
            <div className="card p-6">
              <h2 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
                <UploadCloud size={16} className="text-indigo-500" />
                Upload Documents
              </h2>
              <p className="text-xs text-slate-400 mb-4">
                Uploaded PDFs are indexed into the RAG vector database automatically.
              </p>
              <DocumentUpload caseId={id} onUploadSuccess={loadDocs} />
            </div>

            {/* Document list */}
            <div className="card p-6">
              <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
                <FileText size={16} className="text-slate-500" />
                Case Documents
                <span className="text-xs text-slate-400 font-normal ml-auto">
                  {documents.length} file{documents.length !== 1 ? 's' : ''}
                </span>
              </h2>

              {documents.length === 0 ? (
                <div className="flex flex-col items-center py-14 text-slate-400 gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center">
                    <FileText size={20} className="text-slate-300" />
                  </div>
                  <p className="text-sm text-slate-500">No documents uploaded yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map(doc => (
                    <div
                      key={doc.id}
                      className="flex items-center gap-3 p-3 rounded-xl border border-slate-200
                                 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all group"
                    >
                      {/* PDF icon */}
                      <div className="w-9 h-9 rounded-xl bg-red-100 border border-red-200
                                      flex items-center justify-center flex-shrink-0">
                        <FileText size={15} className="text-red-600" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">
                          {doc.filename}
                        </p>
                        <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                          <span>{formatBytes(doc.file_size)}</span>
                          <span>·</span>
                          <span className={`flex items-center gap-1 font-medium
                            ${doc.is_indexed ? 'text-emerald-600' : 'text-amber-600'}`}>
                            {doc.is_indexed
                              ? <><CheckCircle size={10} /> Indexed</>
                              : <>⏳ Processing…</>}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeleteDoc(doc.id)}
                        disabled={deleteId === doc.id}
                        className="opacity-0 group-hover:opacity-100 transition-opacity
                                   btn-ghost text-red-400 hover:text-red-600 p-1.5"
                      >
                        {deleteId === doc.id
                          ? <Loader2 size={14} className="animate-spin" />
                          : <Trash2 size={14} />}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* TIMELINE */}
        {activeTab === 'timeline' && (
          <div className="card p-6">
            <CaseTimeline caseId={id} />
          </div>
        )}

        {/* PRECEDENTS */}
        {activeTab === 'precedent' && (
          <div className="card p-6">
            <PrecedentFinder />
          </div>
        )}

        {/* CLAUSES */}
        {activeTab === 'clauses' && (
          <div className="card p-6">
            <ClauseAnalyzer caseId={id} documents={documents} />
          </div>
        )}
      </main>
    </div>
  );
}
