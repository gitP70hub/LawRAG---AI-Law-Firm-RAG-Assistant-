import { useState, useCallback, useRef } from 'react';
import {
  UploadCloud, FileText, CheckCircle2, XCircle, X,
  Loader2, AlertTriangle,
} from 'lucide-react';
import { uploadDocument } from '../api/client';

const formatBytes = (bytes) => {
  if (!bytes) return '0 B';
  const k = 1024, sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
};

const StatusIcon = ({ status }) => {
  if (status === 'done')      return <CheckCircle2 size={15} className="text-emerald-500 flex-shrink-0" />;
  if (status === 'error')     return <XCircle      size={15} className="text-red-500 flex-shrink-0" />;
  if (status === 'uploading') return <Loader2      size={15} className="text-indigo-500 animate-spin flex-shrink-0" />;
  return <FileText size={15} className="text-slate-400 flex-shrink-0" />;
};

export default function DocumentUpload({ caseId, onUploadSuccess }) {
  const [dragging, setDragging] = useState(false);
  const [files,    setFiles]    = useState([]); // {file, progress, status, error, chunks}
  const fileInputRef = useRef(null);
  const uploadRef    = useRef(0); // tracks next index independently of closure

  const startUpload = useCallback(async (file, idx) => {
    setFiles(prev => prev.map((f, i) => i === idx ? { ...f, status: 'uploading' } : f));
    try {
      const res = await uploadDocument(caseId, file, (pct) => {
        setFiles(prev => prev.map((f, i) => i === idx ? { ...f, progress: pct } : f));
      });

      // BUG 2 FIX: after successful upload, update status AND trigger document list refresh
      const data = res?.data || {};
      const chunks = data.chunks_created ?? 0;
      const indexed = data.is_indexed ?? false;

      setFiles(prev => prev.map((f, i) =>
        i === idx
          ? { ...f, status: 'done', progress: 100, chunks, indexed }
          : f
      ));

      // Always call onUploadSuccess so CaseDetail.jsx re-fetches the documents list
      if (typeof onUploadSuccess === 'function') {
        onUploadSuccess();
      }
    } catch (err) {
      const msg = err.message || 'Upload failed';
      setFiles(prev => prev.map((f, i) => i === idx ? { ...f, status: 'error', error: msg } : f));
    }
  }, [caseId, onUploadSuccess]);

  const addFiles = useCallback((incoming) => {
    const pdfs = Array.from(incoming).filter(f => f.type === 'application/pdf');
    if (!pdfs.length) return;
    const baseIdx = uploadRef.current;
    const entries = pdfs.map(file => ({ file, progress: 0, status: 'pending', error: null, chunks: 0 }));
    uploadRef.current += pdfs.length;
    setFiles(prev => {
      const next = [...prev, ...entries];
      // kick off uploads
      entries.forEach((_, i) => startUpload(pdfs[i], baseIdx + i));
      return next;
    });
  }, [startUpload]);

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false);
    if (caseId) addFiles(e.dataTransfer.files);
  };
  const onDragOver  = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);
  const onBrowse    = (e) => { addFiles(e.target.files); e.target.value = ''; };
  const removeFile  = (idx) => setFiles(prev => prev.filter((_, i) => i !== idx));

  const hasPending = files.some(f => f.status === 'uploading');

  return (
    <div className="space-y-4">
      {/* Drop Zone */}
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => caseId && fileInputRef.current?.click()}
        className={[
          'relative flex flex-col items-center justify-center gap-3 p-8 rounded-2xl',
          'border-2 border-dashed cursor-pointer transition-all duration-200',
          !caseId
            ? 'border-slate-200 bg-slate-50 opacity-50 cursor-not-allowed'
            : dragging
              ? 'border-indigo-500 bg-indigo-50 scale-[1.01] shadow-glow'
              : 'border-slate-200 bg-slate-50 hover:border-indigo-400 hover:bg-indigo-50/40',
        ].join(' ')}
      >
        <div className={[
          'w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-200',
          dragging ? 'bg-indigo-100' : 'bg-white border border-slate-200 shadow-sm',
        ].join(' ')}>
          <UploadCloud size={22} className={dragging ? 'text-indigo-600' : 'text-slate-400'} />
        </div>

        <div className="text-center">
          <p className={`font-semibold text-sm ${dragging ? 'text-indigo-700' : 'text-slate-700'}`}>
            {dragging ? 'Drop your PDFs here' : 'Drag & drop PDFs'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            or <span className="text-indigo-600 underline underline-offset-2">browse files</span>
          </p>
          <p className="text-[11px] text-slate-400 mt-2">PDF only · Max 50 MB per file</p>
        </div>

        <input
          ref={fileInputRef}
          type="file" accept=".pdf" multiple
          onChange={onBrowse}
          className="hidden"
          disabled={!caseId}
        />

        {hasPending && (
          <div className="absolute inset-0 rounded-2xl bg-white/60 backdrop-blur-[2px]
                          flex items-center justify-center">
            <div className="flex items-center gap-2 text-indigo-600 font-medium text-sm">
              <Loader2 size={16} className="animate-spin" /> Uploading & indexing…
            </div>
          </div>
        )}
      </div>

      {!caseId && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-50
                        border border-amber-200 text-[11px] text-amber-700">
          <AlertTriangle size={13} /> Select a case before uploading documents
        </div>
      )}

      {/* File list */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, i) => (
            <div
              key={i}
              className={[
                'flex flex-col gap-2 p-3 rounded-xl border transition-colors',
                f.status === 'done'
                  ? 'border-emerald-200 bg-emerald-50'
                  : f.status === 'error'
                    ? 'border-red-200 bg-red-50'
                    : 'border-slate-200 bg-white',
              ].join(' ')}
            >
              <div className="flex items-center gap-3">
                <StatusIcon status={f.status} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 truncate">{f.file.name}</p>
                  <p className="text-[11px] text-slate-500">
                    {formatBytes(f.file.size)}
                    {f.status === 'done' && f.chunks > 0 && (
                      <span className="ml-2 text-emerald-600 font-medium">
                        · {f.chunks} chunks indexed
                      </span>
                    )}
                    {f.status === 'done' && f.chunks === 0 && (
                      <span className="ml-2 text-amber-600 font-medium">
                        · Saved (indexing may be pending)
                      </span>
                    )}
                  </p>
                </div>
                <button
                  onClick={() => removeFile(i)}
                  className="text-slate-300 hover:text-slate-500 p-0.5 rounded-md transition-colors"
                >
                  <X size={14} />
                </button>
              </div>

              {/* Progress bar */}
              {f.status === 'uploading' && (
                <div className="w-full bg-slate-100 rounded-full h-1 overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 rounded-full transition-all duration-300
                                relative overflow-hidden"
                    style={{ width: `${f.progress}%` }}
                  >
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent
                                    via-white/30 to-transparent animate-shimmer" />
                  </div>
                </div>
              )}

              {f.status === 'error' && (
                <p className="text-[11px] text-red-600 truncate">{f.error}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
