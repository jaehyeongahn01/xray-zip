// 확률 막대 — 라벨 + 핑크 그라데이션 진행 바.
// prob 는 0~1 값.
export default function ProbBar({ label, prob }) {
  const pct = Math.max(0, Math.min(1, prob)) * 100;
  return (
    <div style={{ marginBottom: '0.9rem' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          marginBottom: '0.3rem',
          fontSize: '0.92rem',
        }}
      >
        <span>{label}</span>
        <span className="muted">{pct.toFixed(1)}%</span>
      </div>
      <div className="probbar-track">
        <div className="probbar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
