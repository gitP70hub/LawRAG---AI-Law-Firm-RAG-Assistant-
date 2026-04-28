import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

/* ── Icons ── */
const Icons = {
  Scale: (props) => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" /><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" /><path d="M7 21h10" /><path d="M12 3v18" /><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" /></svg>,
  Calendar: (props) => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect width="18" height="18" x="3" y="4" rx="2" ry="2" /><line x1="16" x2="16" y1="2" y2="6" /><line x1="8" x2="8" y1="2" y2="6" /><line x1="3" x2="21" y1="10" y2="10" /></svg>,
  Shield: (props) => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2-1 4-2 7-2 2.82 0 5.62.9 8 2 1 .5 1 1 1 2z" /></svg>,
  Pin: (props) => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><line x1="12" x2="12" y1="17" y2="22" /><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.68V6a3 3 0 0 0-3-3h0a3 3 0 0 0-3 3v4.68a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z" /></svg>,
  Lock: (props) => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><rect width="18" height="11" x="3" y="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" /></svg>,
  Sparkle: (props) => <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" stroke="none" {...props}><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" /></svg>
};

const USPS = [
  { icon: <Icons.Pin />, text: 'Exact Source Citations' },
  { icon: <Icons.Lock />, text: 'Private Local Execution' },
  { icon: <Icons.Shield />, text: 'Bank-Grade Security' },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const [go, setGo] = useState(false);

  useEffect(() => {
    // Inject premium custom fonts (Outfit & Plus Jakarta Sans)
    const link = document.createElement('link');
    link.href = 'https://fonts.googleapis.com/css2?family=Outfit:wght@300;500;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap';
    link.rel = 'stylesheet';
    document.head.appendChild(link);

    // Trigger animations right after mount
    const id = requestAnimationFrame(() => setGo(true));
    return () => {
      cancelAnimationFrame(id);
      document.head.removeChild(link);
    };
  }, []);

  return (
    <div style={{
      height: '100vh', overflow: 'hidden',
      fontFamily: "'Plus Jakarta Sans', sans-serif",
      background: 'linear-gradient(135deg, #f0f4ff 0%, #ffffff 40%, #f4f0ff 100%)',
      position: 'relative', display: 'flex', flexDirection: 'column'
    }}>
      {/* ── KEYFRAMES & CUSTOM STYLES ── */}
      <style>{`
        /* Cinematic Blur Reveal */
        @keyframes blurReveal {
          0% { opacity: 0; filter: blur(24px); transform: translateY(40px) scale(0.95); }
          100% { opacity: 1; filter: blur(0px); transform: translateY(0) scale(1); }
        }
        
        /* Organic Floating Effects */
        @keyframes floatY {
          0%, 100% { transform: translateY(0px) rotateY(-10deg) rotateX(5deg); }
          50% { transform: translateY(-15px) rotateY(-8deg) rotateX(8deg); }
        }
        @keyframes floatYReverse {
          0%, 100% { transform: translateY(0px) rotateY(10deg) rotateX(-5deg); }
          50% { transform: translateY(15px) rotateY(8deg) rotateX(-8deg); }
        }
        @keyframes floatBgX {
          0%, 100% { transform: translateX(0px); }
          50% { transform: translateX(30px); }
        }
        @keyframes floatBgY {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-30px); }
        }
        
        /* Sweeping Button Shine */
        @keyframes shine {
          0% { left: -100%; }
          20% { left: 100%; }
          100% { left: 100%; }
        }
        
        /* Pulsing Glow */
        @keyframes pulseBg {
          0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); }
          50% { opacity: 0.8; transform: translate(-50%, -50%) scale(1.15); }
        }

        /* Initial hidden state before JS kicks in */
        .lp-root:not(.go) .anim-reveal { opacity: 0; }
        
        /* Staggered Timings */
        .anim-reveal-1 { animation: blurReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both; }
        .anim-reveal-2 { animation: blurReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.2s both; }
        .anim-reveal-3 { animation: blurReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.3s both; }
        .anim-reveal-4 { animation: blurReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.4s both; }
        .anim-reveal-5 { animation: blurReveal 1.2s cubic-bezier(0.16, 1, 0.3, 1) 0.5s both; }

        /* Typography */
        .hero-title {
          font-family: 'Outfit', sans-serif;
          font-size: clamp(42px, 4.5vw, 68px);
          font-weight: 800;
          line-height: 1.05;
          letter-spacing: -0.04em;
          color: #0f172a;
        }

        .text-gradient {
          background: linear-gradient(135deg, #4f46e5 0%, #a855f7 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }

        /* Interactive Button */
        .magic-btn {
          position: relative;
          overflow: hidden;
          background: #0f172a;
          color: white;
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-weight: 600;
          font-size: 15px;
          padding: 16px 36px;
          border-radius: 100px;
          border: none;
          cursor: pointer;
          transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.3s ease;
          box-shadow: 0 10px 25px rgba(15, 23, 42, 0.15);
        }
        .magic-btn::before {
          content: '';
          position: absolute;
          top: 0; left: -100%;
          width: 50%; height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255,255,255,0.25), transparent);
          transform: skewX(-20deg);
          animation: shine 4s infinite;
        }
        .magic-btn:hover {
          transform: translateY(-4px) scale(1.02);
          box-shadow: 0 20px 40px rgba(79, 70, 229, 0.3);
          background: linear-gradient(135deg, #4f46e5, #7c3aed);
        }

        /* 3D Glassmorphic Cards */
        .glass-card {
          background: rgba(255, 255, 255, 0.6);
          backdrop-filter: blur(24px);
          -webkit-backdrop-filter: blur(24px);
          border: 1px solid rgba(255, 255, 255, 0.9);
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.04), inset 0 1px 0 rgba(255,255,255,1);
          border-radius: 28px;
          padding: 30px;
          transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .glass-card:hover {
          /* Nullify the float rotation on hover to bring it flat to the screen */
          transform: translateY(-8px) scale(1.04) rotateY(0deg) rotateX(0deg) !important;
          box-shadow: 0 30px 60px rgba(79, 70, 229, 0.12), inset 0 1px 0 rgba(255,255,255,1);
          border-color: rgba(99, 102, 241, 0.3);
          z-index: 10 !important;
        }

        .nav-link {
          font-family: 'Plus Jakarta Sans', sans-serif;
          font-weight: 600;
          font-size: 13px;
          color: #475569;
          background: none; border: none; cursor: pointer;
          transition: color 0.2s;
        }
        .nav-link:hover { color: #0f172a; }
      `}</style>

      {/* ── AMBIENT BACKGROUND ORBS ── */}
      <div style={{ position: 'absolute', top: '-20%', left: '-10%', width: '50vw', height: '50vw', background: 'radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 60%)', filter: 'blur(60px)', animation: 'floatBgY 15s ease-in-out infinite', zIndex: 0, pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '-20%', right: '-10%', width: '60vw', height: '60vw', background: 'radial-gradient(circle, rgba(168,85,247,0.1) 0%, transparent 60%)', filter: 'blur(80px)', animation: 'floatBgX 20s ease-in-out infinite', zIndex: 0, pointerEvents: 'none' }} />

      <div className={`lp-root${go ? ' go' : ''}`} style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', height: '100vh' }}>

        {/* ══ NAVBAR ══ */}
        <nav className="anim-reveal-1" style={{ flexShrink: 0, height: 70, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 5%', background: 'rgba(255,255,255,0.4)', backdropFilter: 'blur(20px)', borderBottom: '1px solid rgba(255,255,255,0.6)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 36, height: 36, borderRadius: 12, background: 'linear-gradient(135deg, #4f46e5, #a855f7)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white', boxShadow: '0 4px 10px rgba(79, 70, 229, 0.2)' }}>
              <Icons.Scale width="20" height="20" />
            </div>
            <span style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 800, fontSize: 20, color: '#0f172a', letterSpacing: '-0.02em' }}>
              Law<span className="text-gradient">RAG</span>
            </span>
          </div>

          <button onClick={() => navigate('/dashboard')} style={{ background: '#ffffff', color: '#0f172a', border: '1px solid #e2e8f0', borderRadius: 100, padding: '10px 24px', fontSize: 13, fontWeight: 700, cursor: 'pointer', transition: 'all 0.2s', boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }} onMouseOver={e => e.target.style.borderColor = '#4f46e5'} onMouseOut={e => e.target.style.borderColor = '#e2e8f0'}>
            Get Started
          </button>
        </nav>

        {/* ══ MAIN HERO ══ */}
        <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 5%', maxWidth: 1400, margin: '0 auto', width: '100%', gap: 40 }}>

          {/* LEFT: Copywriting */}
          <div style={{ maxWidth: 580, zIndex: 10 }}>
            <div className="anim-reveal-1" style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 16px', borderRadius: 100, background: 'rgba(255,255,255,0.6)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.8)', boxShadow: '0 4px 12px rgba(0,0,0,0.03)', color: '#4f46e5', fontWeight: 700, fontSize: 12, letterSpacing: '0.05em', marginBottom: 28 }}>
              <Icons.Sparkle width="14" height="14" />
              Next-Generation Legal AI
            </div>

            <h1 className="hero-title anim-reveal-2" style={{ marginBottom: 24 }}>
              Legal Intelligence,<br />
              Powered by <span className="text-gradient">Your Documents.</span>
            </h1>

            <p className="anim-reveal-3" style={{ fontSize: 17, color: '#475569', lineHeight: 1.6, marginBottom: 40, fontWeight: 500 }}>
              Stop digging through endless case files. Query your documents in plain English and get verifiable answers grounded purely in your own corpus.
            </p>

            <div className="anim-reveal-4">
              <button className="magic-btn" onClick={() => navigate('/dashboard')}>
                Experience LawRAG
              </button>
            </div>

            <div className="anim-reveal-5" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 48 }}>
              {USPS.map((u, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', background: 'rgba(255,255,255,0.5)', backdropFilter: 'blur(10px)', borderRadius: 12, border: '1px solid rgba(255,255,255,0.7)', fontSize: 13, fontWeight: 600, color: '#334155', boxShadow: '0 2px 8px rgba(0,0,0,0.02)', transition: 'transform 0.2s', cursor: 'default' }} onMouseOver={e => e.currentTarget.style.transform = 'translateY(-2px)'} onMouseOut={e => e.currentTarget.style.transform = 'none'}>
                  <span style={{ color: '#4f46e5' }}>{u.icon}</span>
                  {u.text}
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT: Floating 3D Composition */}
          <div className="anim-reveal-4" style={{ position: 'relative', width: 500, height: 480, perspective: 1200, display: 'flex', justifyContent: 'center', alignItems: 'center', flexShrink: 0 }}>

            {/* Background glowing orb for contrast under the cards */}
            <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', width: 280, height: 280, borderRadius: '50%', background: 'linear-gradient(135deg, rgba(79,70,229,0.35), rgba(168,85,247,0.35))', filter: 'blur(45px)', zIndex: 0, animation: 'pulseBg 8s ease-in-out infinite' }} />

            {/* Top Card - RAG */}
            <div className="glass-card" style={{ position: 'absolute', top: 20, right: -20, width: 340, zIndex: 2, animation: 'floatY 12s ease-in-out infinite' }}>
              <div style={{ width: 50, height: 50, borderRadius: 16, background: '#e0e7ff', color: '#4f46e5', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
                <Icons.Scale width="28" height="28" />
              </div>
              <h3 style={{ fontFamily: "'Outfit', sans-serif", fontSize: 22, fontWeight: 700, color: '#0f172a', margin: '0 0 10px 0' }}>RAG Legal Q&A</h3>
              <p style={{ margin: 0, fontSize: 14, color: '#475569', lineHeight: 1.6, fontWeight: 500 }}>
                Instant answers drawn directly from your documents. Zero hallucinations, fully cited.
              </p>
            </div>

            {/* Bottom Card - Timeline */}
            <div className="glass-card" style={{ position: 'absolute', bottom: 30, left: -20, width: 340, zIndex: 1, animation: 'floatYReverse 15s ease-in-out infinite' }}>
              <div style={{ width: 50, height: 50, borderRadius: 16, background: '#dbeafe', color: '#0ea5e9', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20 }}>
                <Icons.Calendar width="28" height="28" />
              </div>
              <h3 style={{ fontFamily: "'Outfit', sans-serif", fontSize: 22, fontWeight: 700, color: '#0f172a', margin: '0 0 10px 0' }}>Case Timeline</h3>
              <p style={{ margin: 0, fontSize: 14, color: '#475569', lineHeight: 1.6, fontWeight: 500 }}>
                AI intelligently extracts and maps hearings, orders, and case events chronologically.
              </p>
            </div>

          </div>
        </main>

      </div>
    </div>
  );
}
