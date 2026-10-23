import { createContext, useContext, useEffect, useState } from 'react';
import { getMe, logoutSession } from '../api.js';
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  function login(account) {
    setUser(account);
    localStorage.setItem('cxr_user_id', account.user_id);
    localStorage.removeItem('cxr_auth');
  }
  function clear() {
    setUser(null);
    localStorage.removeItem('cxr_user_id');
    localStorage.removeItem('cxr_auth');
  }
  async function logout() {
    try { await logoutSession(); clear(); }
    catch (e) { window.alert('로그아웃하지 못했습니다. 다시 시도해 주세요.'); }
  }
  useEffect(() => {
    getMe().then(login).catch(clear).finally(() => setReady(true));
    window.addEventListener('cxr-session-expired', clear);
    return () => window.removeEventListener('cxr-session-expired', clear);
  }, []);
  return <AuthContext.Provider value={{ user, login, logout }}>
    {ready ? children : <div className="muted">로그인 확인 중...</div>}
  </AuthContext.Provider>;
}
export const useAuth = () => useContext(AuthContext);
