// FastAPI 백엔드(FEAT-001) 호출 래퍼.
// 모든 엔드포인트는 http://localhost:8000 에 있으며, 오류 응답은 {"detail": "<한글>"} 형태다.
// 필드명은 백엔드 계약과 정확히 일치시킨다.
const BASE = '';

// 공통: 응답 상태를 검사하고, 실패 시 detail 메시지를 담은 Error를 던진다.
async function handle(res) {
  let body = null;
  try {
    body = await res.json();
  } catch (e) {
    body = null;
  }
  if (!res.ok) {
    const detail =
      body && body.detail
        ? body.detail
        : `요청에 실패했습니다. (HTTP ${res.status})`;
    throw new Error(detail);
  }
  return body;
}

// 네트워크 자체가 끊긴 경우도 한국어 메시지로 감싼다.
async function request(url, options) {
  let res;
  try {
    res = await fetch(url, { ...options, credentials: 'include' });
    if (res.status === 401) window.dispatchEvent(new Event('cxr-session-expired'));
  } catch (e) {
    throw new Error('백엔드에 연결할 수 없습니다. 서버(포트 8000)가 켜져 있는지 확인해 주세요.');
  }
  return handle(res);
}

// POST /api/predict — multipart(file + thresh 문자열 폼필드)
// 응답: { probs, pred_idx, pred_kr, class_names_kr, thresh_effective, images:{original,overlay,overlay_thresh} }
export async function predict(file, thresh, saveHistory = true) {
  const form = new FormData();
  form.append('file', file);
  form.append('save_history', String(saveHistory));
  if (thresh !== undefined && thresh !== null) {
    form.append('thresh', String(thresh));
  }
  return request(`${BASE}/api/predict`, { method: 'POST', body: form });
}

// GET /api/questions?n= — 응답: { questions: [{ id }] }
export async function getQuestions(n) {
  return request(`${BASE}/api/questions?n=${encodeURIComponent(n)}`, {
    method: 'GET',
  });
}

// 게임 이미지 URL. kind ∈ {image, overlay}. <img src>에 바로 사용.
export function gameImageUrl(id, kind) {
  return `${BASE}/api/game-image/${encodeURIComponent(id)}/${encodeURIComponent(kind)}`;
}

// POST /api/score
// body: { question_id, chosen_label, click?:{x,y}, display_size?:{w,h} }
// 응답: { score:{class_correct,class_points,location_points,total,distance,needs_click},
//        reveal:{true_label,true_label_kr,ai_pred_label,ai_pred_kr,ai_probs,peak_display,peak_cam,img_size,display_size} }
export async function postScore(body) {
  return request(`${BASE}/api/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// POST /api/register — body: { user_id, password, password_confirm, occupation }
// 응답(AccountResponse): { user_id, occupation } (이름·비번 관련 필드 없음)
export async function register(body) {
  return request(`${BASE}/api/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// POST /api/login — body: { user_id, password }
// 응답(AccountResponse): { user_id, occupation }
export async function login(body) {
  return request(`${BASE}/api/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// POST /api/users — body: { user_id } → { user_id, created }
export async function postUser(userId) {
  return request(`${BASE}/api/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId }),
  });
}

// POST /api/games — body: { user_id, per_question_summary:[...] }(집계값 보내지 않음, 서버 재계산)
// 응답: { saved, game_id, played_at, total_score, average, num_questions, num_correct }
export async function postGame(body) {
  return request(`${BASE}/api/games`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

// GET /api/users/{id}/stats
// 응답: { user_id, plays, avg_score, best_score, class_accuracy:{normal,bacteria,virus}, recent_trend:[] }
export async function getStats(userId) {
  return request(`${BASE}/api/users/${encodeURIComponent(userId)}/stats`, {
    method: 'GET',
  });
}

// GET /api/leaderboard?limit= — 응답: { sort, entries:[{rank,user_id,best_average,avg_average,plays}] }
export async function getLeaderboard(limit) {
  return request(`${BASE}/api/leaderboard?limit=${encodeURIComponent(limit)}`, {
    method: 'GET',
  });
}

export const getMe = () => request('/api/me');
export const logoutSession = () => request('/api/logout', { method: 'POST' });
export const getReadings = (params) => request('/api/readings?' + new URLSearchParams(params));
export const getReading = (id) => request('/api/readings/' + encodeURIComponent(id));
