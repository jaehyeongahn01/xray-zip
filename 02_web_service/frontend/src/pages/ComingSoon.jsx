import { useNavigate } from 'react-router-dom';

// X-LAB 등 미구현 기능 안내. 실제 동작을 기대하게 만들지 않는다.
export default function ComingSoon({ tag = 'X-LAB', title = 'AI Experiment Studio' }) {
  const navigate = useNavigate();
  return (
    <div style={{ textAlign: 'center', padding: '4rem 1rem' }}>
      <div className="app-title" style={{ display: 'inline-block' }}>
        {tag}
      </div>
      <div className="app-sub">{title}</div>
      <div className="card" style={{ maxWidth: 520, margin: '1.5rem auto' }}>
        <p style={{ margin: '0 0 0.4rem', color: 'var(--text)', fontWeight: 600 }}>
          준비 중입니다 — Coming Soon
        </p>
        <p className="muted" style={{ margin: 0, lineHeight: 1.7 }}>
          여러 X-ray AI 모델을 실험하고 성능을 비교하는 공간입니다. 아직 제공되지 않으며,
          준비가 끝나면 이곳에서 만나보실 수 있습니다.
        </p>
      </div>
      <button
        className="btn hero-cta-btn"
        style={{ width: 'auto', minWidth: 160 }}
        onClick={() => navigate('/')}
      >
        홈으로
      </button>
    </div>
  );
}
