import { NavLink, useLocation } from 'react-router-dom';
import Logo from './Logo.jsx';
import { useAuth } from '../auth/AuthContext.jsx';
import '../styles/topnav.css';

// 페이지 맨 위 네비: 왼쪽 XRAY.zip 로고 + 가운데 메뉴 + 오른쪽 사용자/로그아웃.
// X-LAB은 미구현이라 Coming Soon 배지와 함께 비활성(링크 아님).
const LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/x-ai', label: 'X-AI', end: false },
  { to: '/x-play', label: 'X-PLAY', end: false },
];

export default function TopNav() {
  const { user, logout } = useAuth();
  const location = useLocation();
  // X-PLAY 하위(/x-play, /x-play/rank) 어디서든 X-PLAY 메뉴를 활성으로.
  const xplayActive = location.pathname.startsWith('/x-play');

  return (
    <nav className="topnav" aria-label="주 메뉴">
      <NavLink to="/" className="topnav-logo" aria-label="XRAY.zip 홈">
        <Logo size="sm" />
      </NavLink>

      <div className="topnav-links">
        {LINKS.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            end={l.end}
            className={({ isActive }) => {
              const active = l.to === '/x-play' ? xplayActive : isActive;
              return active ? 'topnav-link topnav-link--active' : 'topnav-link';
            }}
          >
            {l.label}
          </NavLink>
        ))}
        {/* X-LAB — 미구현: 클릭 불가, Coming Soon 표시 */}
        <span
          className="topnav-link topnav-link--disabled"
          aria-disabled="true"
          title="준비 중입니다"
        >
          X-LAB
          <span className="topnav-soon">Coming Soon</span>
        </span>
      </div>

      {user && (
        <div className="topnav-user">
          <span className="topnav-user-label">{user.user_id}</span>
          <button type="button" className="topnav-logout" onClick={logout}>
            로그아웃
          </button>
        </div>
      )}
    </nav>
  );
}
