import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import TopNav from './components/TopNav.jsx';
import AuthGate from './components/AuthGate.jsx';
import Home from './pages/Home.jsx';
import Reader from './pages/Reader.jsx';
import XPlay from './pages/XPlay.jsx';
import ComingSoon from './pages/ComingSoon.jsx';
import { useAuth } from './auth/AuthContext.jsx';

export default function App() {
  const { user } = useAuth();
  const location = useLocation();

  // 미로그인 시: AuthGate만 노출 — 어떤 화면도 접근 불가.
  // 이때 URL 을 '/' 로 맞춰두면, 로그인되는 순간 Routes 가 무조건 Home 부터 시작한다
  // (이전에 보던 /x-ai, /x-play 등으로 바로 들어오지 않게 — "로그인하면 무조건 Home").
  if (!user) {
    return (
      <div className="page">
        {location.pathname !== '/' && <Navigate to="/" replace />}
        <AuthGate />
      </div>
    );
  }

  return (
    <div className="page">
      <TopNav />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/x-ai" element={<Reader />} />
        {/* X-PLAY: 내부 GAME / RANK 서브탭 (RANK = 내 기록 + 순위표) */}
        <Route path="/x-play" element={<XPlay />} />
        <Route path="/x-play/:sub" element={<XPlay />} />
        {/* X-LAB: 미구현 — Coming Soon 안내만 */}
        <Route path="/x-lab" element={<ComingSoon />} />
        {/* 알 수 없는 경로는 홈으로 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
