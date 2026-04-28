import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Send, Bot, User, ChevronDown, ChevronUp, Trash2,
  Scale, Sparkles, FileText, AlertCircle,
} from 'lucide-react';
import { sendChat, getHistory, clearChat } from '../api/client';

/* ─── Helpers ──────────────────────────────────────────── */
const formatTime = (iso) =>
  iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'just now';

/* ─── Source citation pill ─────────────────────────────── */
const SourcePill = ({ src, idx }) => (
  <div className="flex items-start gap-2.5 px-3 py-2.5 bg-indigo-50 border border-indigo-100
                  rounded-xl text-xs animate-fade-in">
    <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-[10px] font-bold
                     flex items-center justify-center flex-shrink-0 mt-0.5">
      {idx + 1}
    </span>
    <div className="min-w-0">
      <p className="font-semibold text-slate-700 truncate flex items-center gap-1">
        <FileText size={10} className="text-indigo-400" />
        {src.filename}
      </p>
      <p className="text-slate-500 mt-0.5">
        Page {src.page_num}
        {src.score != null && (
          <> · <span className="text-indigo-600 font-semibold">{(src.score * 100).toFixed(0)}% match</span></>
        )}
      </p>
      {src.excerpt && (
        <p className="text-slate-500 mt-1 italic line-clamp-2 leading-relaxed">"{src.excerpt}"</p>
      )}
    </div>
  </div>
);

/* ─── Message bubble ───────────────────────────────────── */
const Bubble = ({ msg }) => {
  const isUser  = msg.role === 'user';
  const isError = msg.role === 'assistant' && msg.content?.startsWith('⚠️');
  const [showSrc, setShowSrc] = useState(false);
  const sources = msg.sources || [];

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div className={[
        'flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center shadow-sm',
        isUser
          ? 'bg-gradient-to-br from-indigo-500 to-indigo-700'
          : isError
            ? 'bg-red-100'
            : 'bg-gradient-to-br from-slate-700 to-slate-900',
      ].join(' ')}>
        {isUser
          ? <User size={13} className="text-white" />
          : isError
            ? <AlertCircle size={13} className="text-red-500" />
            : <Bot size={13} className="text-white" />}
      </div>

      <div className={`max-w-[78%] flex flex-col gap-1 ${isUser ? 'items-end' : 'items-start'}`}>
        {/* Bubble body */}
        <div className={[
          'px-4 py-3 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words',
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm shadow-sm'
            : isError
              ? 'bg-red-50 text-red-800 border border-red-200 rounded-tl-sm'
              : 'bg-white text-slate-800 border border-slate-200/80 rounded-tl-sm shadow-sm',
        ].join(' ')}>
          {msg.content}
        </div>

        {/* Sources */}
        {!isUser && sources.length > 0 && (
          <div className="w-full">
            <button
              onClick={() => setShowSrc(s => !s)}
              className="flex items-center gap-1.5 text-[11px] text-slate-400 hover:text-indigo-600
                         transition-colors mt-0.5 px-1"
            >
              {showSrc ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              {sources.length} source{sources.length !== 1 ? 's' : ''} used
            </button>
            {showSrc && (
              <div className="mt-2 space-y-1.5">
                {sources.map((s, i) => <SourcePill key={i} src={s} idx={i} />)}
              </div>
            )}
          </div>
        )}

        <span className="text-[10px] text-slate-400 px-1">{formatTime(msg.created_at)}</span>
      </div>
    </div>
  );
};

/* ─── Typing dots ──────────────────────────────────────── */
const TypingDots = () => (
  <div className="flex gap-3 animate-fade-in">
    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-slate-700 to-slate-900
                    flex items-center justify-center flex-shrink-0 shadow-sm">
      <Sparkles size={12} className="text-indigo-300" />
    </div>
    <div className="bg-white border border-slate-200/80 rounded-2xl rounded-tl-sm
                    px-4 py-3 shadow-sm flex items-center gap-1.5 h-10">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse-dot"
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
    </div>
  </div>
);

/* ─── Suggested questions ──────────────────────────────── */
const SUGGESTIONS = [
  'What are the key facts of this case?',
  'What are my rights in this situation?',
  'What should be my next steps?',
  'Summarise the important dates and deadlines',
];

const EmptyChat = ({ onSuggest }) => (
  <div className="flex flex-col items-center justify-center h-full text-center py-12 px-6">
    <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-100 to-indigo-50
                    flex items-center justify-center mb-4 shadow-sm">
      <Scale size={24} className="text-indigo-500" />
    </div>
    <p className="font-semibold text-slate-700 mb-1">Ask anything about your case</p>
    <p className="text-sm text-slate-400 max-w-xs leading-relaxed">
      Ask in plain English — no legal jargon needed. AI will search your documents and answer instantly.
    </p>
    <div className="mt-5 flex flex-col gap-2 w-full max-w-sm">
      {SUGGESTIONS.map((q) => (
        <button
          key={q}
          onClick={() => onSuggest(q)}
          className="text-xs text-left px-4 py-2.5 rounded-xl bg-slate-50 border border-slate-200
                     text-slate-600 hover:bg-indigo-50 hover:border-indigo-200 hover:text-indigo-700
                     transition-all leading-snug"
        >
          {q}
        </button>
      ))}
    </div>
  </div>
);

/* ─── Main ChatWindow ──────────────────────────────────── */
export default function ChatWindow({ caseId }) {
  const [messages, setMessages] = useState([]);
  const [input,    setInput]    = useState('');
  const [loading,  setLoading]  = useState(false);
  const [fetching, setFetching] = useState(false);
  const bottomRef   = useRef(null);
  const textareaRef = useRef(null);

  /* Load history */
  const loadHistory = useCallback(async () => {
    if (!caseId) return;
    setFetching(true);
    try {
      const { data } = await getHistory(caseId, { limit: 100 });
      setMessages(data.messages || []);
    } catch { setMessages([]); }
    finally { setFetching(false); }
  }, [caseId]);

  useEffect(() => { loadHistory(); }, [loadHistory]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  /* Auto-resize textarea */
  const resize = () => {
    if (!textareaRef.current) return;
    textareaRef.current.style.height = 'auto';
    textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 128) + 'px';
  };

  /* Send */
  const handleSend = async (text = input) => {
    const msg = text.trim();
    if (!msg || loading || !caseId) return;
    setMessages(p => [...p, { role: 'user', content: msg, created_at: new Date().toISOString() }]);
    setInput('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
    setLoading(true);
    try {
      const { data } = await sendChat({
        case_id: caseId, message: msg, role: 'client', prompt_type: 'client', top_k: 5,
      });
      setMessages(p => [...p, {
        role: 'assistant', content: data.answer,
        sources: data.sources, created_at: new Date().toISOString(),
      }]);
    } catch (err) {
      setMessages(p => [...p, {
        role: 'assistant',
        content: `⚠️ ${err.message || 'Failed to get a response. Please try again.'}`,
        created_at: new Date().toISOString(),
      }]);
    } finally { setLoading(false); }
  };

  const handleClear = async () => {
    if (!caseId || !window.confirm('Clear all chat history for this case?')) return;
    await clearChat(caseId).catch(() => {});
    setMessages([]);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl border border-slate-200/80 shadow-sm overflow-hidden">
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100
                      bg-gradient-to-r from-slate-50 to-white flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-700
                          flex items-center justify-center shadow-sm">
            <Sparkles size={13} className="text-white" />
          </div>
          <div>
            <span className="font-semibold text-slate-800 text-sm">LawRAG AI</span>
            <span className="text-[11px] text-slate-400 ml-1.5">Legal Assistant</span>
          </div>
          {messages.length > 0 && (
            <span className="text-[10px] text-slate-300 border border-slate-200 rounded-full px-2 py-0.5 ml-1">
              {messages.length} message{messages.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>

        <button
          onClick={handleClear}
          title="Clear history"
          className="btn-ghost text-slate-400 hover:text-red-500 hover:bg-red-50 p-1.5 rounded-lg"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-5 bg-[#fafbfc]">
        {fetching && (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 rounded-full border-2 border-indigo-200 border-t-indigo-500 animate-spin" />
          </div>
        )}

        {!fetching && messages.length === 0 && (
          <EmptyChat onSuggest={(q) => { setInput(q); handleSend(q); }} />
        )}

        {messages.map((msg, i) => <Bubble key={i} msg={msg} />)}
        {loading && <TypingDots />}
        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div className="flex-shrink-0 px-4 py-3 border-t border-slate-100 bg-white">
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={e => { setInput(e.target.value); resize(); }}
            onKeyDown={handleKey}
            disabled={!caseId || loading}
            placeholder={caseId ? 'Ask a question about your case… (Enter to send)' : 'Select a case first'}
            rows={1}
            className="input flex-1 resize-none min-h-[42px] max-h-32 py-2.5 leading-relaxed bg-slate-50 focus:bg-white"
          />
          <button
            onClick={() => handleSend()}
            disabled={!caseId || loading || !input.trim()}
            className="btn-primary h-[42px] w-[42px] p-0 justify-center rounded-xl flex-shrink-0"
          >
            {loading
              ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              : <Send size={15} />}
          </button>
        </div>
        <p className="text-[10px] text-slate-300 text-right mt-1.5 pr-1">Shift+Enter for newline</p>
      </div>
    </div>
  );
}
