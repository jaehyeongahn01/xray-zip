import { useState, useEffect } from 'react';
import { getLeaderboard } from '../api.js';
import '../styles/stats.css';

export default function Leaderboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    getLeaderboard(10)
      .then((out) => {
        if (alive) setData(out);
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
  }, []);

  return (
    <div>
      <div className="app-title">순위표</div>
      <div className="app-sub">최고 평균 점수 기준 상위 플레이어</div>

      {error && <div className="notice">{error}</div>}
      {loading && <div className="muted">불러오는 중...</div>}

      {data && (
        <>
          {data.entries.length === 0 ? (
            <div className="muted">아직 기록이 없습니다. 게임을 플레이하면 순위에 오릅니다.</div>
          ) : (
            <table className="lb-table">
              <thead>
                <tr>
                  <th>순위</th>
                  <th>사용자</th>
                  <th>최고 평균</th>
                  <th>전체 평균</th>
                  <th>플레이</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((e) => (
                  <tr key={e.user_id}>
                    <td>{e.rank}</td>
                    <td>{e.user_id}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>{e.best_average.toFixed(1)}</span>
                        <div className="lb-mini-track">
                          <div
                            className="lb-mini-fill"
                            style={{ width: `${Math.max(0, Math.min(100, e.best_average))}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>{e.avg_average.toFixed(1)}</span>
                        <div className="lb-mini-track">
                          <div
                            className="lb-mini-fill"
                            style={{ width: `${Math.max(0, Math.min(100, e.avg_average))}%` }}
                          />
                        </div>
                      </div>
                    </td>
                    <td>{e.plays}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <div className="muted" style={{ marginTop: '1rem', fontSize: '0.85rem' }}>
            정렬 규칙: {data.sort}
          </div>
        </>
      )}
    </div>
  );
}
