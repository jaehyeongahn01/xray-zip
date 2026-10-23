import { useNavigate, useParams } from 'react-router-dom';
import Game from './Game.jsx';
import MyStats from './MyStats.jsx';
import Leaderboard from './Leaderboard.jsx';
import '../styles/xplay.css';

// X-PLAY: 큰 라벨 없이 내부에서 GAME / RANK 서브탭으로만 나눈다.
// 라우트: /x-play (GAME 기본) · /x-play/rank (RANK)
// RANK 탭은 내 기록(MyStats) + 순위표(Leaderboard)를 한 화면에 보여준다.
export default function XPlay() {
  const navigate = useNavigate();
  const { sub } = useParams(); // undefined | 'rank'
  const tab = sub === 'rank' ? 'rank' : 'game';

  return (
    <div className="xplay">
      <div className="xplay-tabs" role="tablist" aria-label="X-PLAY 메뉴">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'game'}
          className={tab === 'game' ? 'xplay-tab xplay-tab--active' : 'xplay-tab'}
          onClick={() => navigate('/x-play')}
        >
          GAME
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'rank'}
          className={tab === 'rank' ? 'xplay-tab xplay-tab--active' : 'xplay-tab'}
          onClick={() => navigate('/x-play/rank')}
        >
          RANK
        </button>
      </div>

      {tab === 'game' ? (
        <Game />
      ) : (
        <div className="xplay-rank">
          <MyStats />
          <div className="xplay-rank-divider" />
          <Leaderboard />
        </div>
      )}
    </div>
  );
}
