import { useState, useEffect } from 'react';
import { getStats } from '../api.js';
import '../styles/stats.css';

const LS_KEY = 'cxr_user_id';
const CLASS_ROWS = [
  { key: 'normal', label: '정상' },
  { key: 'bacteria', label: '세균성 폐렴' },
  { key: 'virus', label: '바이러스성 폐렴' },
];

export default function MyStats() {
  const userId = localStorage.getItem(LS_KEY) || '';
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userId) return;
    let alive = true;
    setLoading(true);
    getStats(userId)
      .then((out) => {
        if (alive) setStats(out);
      })
      .catch((e) => {
        if (alive) setError(e.message);
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [userId]);

  if (!userId) {
    return (
      <div>
        <div className="app-title">내 기록</div>
        <div className="notice">게임을 먼저 시작해 ID를 등록하세요.</div>
      </div>
    );
  }

  return (
    <div>
      <div className="app-title">내 기록</div>
      <div className="app-sub">
        플레이어: <b style={{ color: 'var(--text)' }}>{userId}</b>
      </div>

      {error && <div className="notice">{error}</div>}
      {loading && <div className="muted">불러오는 중...</div>}

      {stats && (
        <>
          <div className="stat-cards">
            <div className="stat-card">
              <div className="num">{stats.plays}</div>
              <div className="lbl">플레이 횟수</div>
            </div>
            <div className="stat-card">
              <div className="num">{stats.avg_score.toFixed(1)}</div>
              <div className="lbl">평균 점수</div>
            </div>
            <div className="stat-card">
              <div className="num">{stats.best_score.toFixed(1)}</div>
              <div className="lbl">최고 점수</div>
            </div>
          </div>

          <h3>클래스별 정확도</h3>
          <div className="card">
            {CLASS_ROWS.map((row) => {
              const c = stats.class_accuracy[row.key];
              const pct = (c.accuracy || 0) * 100;
              return (
                <div className="bar-row" key={row.key}>
                  <span>{row.label}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="bar-val">
                    {c.correct}/{c.total}
                  </span>
                </div>
              );
            })}
          </div>

          <h3>최근 추이 (오래된 → 최신)</h3>
          {stats.recent_trend.length === 0 ? (
            <div className="muted">아직 기록이 없습니다.</div>
          ) : (
            <div className="trend">
              {stats.recent_trend.map((v, i) => (
                <div
                  className="trend-bar"
                  key={i}
                  style={{ height: `${Math.max(2, v)}%` }}
                  title={`${v.toFixed(1)}점`}
                >
                  <span>{v.toFixed(0)}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
