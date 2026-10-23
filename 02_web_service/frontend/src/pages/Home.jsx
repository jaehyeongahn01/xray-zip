import { useNavigate } from 'react-router-dom';
import Logo from '../components/Logo.jsx';
import '../styles/home.css';

// 구현된 기능만 카드/CTA로 노출. X-LAB은 Coming Soon(링크·동작 없음).
const FEATURES = [
  {
    tag: 'X-AI',
    title: 'AI Imaging Assistant',
    desc: 'X-ray를 업로드하면 정상·세균성·바이러스성 폐렴을 분류하고, Grad-CAM으로 AI가 주목한 영역을 보여줍니다.',
    icon: '🫁',
    to: '/x-ai',
    ready: true,
  },
  {
    tag: 'X-PLAY',
    title: 'Diagnostic Challenge',
    desc: '직접 X-ray를 판독하고 AI와 비교하며 배우는 교육 게임. 내 기록과 순위도 함께 확인하세요.',
    icon: '🎯',
    to: '/x-play',
    ready: true,
  },
  {
    tag: 'X-LAB',
    title: 'AI Experiment Studio',
    desc: '여러 X-ray AI 모델을 실험하고 성능을 비교하는 공간. 곧 찾아옵니다.',
    icon: '🧪',
    to: null,
    ready: false,
  },
];

export default function Home() {
  const navigate = useNavigate();

  return (
    <div className="home">
      {/* ---- Hero ---- */}
      <section className="hero">
        <Logo size="lg" className="hero-logo" />
        <h1 className="hero-slogan">All Things X-ray, One Place.</h1>
        <p className="hero-slogan-kr">X-ray의 모든 가능성을 담은 공간</p>
        <p className="hero-sub">
          X-ray를 분석하고, 판독에 도전하고, AI의 판단을 탐험해 보세요.
        </p>
        <p className="hero-sub-en">Analyze, Play, and Explore the World of X-ray.</p>
      </section>

      {/* ---- 소개 ---- */}
      <section className="intro card">
        <p>
          <b style={{ color: 'var(--text)' }}>XRAY ZIP</b>은 X-ray와 관련된 다양한 기능을
          한곳에 모은 통합 플랫폼입니다. AI 판독(X-AI), 판독 교육 게임(X-PLAY), 모델 실험
          공간(X-LAB)까지 — 분석하고, 배우고, 탐험하는 모든 과정을 하나의 공간에서 경험하세요.
        </p>
      </section>

      {/* ---- Feature 카드 ---- */}
      <section className="features">
        {FEATURES.map((f) => (
          <article
            key={f.tag}
            className={f.ready ? 'feature-card' : 'feature-card feature-card--soon'}
            onClick={() => f.ready && navigate(f.to)}
            role={f.ready ? 'button' : undefined}
            tabIndex={f.ready ? 0 : undefined}
            onKeyDown={(e) => {
              if (f.ready && (e.key === 'Enter' || e.key === ' ')) navigate(f.to);
            }}
          >
            <div className="feature-icon" aria-hidden="true">
              {f.icon}
            </div>
            <div className="feature-tag">{f.tag}</div>
            <div className="feature-title">{f.title}</div>
            <p className="feature-desc">{f.desc}</p>
            {!f.ready && <span className="feature-soon">Coming Soon</span>}
          </article>
        ))}
      </section>
    </div>
  );
}
