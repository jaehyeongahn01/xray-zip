import { useState, useEffect, useRef } from 'react';
import { predict, getReadings, getReading } from '../api.js';
import ProbBar from '../components/ProbBar.jsx';
import '../styles/reader.css';

// 뷰 전환: 원본 / Grad-CAM 전체 / 핵심 영역
const VIEWS = [
  { key: 'original', label: '원본' },
  { key: 'overlay', label: 'Grad-CAM 전체' },
  { key: 'overlay_thresh', label: '핵심 영역' },
];

export default function Reader() {
  const [file, setFile] = useState(null);
  const [thresh, setThresh] = useState(0.7);
  const [result, setResult] = useState(null);
  const [view, setView] = useState('original');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState([]);
  const [filters, setFilters] = useState({ start: '', end: '', label: '' });
  const [hasMore, setHasMore] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [historyLoading, setHistoryLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const historySeq = useRef(0);
  const predictionSeq = useRef(0);
  async function loadHistory(offset = 0) {
    const seq = ++historySeq.current;
    setHistoryLoading(true); setHistoryError('');
    try {
      const params = Object.fromEntries(Object.entries(filters).filter(([,v]) => v !== ''));
      const out = await getReadings({ ...params, offset });
      if (seq !== historySeq.current) return;
      setHistory(prev => offset ? [...prev, ...out.items] : out.items);
      setHasMore(out.has_more);
    } catch(e) { if (seq === historySeq.current) setHistoryError(e.message); }
    finally { if (seq === historySeq.current) setHistoryLoading(false); }
  }
  useEffect(() => { if (historyOpen) loadHistory(); }, [historyOpen, filters, revision]);
  async function openReading(id) {
    const seq = ++predictionSeq.current;
    setLoading(true); setError('');
    try {
      const out = await getReading(id);
      if (seq !== predictionSeq.current) return;
      setFile(null); setResult(out); setThresh(out.thresh_effective); setView('original');
    } catch(e) { if (seq === predictionSeq.current) setError(e.message); }
    finally { if (seq === predictionSeq.current) setLoading(false); }
  }
  async function runPredict(f, th, saveHistory = true) {
    const seq = ++predictionSeq.current;
    setLoading(true);
    setError('');
    try {
      const out = await predict(f, th, saveHistory);
      if (seq !== predictionSeq.current) return;
      if (saveHistory && out.reading_id) { setRevision(v => v+1); setHistoryOpen(true); }
      setResult(out);
    } catch (e) {
      if (seq === predictionSeq.current) { setError(e.message); setResult(null); }
    } finally {
      if (seq === predictionSeq.current) setLoading(false);
    }
  }

  function onFileChange(e) {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setFile(f);
    setView('original');
    runPredict(f, thresh);
  }

  // thresh 변경 시 동일 파일로 재호출해 overlay_thresh 갱신
  function onThreshCommit(v) {
    setThresh(v);
    if (file) runPredict(file, v, false);
  }

  const caption =
    view === 'original'
      ? '원본 흉부 X선'
      : view === 'overlay'
      ? 'Grad-CAM (전체) — 모델이 주목한 정도'
      : result
      ? `핵심 영역 (cam ≥ ${result.thresh_effective}) — 가장 강하게 주목한 곳`
      : '';

  return (
    <div className={historyOpen ? 'reader-layout history-open' : 'reader-layout'}>
      {historyOpen && <aside className="reader-history" aria-label="내 판독 기록">
        <div className="history-heading"><h3>내 판독 기록</h3><button className="btn" onClick={() => setHistoryOpen(false)} aria-label="기록 닫기">닫기</button></div>
        <label>시작일<input aria-label="시작일" type="date" value={filters.start} onChange={e => setFilters({...filters, start:e.target.value})} /></label>
        <label>종료일<input aria-label="종료일" type="date" value={filters.end} onChange={e => setFilters({...filters, end:e.target.value})} /></label>
        <label>AI 예측<select value={filters.label} onChange={e => setFilters({...filters, label:e.target.value})}>
          <option value="">전체</option><option value="0">정상</option><option value="1">세균성 폐렴</option><option value="2">바이러스성 폐렴</option>
        </select></label>
        <button className="btn" onClick={() => setFilters({start:'',end:'',label:''})}>필터 초기화</button>
        <small className="muted">날짜는 한국 시간 기준입니다.</small>
        {historyError && <div role="alert">{historyError}<button onClick={() => loadHistory()}>다시 시도</button></div>}
        {historyLoading && <p className="muted">기록 불러오는 중...</p>}
        {!historyLoading && !historyError && !history.length && <p className="muted">조건에 맞는 판독 기록이 없습니다.</p>}
        {history.map(item => <button className="history-item" key={item.id} onClick={() => openReading(item.id)}>
          <strong>{item.filename}</strong><span>{item.pred_kr} · {(item.probs[item.pred_idx]*100).toFixed(1)}%</span>
          <small>{new Date(item.created_at).toLocaleString('ko-KR', {timeZone:'Asia/Seoul'})}</small>
        </button>)}
        {hasMore && <button className="btn" disabled={historyLoading} onClick={() => loadHistory(history.length)}>더 보기</button>}
      </aside>}
      <main className="reader-main">
      <button className="btn" aria-expanded={historyOpen} onClick={() => setHistoryOpen(v => !v)}>내 판독 기록 {historyOpen ? '닫기' : '열기'}</button>
      <div className="app-title">
        X-AI <span className="title-suffix">· AI 판독 보조</span>
      </div>
      <div className="app-sub">
        ResNet18 · 3분류(정상 / 세균성 / 바이러스성) · Grad-CAM 근거 시각화
      </div>

      <label className="reader-uploader">
        흉부 X선 이미지를 업로드하세요 (jpg / jpeg / png)
        <input disabled={loading} type="file" accept=".jpg,.jpeg,.png" onChange={onFileChange} />
      </label>

      {error && (
        <div className="notice" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {loading && <div className="muted">분석 중...</div>}

      {!result && !file && !loading && (
        <div className="muted">
          이미지를 올리면 원본 CXR이 표시됩니다. 사진 아래 버튼으로 AI의 판단 근거(Grad-CAM)를
          볼 수 있어요.
        </div>
      )}

      {result?.history_warning && <div className="notice" role="alert">{result.history_warning}</div>}
      {result && (
        <>
          <div style={{ margin: '0.5rem 0 1.2rem' }}>
            예측 &nbsp;
            <span className="pred-pill">
              {result.pred_kr} · {(result.probs[result.pred_idx] * 100).toFixed(1)}%
            </span>
          </div>

          <div className="reader-image-wrap">
            <img
              className="reader-image"
              src={result.images[view]}
              alt={caption}
            />
          </div>
          <div className="muted" style={{ textAlign: 'center', marginBottom: '0.8rem' }}>
            {caption}
          </div>

          <div className="reader-view-btns">
            {VIEWS.map((v) => (
              <button
                key={v.key}
                className={view === v.key ? 'btn btn-primary' : 'btn'}
                onClick={() => setView(v.key)}
              >
                {v.label}
              </button>
            ))}
          </div>

          {file ? <div className="reader-thresh">
            <label>Grad-CAM 핵심영역 문턱값</label>
            <input
              disabled={loading}
              type="range"
              min="0.3"
              max="0.9"
              step="0.05"
              value={thresh}
              onChange={(e) => setThresh(parseFloat(e.target.value))}
              onMouseUp={(e) => onThreshCommit(parseFloat(e.target.value))}
              onTouchEnd={(e) => onThreshCommit(parseFloat(e.target.value))}
            />
            <span className="muted">{thresh.toFixed(2)}</span>
          </div>

          : <p className="muted">저장 당시의 판독 결과입니다. {result.filename}</p>}

          <h3>클래스별 확률</h3>
          {result.class_names_kr.map((kr, i) => (
            <ProbBar key={kr} label={kr} prob={result.probs[i]} />
          ))}

          <div className="notice" style={{ marginTop: '1.4rem' }}>
            <b>⚠️ 한계 고지</b>: 본 도구는 교육·연구용 PoC입니다. 실제 의료 진단이 아니며, 공개
            데이터(jpg)로 학습한 참고용 결과입니다. 임상 판단은 반드시 의료 전문가가 수행해야
            합니다. Grad-CAM은 '모델이 주목한 영역'이지 의학적 병변 위치가 아닙니다.
          </div>
        </>
      )}
      </main>
    </div>
  );
}
