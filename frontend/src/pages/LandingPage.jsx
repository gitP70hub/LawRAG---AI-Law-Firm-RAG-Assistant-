import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

/* ─── data ──────────────────────────────────────────────────── */
const FEATURES = [
  { icon: '⚖️', title: 'RAG Legal Q&A',     desc: 'Source-cited answers drawn exclusively from your uploaded case documents — zero hallucination.' },
  { icon: '📅', title: 'Case Timeline',      desc: 'AI extracts chronological events, hearings and court orders automatically.' },
  { icon: '🔍', title: 'Precedent Finder',   desc: 'Semantic search across case laws to surface similar judgments in seconds.' },
  { icon: '📋', title: 'Clause Analyzer',    desc: 'Flags risky contract clauses rated High / Medium / Low with plain-English explanations.' },
  { icon: '👤', title: 'Client View',        desc: 'Plain-language summaries of complex legal documents tailored for end clients.' },
  { icon: '👨‍⚖️', title: 'Lawyer Dashboard', desc: 'Full technical analysis toolkit — timelines, precedents, clause risk — for advocates.' },
];

const STEPS = [
  { num: '01', label: 'Upload', desc: 'Drop your legal PDFs into any case workspace.' },
  { num: '02', label: 'Index',  desc: 'AI chunks, embeds and stores them into ChromaDB vectors.' },
  { num: '03', label: 'Ask',    desc: 'Get grounded answers with exact source file citations.' },
];

const USPS = [
  { icon: '🔒', text: 'Not a generic chatbot — answers only from YOUR uploaded documents' },
  { icon: '📌', text: 'Every answer cites the exact source file and page number' },
  { icon: '👥', text: 'Separate purpose-built views for clients and lawyers' },
  { icon: '🖥️', text: 'Runs fully locally — your confidential legal data never leaves your machine' },
];

/* ─── reveal hook ───────────────────────────────────────────── */
function useReveal() {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { el.dataset.visible = 'true'; obs.disconnect(); } },
      { threshold: 0.1 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

function Reveal({ children, delay = 0 }) {
  const ref = useReveal();
  return (
    <div ref={ref} style={{ transitionDelay: `${delay}ms` }} className="rv-item">
      {children}
    </div>
  );
}

/* ─── page ──────────────────────────────────────────────────── */
export default function LandingPage() {
  const navigate = useNavigate();
  const howRef   = useRef(null);

  const goApp = () => navigate('/dashboard');
  const goHow = () => howRef.current?.scrollIntoView({ behavior: 'smooth' });

  return (
    <div style={{ background: '#f8fafc', color: '#0f172a', fontFamily: "'Inter',sans-serif", overflowX: 'hidden' }} className="min-h-screen">

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

        /* reveal */
        .rv-item { opacity:0; transform:translateY(20px); transition:opacity .6s cubic-bezier(.16,1,.3,1), transform .6s cubic-bezier(.16,1,.3,1); }
        .rv-item[data-visible="true"] { opacity:1; transform:translateY(0); }

        /* hero mesh gradient */
        .hero-mesh {
          background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 40%, #faf5ff 70%, #eef2ff 100%);
        }

        /* dot grid */
        .dot-grid {
          background-image: radial-gradient(#c7d2fe 1.2px, transparent 1.2px);
          background-size: 28px 28px;
        }

        /* card hover */
        .feat-card {
          background:#ffffff;
          border:1px solid #e2e8f0;
          transition: all .25s ease;
        }
        .feat-card:hover {
          border-color:#6366f1;
          box-shadow: 0 12px 40px rgba(99,102,241,0.12);
          transform: translateY(-4px);
        }

        /* stat card */
        .stat-card { transition: all .2s; }
        .stat-card:hover { box-shadow:0 8px 32px rgba(99,102,241,0.12); transform:translateY(-2px); }

        /* usp card */
        .usp-card {
          background:#ffffff;
          border:1px solid #e2e8f0;
          transition: all .2s;
        }
        .usp-card:hover { border-color:#6366f1; box-shadow:0 6px 24px rgba(99,102,241,0.1); }

        /* step connector */
        .step-connector {
          position:absolute; top:28px;
          left:calc(50% + 40px); right:calc(-50% + 40px);
          height:2px;
          background: linear-gradient(90deg,#6366f1,#a5b4fc44);
        }

        /* badge */
        .badge-tag {
          background:#eef2ff;
          border:1px solid #c7d2fe;
          color:#4338ca;
        }

        /* pill */
        .pill-badge {
          background: linear-gradient(135deg,#eef2ff,#faf5ff);
          border:1px solid #c7d2fe;
          color:#4338ca;
        }

        /* section divider */
        .s-div { height:1px; background:linear-gradient(90deg,transparent,#e2e8f0,transparent); }

        /* navbar scroll shadow — applied via JS */
        .nav-scrolled { box-shadow:0 1px 24px rgba(99,102,241,0.08) !important; }
      `}</style>

      {/* ══ NAVBAR ════════════════════════════════════════════ */}
      <NavBar onEnter={goApp} />

      {/* ══ HERO ══════════════════════════════════════════════ */}
      <section className="hero-mesh dot-grid relative min-h-screen flex flex-col items-center justify-center px-6 text-center pt-20 pb-28 overflow-hidden">
        {/* decorative blobs */}
        <div className="absolute pointer-events-none rounded-full"
             style={{ width:520, height:520, top:'-10%', left:'-8%', background:'radial-gradient(circle,rgba(99,102,241,0.12) 0%,transparent 70%)', filter:'blur(60px)' }} />
        <div className="absolute pointer-events-none rounded-full"
             style={{ width:480, height:480, bottom:'-5%', right:'-5%', background:'radial-gradient(circle,rgba(168,85,247,0.09) 0%,transparent 70%)', filter:'blur(60px)' }} />

        <div className="relative z-10 max-w-4xl mx-auto">
          {/* pill */}
          <div className="pill-badge inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold tracking-widest mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
            RAG-POWERED · LOCALLY HOSTED · SOURCE-CITED
          </div>

          {/* headline */}
          <h1 className="text-5xl md:text-7xl font-black leading-[1.05] tracking-tight mb-5"
              style={{ color:'#1e1b4b' }}>
            AI-Powered<br />
            <span style={{
              background:'linear-gradient(135deg,#4f46e5 0%,#7c3aed 50%,#4f46e5 100%)',
              WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', backgroundClip:'text'
            }}>
              Legal Intelligence
            </span>
          </h1>

          {/* sub */}
          <p className="text-lg md:text-xl leading-relaxed mb-10 max-w-2xl mx-auto" style={{ color:'#475569' }}>
            Upload case documents. Ask questions.<br />
            Get <strong style={{ color:'#4f46e5', fontWeight:700 }}>source-cited answers</strong> powered by RAG.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-10">
            <button id="hero-get-started" onClick={goApp}
              style={{ background:'linear-gradient(135deg,#4f46e5,#7c3aed)', color:'#fff' }}
              className="px-9 py-4 rounded-xl text-base font-bold hover:opacity-90 active:scale-95 transition-all shadow-xl shadow-indigo-200">
              Get Started →
            </button>
            <button id="hero-how-it-works" onClick={goHow}
              style={{ border:'2px solid #c7d2fe', color:'#4f46e5', background:'rgba(99,102,241,0.04)' }}
              className="px-9 py-4 rounded-xl text-base font-semibold hover:bg-indigo-50 active:scale-95 transition-all">
              See How It Works
            </button>
          </div>

          {/* tech tags */}
          <div className="flex items-center justify-center gap-3 flex-wrap">
            {['LangChain', 'ChromaDB', 'HuggingFace', 'FastAPI', 'React'].map(t => (
              <span key={t} className="badge-tag text-xs font-medium px-3 py-1 rounded-full">{t}</span>
            ))}
          </div>
        </div>

        {/* scroll */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5 opacity-40 select-none">
          <span className="text-[10px] tracking-[0.25em] uppercase text-indigo-400">Scroll</span>
          <div className="w-px h-8" style={{ background:'linear-gradient(to bottom,#6366f1,transparent)' }} />
        </div>
      </section>

      <div className="s-div" />

      {/* ══ STATS BAR ═════════════════════════════════════════ */}
      <section className="py-12 px-6" style={{ background:'#ffffff' }}>
        <div className="max-w-3xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-5">
          {[
            { val: 'RAG Pipeline',  sub: 'LangChain LCEL orchestration' },
            { val: '5 AI Modules',  sub: 'Q&A · Timeline · Precedent · Clause · Risk' },
            { val: '2 Role Views',  sub: 'Client-friendly & Lawyer-grade UI' },
          ].map(s => (
            <div key={s.val} className="stat-card text-center py-7 px-4 rounded-2xl"
                 style={{ border:'1px solid #e0e7ff', background:'#fafbff' }}>
              <p className="text-xl font-black mb-1" style={{ color:'#4f46e5' }}>{s.val}</p>
              <p className="text-xs" style={{ color:'#94a3b8' }}>{s.sub}</p>
            </div>
          ))}
        </div>
      </section>

      <div className="s-div" />

      {/* ══ FEATURES ══════════════════════════════════════════ */}
      <section className="py-24 px-6" style={{ background:'#f8fafc' }}>
        <div className="max-w-5xl mx-auto">
          <Reveal>
            <div className="text-center mb-14">
              <p className="text-xs font-bold tracking-widest uppercase mb-2" style={{ color:'#6366f1' }}>Features</p>
              <h2 className="text-3xl md:text-4xl font-black" style={{ color:'#1e1b4b' }}>
                Everything your law firm needs
              </h2>
            </div>
          </Reveal>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {FEATURES.map((f, i) => (
              <Reveal key={f.title} delay={i * 60}>
                <div className="feat-card p-6 rounded-2xl h-full">
                  <div className="text-3xl mb-4">{f.icon}</div>
                  <h3 className="font-bold text-base mb-2" style={{ color:'#1e1b4b' }}>{f.title}</h3>
                  <p className="text-sm leading-relaxed" style={{ color:'#64748b' }}>{f.desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <div className="s-div" />

      {/* ══ HOW IT WORKS ══════════════════════════════════════ */}
      <section ref={howRef} id="how-it-works" className="py-24 px-6" style={{ background:'#ffffff' }}>
        <div className="max-w-4xl mx-auto">
          <Reveal>
            <div className="text-center mb-16">
              <p className="text-xs font-bold tracking-widest uppercase mb-2" style={{ color:'#6366f1' }}>How It Works</p>
              <h2 className="text-3xl md:text-4xl font-black" style={{ color:'#1e1b4b' }}>
                Three steps to AI-powered answers
              </h2>
            </div>
          </Reveal>

          <Reveal delay={100}>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-10 relative">
              {STEPS.map((s, i) => (
                <div key={s.num} className="flex flex-col items-center text-center relative">
                  <div className="w-16 h-16 rounded-full flex items-center justify-center text-xl font-black mb-4 relative z-10"
                       style={{ background:'linear-gradient(135deg,#eef2ff,#f5f3ff)', border:'2px solid #6366f1', color:'#4f46e5' }}>
                    {s.num}
                  </div>
                  <h3 className="text-lg font-bold mb-1" style={{ color:'#1e1b4b' }}>{s.label}</h3>
                  <p className="text-sm" style={{ color:'#64748b', maxWidth:180 }}>{s.desc}</p>
                  {i < STEPS.length - 1 && <div className="step-connector hidden md:block" />}
                </div>
              ))}
            </div>
          </Reveal>

          <Reveal delay={250}>
            <div className="mt-14 text-center">
              <button id="how-try-now" onClick={goApp}
                style={{ border:'2px solid #6366f1', color:'#4f46e5', background:'#eef2ff' }}
                className="px-8 py-3.5 rounded-xl text-sm font-bold hover:bg-indigo-100 active:scale-95 transition-all">
                Try It Now →
              </button>
            </div>
          </Reveal>
        </div>
      </section>

      <div className="s-div" />

      {/* ══ USP ═══════════════════════════════════════════════ */}
      <section className="py-24 px-6" style={{ background:'#f8fafc' }}>
        <div className="max-w-3xl mx-auto">
          <Reveal>
            <div className="text-center mb-12">
              <p className="text-xs font-bold tracking-widest uppercase mb-2" style={{ color:'#6366f1' }}>Why LawRAG</p>
              <h2 className="text-3xl md:text-4xl font-black" style={{ color:'#1e1b4b' }}>
                Built different, by design
              </h2>
              <p className="mt-3 text-sm" style={{ color:'#64748b' }}>
                Most legal chatbots guess. LawRAG only answers from what you upload.
              </p>
            </div>
          </Reveal>

          <div className="space-y-4">
            {USPS.map((u, i) => (
              <Reveal key={i} delay={i * 70}>
                <div className="usp-card flex items-start gap-4 p-5 rounded-2xl">
                  <span className="text-2xl flex-shrink-0">{u.icon}</span>
                  <p className="text-sm leading-relaxed" style={{ color:'#334155' }}>{u.text}</p>
                </div>
              </Reveal>
            ))}
          </div>

          <Reveal delay={350}>
            <div className="mt-12 text-center">
              <button id="usp-enter-app" onClick={goApp}
                style={{ background:'linear-gradient(135deg,#4f46e5,#7c3aed)', color:'#fff' }}
                className="px-10 py-4 rounded-xl text-base font-black hover:opacity-90 active:scale-95 transition-all shadow-xl shadow-indigo-200">
                Enter LawRAG →
              </button>
            </div>
          </Reveal>
        </div>
      </section>

      <div className="s-div" />

      {/* ══ FOOTER ════════════════════════════════════════════ */}
      <footer className="py-8 px-6 text-center" style={{ background:'#ffffff', borderTop:'1px solid #e2e8f0' }}>
        <p className="text-xs mb-1" style={{ color:'#94a3b8' }}>
          Built with{' '}
          <span style={{ color:'#64748b' }}>LangChain · HuggingFace · FastAPI · React · ChromaDB</span>
        </p>
        <p className="text-xs" style={{ color:'#cbd5e1' }}>LawRAG © 2026</p>
      </footer>

    </div>
  );
}

/* ─── Navbar (extracted to avoid re-renders) ───────────────── */
function NavBar({ onEnter }) {
  const navRef = useRef(null);
  useEffect(() => {
    const onScroll = () => {
      if (!navRef.current) return;
      navRef.current.classList.toggle('nav-scrolled', window.scrollY > 10);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <nav ref={navRef}
         style={{ background:'rgba(248,250,252,0.9)', backdropFilter:'blur(16px)', borderBottom:'1px solid #e2e8f0' }}
         className="fixed top-0 inset-x-0 z-50 flex items-center justify-between px-6 md:px-14 h-16 transition-shadow duration-300">
      <div className="flex items-center gap-2">
        <span className="text-xl">⚖️</span>
        <span className="text-lg font-bold tracking-tight" style={{ color:'#1e1b4b' }}>
          Law<span style={{ color:'#4f46e5' }}>RAG</span>
        </span>
      </div>
      <button id="navbar-enter-app" onClick={onEnter}
        style={{ background:'linear-gradient(135deg,#4f46e5,#7c3aed)', color:'#fff' }}
        className="px-5 py-2 rounded-xl text-sm font-bold hover:opacity-90 active:scale-95 transition-all shadow-md shadow-indigo-200">
        Enter App →
      </button>
    </nav>
  );
}
