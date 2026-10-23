import { useState, useRef } from 'react';
import { register as apiRegister, login as apiLogin } from '../api.js';
import { useAuth } from '../auth/AuthContext.jsx';
import Logo from './Logo.jsx';
import '../styles/auth.css';

const OCCUPATIONS = ['의사', '학생', '무직', '기타'];

// ID 입력 정리: IME 조합 중(composing)에는 원본을 그대로 두어 한글 조합이 깨지지 않게 하고,
// 조합이 끝났거나 조합이 아닌 입력일 때만 허용 문자(영문/숫자/-/_) 외를 제거한다.
function sanitizeId(value, composing) {
  return composing ? value : value.replace(/[^A-Za-z0-9_-]/g, '');
}

// 로그인하지 않은 사용자에게 보이는 유일한 화면.
// 로그인/회원가입 탭을 토글하고, 성공 시 useAuth().login으로 앱에 진입한다.
export default function AuthGate() {
  const { login } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' | 'register'

  // 로그인 폼
  const [loginId, setLoginId] = useState('');
  const [loginPw, setLoginPw] = useState('');

  // 회원가입 폼 (이름은 사용하지 않음)
  const [regId, setRegId] = useState('');
  const [regPw, setRegPw] = useState('');
  const [regPw2, setRegPw2] = useState('');
  const [regOcc, setRegOcc] = useState(OCCUPATIONS[0]);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // ID칸 IME 조합 상태(조합 중에는 허용문자 치환을 미뤄 한글 조합이 끊기지 않게).
  const composingId = useRef(false);

  // 비밀번호 확인: 두 칸 모두 입력됐고 값이 다를 때만 불일치로 본다.
  const pwMismatch = regPw.length > 0 && regPw2.length > 0 && regPw !== regPw2;

  function switchMode(next) {
    setMode(next);
    setError('');
  }

  async function onLogin(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const account = await apiLogin({
        user_id: loginId.trim(),
        password: loginPw,
      });
      login(account);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function onRegister(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const account = await apiRegister({
        user_id: regId.trim(),
        password: regPw,
        password_confirm: regPw2,
        occupation: regOcc,
      });
      // 회원가입 성공 → 반환된 {user_id,name,occupation}로 자동 로그인
      login(account);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card">
        <div className="auth-brand">
          <Logo size="md" />
        </div>
        <div className="app-sub auth-brand-sub">
          All Things X-ray, One Place.<br />
          로그인 후 X-AI 판독과 X-PLAY 교육 게임을 이용할 수 있습니다.
        </div>

        <div className="auth-tabs" role="tablist" aria-label="로그인 또는 회원가입">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={mode === 'login' ? 'auth-tab auth-tab--active' : 'auth-tab'}
            onClick={() => switchMode('login')}
          >
            로그인
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'auth-tab auth-tab--active' : 'auth-tab'}
            onClick={() => switchMode('register')}
          >
            회원가입
          </button>
        </div>

        {error && (
          <div className="notice" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        {mode === 'login' ? (
          <form onSubmit={onLogin}>
            <div className="auth-field">
              <label className="auth-label" htmlFor="login-id">
                사용자 ID
              </label>
              <input
                id="login-id"
                className="text-input"
                type="text"
                autoComplete="username"
                maxLength={64}
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label" htmlFor="login-pw">
                비밀번호 (숫자 4자리)
              </label>
              <input
                id="login-pw"
                className="text-input"
                type="password"
                inputMode="numeric"
                autoComplete="current-password"
                maxLength={4}
                value={loginPw}
                onChange={(e) => setLoginPw(e.target.value)}
              />
            </div>
            <div style={{ marginTop: '0.4rem' }}>
              <button
                className="btn btn-primary"
                type="submit"
                disabled={loading || !loginId.trim() || !loginPw}
              >
                {loading ? '로그인 중...' : '로그인'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={onRegister}>
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-id">
                사용자 ID
              </label>
              <input
                id="reg-id"
                className="text-input"
                type="text"
                autoComplete="username"
                placeholder="Gildong"
                maxLength={64}
                value={regId}
                // ID 는 영문/숫자/-/_ 만. 단 IME 조합 중에는 치환하지 않고(한글 조합이 깨지지 않게)
                // 조합이 끝난 뒤 그 외 문자를 제거한다. ID엔 한글이 남을 일이 없지만 패턴을 통일.
                onChange={(e) => setRegId(sanitizeId(e.target.value, composingId.current))}
                onCompositionStart={() => { composingId.current = true; }}
                onCompositionEnd={(e) => { composingId.current = false; setRegId(sanitizeId(e.target.value, false)); }}
              />
              <small className="auth-hint">영문·숫자·-·_만 사용할 수 있어요.</small>
            </div>
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-pw">
                비밀번호 (숫자 4자리)
              </label>
              <input
                id="reg-pw"
                className="text-input"
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                maxLength={4}
                value={regPw}
                onChange={(e) => setRegPw(e.target.value)}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label auth-label--row" htmlFor="reg-pw2">
                <span>비밀번호 확인</span>
                {pwMismatch && (
                  <span className="auth-error-inline">비밀번호가 다릅니다.</span>
                )}
              </label>
              <input
                id="reg-pw2"
                className={pwMismatch ? 'text-input text-input--error' : 'text-input'}
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                maxLength={4}
                value={regPw2}
                onChange={(e) => setRegPw2(e.target.value)}
                aria-invalid={pwMismatch}
              />
            </div>
            <div className="auth-field">
              <label className="auth-label" htmlFor="reg-occ">
                직업
              </label>
              <select
                id="reg-occ"
                className="text-input"
                value={regOcc}
                onChange={(e) => setRegOcc(e.target.value)}
              >
                {OCCUPATIONS.map((o) => (
                  <option key={o} value={o}>
                    {o}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ marginTop: '0.4rem' }}>
              <button
                className="btn btn-primary"
                type="submit"
                disabled={
                  loading || !regId.trim() || !regPw || !regPw2 || pwMismatch
                }
              >
                {loading ? '가입 중...' : '회원가입'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
