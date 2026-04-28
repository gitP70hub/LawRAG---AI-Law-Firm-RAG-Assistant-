import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft, Scale, MessageSquare, FileText, Clock,
  Loader2, Trash2, CheckCircle, AlertCircle, UploadCloud, Info,
} from 'lucide-react';
import ChatWindow     from '../components/ChatWindow';
import DocumentUpload from '../components/DocumentUpload';
import CaseTimeline   from '../components/CaseTimeline';
import { getCase, getDocuments, deleteDocument } from '../api/client';

/* ─── Tab config (3 simple tabs only) ───────────────────── */
const TABS = [
  { id: 'chat',      label: 'Ask AI',    icon: MessageSquare, desc: 'Ask questions'     },
  { id: 'documents', label: 'Documents', icon: FileText,      desc: 'Upload files'      },
  { id: 'timeline',  label: 'Timeline',  icon: Clock,         desc: 'Key events & dates'},
];

const STATUS_CFG = {
  open:      { cls: 'bg-emerald-100 text-emerald-700', label: 'Active'     },
  in_review: { cls: 'bg-amber-100  text-amber-700',   label: 'In Review'  },
  closed:    { cls: 'bg-slate-100  text-slate-500',   label: 'Closed'     },
  archived:  { cls: 'bg-slate-100  text-slate-400',   label: 'Archived'   },
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
      // Auto-switch to Timeline tab after a successful upload
      setTimeout(() => setActiveTab('timeline'), 800);
    } catch {}
  }, [id]);

  const handleDeleteDoc = async (docId) => {
    if (!window.confirm('Remove this document from the case?')) return;
    setDeleteId(docId);
    try {
      await deleteDocument(docId);
      setDocuments(prev => prev.filter(d => d.id !== docId));
    } catch {}
    finally { setDeleteId(null); }
  };

  /* Loading */
  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f6fa] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="relative w-12 h-12">
            <div className="absolute inset-0 rounded-full border-4 border-indigo-100" />
            <div className="absolute inset-0 rounded-full border-4 border-indigo-500 border-t-transparent animate-spin" />
          </div>
          <p className="text-slate-500 text-sm">Loading matter…</p>
        </div>
      </div>
    );
  }

  /* 404 */
  if (!caseData) {
    return (
      <div className="min-h-screen bg-[#f5f6fa] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-4">
            <Scale size={28} className="text-slate-400" />
          </div>
          <p className="font-semibold text-slate-700">Matter not found</p>
          <p className="text-sm text-slate-400 mt-1 mb-5">This matter may have been deleted.</p>
          <Link to="/" className="btn-primary">← Back to My Matters</Link>
        </div>
      </div>
    );
  }

  const sc = STATUS_CFG[caseData.status] || STATUS_CFG.open;

  return (
    <div className="min-h-screen bg-[#f5f6fa] flex flex-col">
      {/* ── Sticky header ── */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-slate-200/80">
        {/* Case info row */}
        <div className="max-w-5xl mx-auto px-5 h-[58px] flex items-center gap-3">
          <Link to="/" className="btn-ghost p-2 rounded-xl flex-shrink-0">
            <ArrowLeft size={16} />
          </Link>

          <div className="w-px h-5 bg-slate-200 flex-shrink-0" />

          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700
                          flex items-center justify-center flex-shrink-0 shadow-sm">
            <Scale size={14} className="text-white" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="font-bold text-slate-900 text-[14px] truncate">{caseData.title}</h1>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${sc.cls}`}>
                {sc.label}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 truncate">
              {caseData.client_name}
              {' · '}
              <span className={documents.length > 0 ? 'text-emerald-600' : 'text-slate-400'}>
                {documents.length} file{documents.length !== 1 ? 's' : ''} uploaded
              </span>
            </p>
          </div>
        </div>

        {/* Tab bar */}
        <div className="max-w-5xl mx-auto px-5 flex gap-0 border-t border-slate-100 overflow-x-auto">
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
      <main className="flex-1 max-w-5xl mx-auto w-full px-5 py-5">

        {/* CHAT */}
        {activeTab === 'chat' && (
          <div className="h-[calc(100vh-150px)] min-h-[500px] flex flex-col gap-3">
            {documents.length === 0 && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-2xl bg-amber-50
                              border border-amber-200 text-sm text-amber-700">
                <AlertCircle size={15} className="flex-shrink-0" />
                <span>
                  No documents uploaded yet —{' '}
                  <button
                    onClick={() => setActiveTab('documents')}
                    className="underline underline-offset-2 font-semibold hover:text-amber-900"
                  >
                    upload your PDF first
                  </button>{' '}
                  so AI can read and answer your questions.
                </span>
              </div>
            )}
            <div className="flex-1 min-h-0">
              <ChatWindow caseId={id} />
            </div>
          </div>
        )}

        {/* DOCUMENTS */}
        {activeTab === 'documents' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Upload panel */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <h2 className="font-semibold text-slate-800 mb-1 flex items-center gap-2 text-sm">
                <UploadCloud size={15} className="text-indigo-500" />
                Upload Your Documents
              </h2>
              <p className="text-xs text-slate-400 mb-4">
                Upload any PDF — court notice, contract, FIR, agreement. AI will read it automatically.
                After upload, you'll be taken to the Timeline view.
              </p>
              <DocumentUpload caseId={id} onUploadSuccess={loadDocs} />
            </div>

            {/* Document list */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
              <h2 className="font-semibold text-slate-800 mb-4 flex items-center gap-2 text-sm">
                <FileText size={15} className="text-slate-500" />
                Uploaded Files
                <span className="text-xs text-slate-400 font-normal ml-auto">
                  {documents.length} file{documents.length !== 1 ? 's' : ''}
                </span>
              </h2>

              {documents.length === 0 ? (
                <div className="flex flex-col items-center py-14 text-slate-400 gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center">
                    <FileText size={20} className="text-slate-300" />
                  </div>
                  <p className="text-sm text-slate-500">No files uploaded yet</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {documents.map(doc => (
                    <div
                      key={doc.id}
                      className="flex items-center gap-3 p-3 rounded-xl border border-slate-200
                                 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all group"
                    >
                      <div className="w-9 h-9 rounded-xl bg-red-50 border border-red-200
                                      flex items-center justify-center flex-shrink-0">
                        <FileText size={14} className="text-red-500" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-800 truncate">{doc.filename}</p>
                        <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                          <span>{formatBytes(doc.file_size)}</span>
                          <span>·</span>
                          <span className={`flex items-center gap-1 font-medium
                            ${doc.is_indexed ? 'text-emerald-600' : 'text-amber-600'}`}>
                            {doc.is_indexed
                              ? <><CheckCircle size={10} /> Ready</>
                              : <>⏳ Processing…</>}
                          </span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleDeleteDoc(doc.id)}
                        disabled={deleteId === doc.id}
                        className="opacity-0 group-hover:opacity-100 transition-opacity
                                   btn-ghost text-red-400 hover:text-red-600 p-1.5 rounded-lg"
                      >
                        {deleteId === doc.id
                          ? <Loader2 size={13} className="animate-spin" />
                          : <Trash2 size={13} />}
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
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <CaseTimeline caseId={id} />
          </div>
        )}
      </main>
    </div>
  );
}
