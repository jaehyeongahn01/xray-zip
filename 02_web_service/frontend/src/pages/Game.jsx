import { useState, useEffect, useRef } from 'react';
import { getQuestions, gameImageUrl, postScore, postGame } from '../api.js';
import { useAuth } from '../auth/AuthContext.jsx';
import ImageMarker from '../components/ImageMarker.jsx';
import '../styles/game.css';

const DISPLAY = 512; // 게임 이미지 정사각 한 변(px) — 백엔드 peak_display 환산과 일치
const CLASS_KR = ['정상', '세균성 폐렴', '바이러스성 폐렴'];
const TIME_LIMIT = 10; // 문제당 제한시간(초). 초과 시 자동 0점 처리.

// phase: start → playing → revealed → finished (ID 등록은 로그인으로 대체됨)
export default function Game() {
  const { user } = useAuth();
  const userId = user.user_id;
  const [phase, setPhase] = useState('start');

  const [numQ, setNumQ] = useState(5);
  const [questions, setQuestions] = useState([]); // [{id}]
  const [idx, setIdx] = useState(0);
  const [results, setResults] = useState([]); // per-question records

  const [chosen, setChosen] = useState(null);
  const [click, setClick] = useState(null); // {x,y} 표시 좌표(512 기준)
  const [score, setScore] = useState(null); // 방금 /api/score 응답
  const [finalData, setFinalData] = useState(null); // /api/games 응답

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // 제한시간 타이머
  const [timeLeft, setTimeLeft] = useState(TIME_LIMIT);
  const submittedRef = useRef(false); // 이 문제에서 이미 제출/시간초과 처리됐는지

  const current = questions[idx];

  // ---- 시작 ----
  async function startGame(n) {
    setLoading(true);
    setError('');
    try {
      const out = await getQuestions(n);
      setQuestions(out.questions);
      setNumQ(n);
      setIdx(0);
      setResults([]);
      resetQuestion();
      setFinalData(null);
      setPhase('playing');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function resetQuestion() {
    setChosen(null);
    setClick(null);
    setScore(null);
  }

  // ---- 제출(채점) ----
  // 게이팅: 사용자 선택 기준(chosen!=0 이면 클릭 필수). 서버 needs_click 과 다름.
  const canSubmit =
    chosen !== null && (chosen === 0 || click !== null);

  // timedOut=true 면 제한시간 초과 → 서버가 0점 처리(선택/클릭 무시).
  async function submit(timedOut = false) {
    if (submittedRef.current) return; // 중복 방지(수동 제출과 타이머 동시 발생 등)
    if (!timedOut && !canSubmit) return;
    submittedRef.current = true;
    setLoading(true);
    setError('');
    // 시간초과 시에도 chosen_label 은 스키마상 필수라 선택값(없으면 0)을 보낸다. 서버가 0점으로 덮어씀.
    const body = {
      question_id: current.id,
      chosen_label: timedOut ? (chosen ?? 0) : chosen,
      timed_out: timedOut,
    };
    // 폐렴 선택 + 클릭이 있으면 click/display_size 동반 전송 (시간초과가 아닐 때만 의미)
    if (!timedOut && chosen !== 0 && click) {
      body.click = { x: click.x, y: click.y };
      body.display_size = { w: DISPLAY, h: DISPLAY };
    }
    try {
      const out = await postScore(body);
      setScore(out);
      setResults((prev) => [
        ...prev,
        {
          question_id: current.id,
          chosen_label: chosen,
          click,
          score: out.score,
          reveal: out.reveal,
        },
      ]);
      setPhase('revealed');
    } catch (e) {
      setError(e.message);
      submittedRef.current = false; // 실패 시 재시도 허용
    } finally {
      setLoading(false);
    }
  }

  // ---- 타이머: playing 진입 때마다 10초 리셋, 0이면 자동 시간초과 제출 ----
  useEffect(() => {
    if (phase !== 'playing' || !current) return;
    submittedRef.current = false;
    setTimeLeft(TIME_LIMIT);
    const started = Date.now();
    const timer = setInterval(() => {
      const remain = TIME_LIMIT - (Date.now() - started) / 1000;
      if (remain <= 0) {
        clearInterval(timer);
        setTimeLeft(0);
        submit(true); // 시간초과 → 0점
      } else {
        setTimeLeft(remain);
      }
    }, 100);
    return () => clearInterval(timer);
    // idx 가 바뀌면(다음 문제) 새로 시작. phase 가 playing 될 때도.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase, idx]);

  // ---- 다음 / 종료 ----
  const isLast = idx + 1 >= questions.length;

  async function next() {
    if (!isLast) {
      setIdx((i) => i + 1);
      resetQuestion();
      setPhase('playing');
      return;
    }
    // 마지막 → 저장
    setLoading(true);
    setError('');
    const per_question_summary = results.map((r) => ({
      question_id: r.question_id,
      true_label: r.reveal.true_label,
      chosen_label: r.chosen_label,
      class_correct: r.score.class_correct,
      location_points: r.score.location_points,
      total: r.score.total,
      needs_click: r.score.needs_click,
    }));
    try {
      const out = await postGame({ user_id: userId, per_question_summary });
      setFinalData(out);
      setPhase('finished');
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function restart() {
    setResults([]);
    setQuestions([]);
    setIdx(0);
    resetQuestion();
    setFinalData(null);
    setPhase('start');
  }

  // ============================================================
  return (
    <div>
      <div className="app-title">
        X-PLAY <span className="title-suffix">· 판독 챌린지</span>
      </div>
      <div className="app-sub">
        직접 판독하고 AI(Grad-CAM)와 비교하며 배우는 연습 — 위치 점수는 "AI가 주목한 영역과의
        일치도"이지 의학적 정답이 아닙니다.
      </div>

      {error && (
        <div className="notice" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {phase === 'start' && (
        <StartView
          userId={userId}
          numQ={numQ}
          setNumQ={setNumQ}
          onStart={startGame}
          loading={loading}
        />
      )}

      {phase === 'playing' && current && (
        <PlayingView
          current={current}
          idx={idx}
          total={questions.length}
          chosen={chosen}
          setChosen={setChosen}
          click={click}
          setClick={setClick}
          canSubmit={canSubmit}
          onSubmit={() => submit(false)}
          loading={loading}
          timeLeft={timeLeft}
          runningScore={results.reduce((s, r) => s + r.score.total, 0)}
        />
      )}

      {phase === 'revealed' && current && score && (
        <RevealedView
          current={current}
          chosen={chosen}
          click={click}
          score={score.score}
          reveal={score.reveal}
          isLast={isLast}
          onNext={next}
          loading={loading}
        />
      )}

      {phase === 'finished' && finalData && (
        <FinishedView data={finalData} results={results} onRestart={restart} />
      )}
    </div>
  );
}

// ---------------- 시작 ----------------
function StartView({ userId, numQ, setNumQ, onStart, loading }) {
  return (
    <div>
      <div className="card">
        <h3>게임 설정</h3>
        <p className="muted">
          플레이어: <b style={{ color: 'var(--text)' }}>{userId}</b>
        </p>
        <p>문제 수를 고르고 시작하세요. 문제는 무작위로 출제됩니다.</p>
        <div className="game-start-btns">
          <button
            className={numQ === 5 ? 'btn btn-primary' : 'btn'}
            onClick={() => setNumQ(5)}
          >
            5문제
          </button>
          <button
            className={numQ === 10 ? 'btn btn-primary' : 'btn'}
            onClick={() => setNumQ(10)}
          >
            10문제
          </button>
        </div>
        <div className="muted" style={{ margin: '0.4rem 0 1rem' }}>
          선택된 문제 수: <b style={{ color: 'var(--text)' }}>{numQ}문제</b>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => onStart(numQ)}
          disabled={loading}
        >
          {loading ? '불러오는 중...' : '시작하기'}
        </button>
      </div>

      <div className="card">
        <h3>진행 방식</h3>
        <ul className="muted" style={{ marginTop: '0.4rem', lineHeight: 1.8 }}>
          <li>흉부 X선을 보고 정상 / 세균성 폐렴 / 바이러스성 폐렴 중 하나를 고릅니다.</li>
          <li>폐렴을 골랐다면 이상 소견이 의심되는 지점을 이미지에서 클릭하세요 (제출 조건).</li>
          <li>정상은 클릭 없이 바로 제출할 수 있습니다.</li>
          <li>
            <b style={{ color: 'var(--text)' }}>문제마다 제한시간 {TIME_LIMIT}초</b>가 있습니다.
            질문 위 게이지가 줄어들며, 시간 안에 제출하지 못하면 그 문제는 0점 처리됩니다.
          </li>
          <li>제출하면 실제 라벨·AI 예측·Grad-CAM과 비교해 점수를 매깁니다.</li>
        </ul>
        <p className="muted">
          점수 — 문제당 100점: 클래스 정답 50점 + 위치 일치도 50점 (정상 문제는 클래스만, 맞으면
          100점).
        </p>
      </div>
    </div>
  );
}

// ---------------- 풀이 ----------------
function PlayingView({
  current,
  idx,
  total,
  chosen,
  setChosen,
  click,
  setClick,
  canSubmit,
  onSubmit,
  loading,
  timeLeft,
  runningScore,
}) {
  const pct = Math.max(0, Math.min(100, (timeLeft / TIME_LIMIT) * 100));
  // 시간 얼마 안 남으면 게이지 색 경고(코랄→붉게)
  const low = timeLeft <= 3;
  const hint =
    chosen === null
      ? '클래스를 먼저 선택하세요.'
      : chosen !== 0 && !click
      ? '폐렴을 선택했어요. 이상 소견 지점을 이미지에서 클릭해야 제출할 수 있어요.'
      : '';

  return (
    <div>
      <div className="game-progress">
        문제 {idx + 1} / {total} · 현재까지 점수: {Math.round(runningScore)}점
      </div>
      <div className="game-layout">
        <div className="game-image-col">
          <ImageMarker
            src={gameImageUrl(current.id, 'image')}
            size={DISPLAY}
            click={chosen !== 0 ? click : null}
            onPick={(x, y) => setClick({ x, y })}
            alt={`문제 ${idx + 1}`}
          />
          <span className="muted" style={{ fontSize: '0.85rem' }}>
            세균성·바이러스성을 골랐다면 이상 소견이 의심되는 지점을 클릭하세요. 다시 클릭하면
            위치가 바뀝니다.
          </span>
        </div>

        <div>
          {/* 제한시간 게이지 — 질문 글자 위에서 가로로 줄어든다 */}
          <div className="game-timer" aria-label={`남은 시간 ${Math.ceil(timeLeft)}초`}>
            <div className="game-timer-head">
              <span className="muted">남은 시간</span>
              <span className={low ? 'game-timer-sec game-timer-sec--low' : 'game-timer-sec'}>
                {Math.ceil(timeLeft)}초
              </span>
            </div>
            <div className="game-timer-track">
              <div
                className={low ? 'game-timer-fill game-timer-fill--low' : 'game-timer-fill'}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>

          <b>이 영상을 어떻게 판독하시겠어요?</b>
          <div className="game-class-btns" style={{ marginTop: '0.7rem' }}>
            {CLASS_KR.map((kr, li) => (
              <button
                key={kr}
                className={chosen === li ? 'btn btn-primary' : 'btn'}
                onClick={() => setChosen(li)}
              >
                {kr}
              </button>
            ))}
          </div>

          {hint && (
            <div className="muted" style={{ marginBottom: '0.8rem' }}>
              {hint}
            </div>
          )}

          <button
            className="btn btn-primary"
            onClick={onSubmit}
            disabled={!canSubmit || loading}
          >
            {loading ? '채점 중...' : '정답 제출'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------- 정답 공개 ----------------
function RevealedView({ current, chosen, click, score, reveal, isLast, onNext, loading }) {
  return (
    <div>
      <div className="game-layout">
        <div className="game-image-col">
          <ImageMarker
            src={gameImageUrl(current.id, 'overlay')}
            size={DISPLAY}
            peak={reveal.peak_display}
            click={click}
            alt="Grad-CAM 오버레이"
          />
          <span className="muted" style={{ fontSize: '0.85rem' }}>
            Grad-CAM 오버레이 · 초록=AI 주목 지점, 분홍=내 선택
          </span>
        </div>

        <div>
          {score.class_correct ? (
            <span className="badge-ok">● 클래스 정답</span>
          ) : (
            <span className="badge-no">● 클래스 오답</span>
          )}
          <ul style={{ marginTop: '0.7rem', lineHeight: 1.9 }}>
            <li>
              실제 라벨: <b>{reveal.true_label_kr}</b>
            </li>
            <li>
              내 선택: <b>{CLASS_KR[chosen]}</b>
            </li>
            <li>
              AI 예측: <b>{reveal.ai_pred_kr}</b> (
              {(reveal.ai_probs[reveal.ai_pred_label] * 100).toFixed(1)}%)
            </li>
          </ul>

          <hr style={{ borderColor: 'rgba(247,138,159,0.15)' }} />

          {score.needs_click ? (
            <ul style={{ lineHeight: 1.9 }}>
              <li>
                클래스 점수: <b>{score.class_points} / 50</b>
              </li>
              <li>
                위치 점수: <b>{score.location_points.toFixed(0)} / 50</b>
                {score.distance !== null &&
                  score.distance !== undefined &&
                  ` (AI 주목 지점까지 ${score.distance.toFixed(0)}px)`}
              </li>
            </ul>
          ) : (
            <p>
              정상 문제: 클래스만 채점 → <b>{score.class_points} / 100</b>
            </p>
          )}

          <div style={{ margin: '0.6rem 0' }}>
            이 문제 점수 &nbsp;
            <span className="score-pill">{score.total.toFixed(0)}</span>
            <span className="muted"> / 100</span>
          </div>

          <button className="btn btn-primary" onClick={onNext} disabled={loading}>
            {loading ? '저장 중...' : isLast ? '결과 보기' : '다음 문제'}
          </button>
        </div>
      </div>

      <div className="notice" style={{ marginTop: '1.2rem' }}>
        위치 점수는 Grad-CAM(AI가 주목한 영역)과의 일치도이며 의학적 병변 위치의 정답이 아닙니다.
        교육·연구용 PoC입니다.
      </div>
    </div>
  );
}

// ---------------- 종료 ----------------
function FinishedView({ data, results, onRestart }) {
  return (
    <div>
      <h3>게임 종료</h3>
      <div style={{ margin: '0.6rem 0 1.2rem' }}>
        최종 점수 &nbsp;
        <span className="score-pill">{data.average.toFixed(1)}</span>
        <span className="muted"> / 100 (문제 평균)</span>
      </div>

      <div className="game-metrics">
        <div className="metric-card">
          <div className="num">{data.num_correct} / {data.num_questions}</div>
          <div className="lbl">클래스 정답</div>
        </div>
        <div className="metric-card">
          <div className="num">{data.num_questions}</div>
          <div className="lbl">문제 수</div>
        </div>
        <div className="metric-card">
          <div className="num">{Math.round(data.total_score)}</div>
          <div className="lbl">누적 득점 (Σ)</div>
        </div>
      </div>

      <h3>문제별 요약</h3>
      {results.map((r, i) => {
        const ok = r.score.class_correct ? '✅' : '❌';
        let loc = '';
        if (r.score.needs_click) {
          loc = ` · 위치 ${r.score.location_points.toFixed(0)}/50`;
          if (r.score.distance !== null && r.score.distance !== undefined) {
            loc += ` (거리 ${r.score.distance.toFixed(0)}px)`;
          }
        }
        return (
          <div className="game-summary-row" key={i}>
            <b>Q{i + 1}</b> {ok} 정답: <b>{r.reveal.true_label_kr}</b> / 내 선택:{' '}
            {CLASS_KR[r.chosen_label]} · 점수 <b>{r.score.total.toFixed(0)}/100</b>
            {loc}
          </div>
        );
      })}

      <div style={{ marginTop: '1.4rem', maxWidth: 240 }}>
        <button className="btn btn-primary" onClick={onRestart}>
          다시 시작
        </button>
      </div>

      <div className="notice" style={{ marginTop: '1.2rem' }}>
        위치 점수는 Grad-CAM 일치도이며 의학적 정답이 아닙니다. 본 게임은 교육·연구용 PoC입니다.
      </div>
    </div>
  );
}
