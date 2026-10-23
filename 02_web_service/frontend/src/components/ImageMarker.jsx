import '../styles/imagemarker.css';

// 이미지 위에 absolute 포지션 마커(원 + 십자)를 겹쳐 그린다.
// - 클릭 수집: onPick(x, y) 로 e.nativeEvent.offsetX/offsetY 전달.
// - 마커: click(분홍 #F78A9F), peak(초록 #7CE38B).
// - size: 정사각 한 변(px). 게임은 512 고정.
export default function ImageMarker({
  src,
  size,
  click = null, // {x, y} 내 클릭(분홍)
  peak = null, // {x, y} AI peak(초록)
  onPick = null, // (x, y) => void. 주면 클릭 가능.
  alt = '',
}) {
  function handleClick(e) {
    if (!onPick) return;
    const x = e.nativeEvent.offsetX;
    const y = e.nativeEvent.offsetY;
    onPick(x, y);
  }

  return (
    <div
      className="imgmarker"
      style={{ width: size, height: size }}
    >
      <img
        src={src}
        alt={alt}
        width={size}
        height={size}
        draggable={false}
        onClick={handleClick}
        style={{ cursor: onPick ? 'crosshair' : 'default' }}
      />
      {click && (
        <Marker x={click.x} y={click.y} color="#F78A9F" />
      )}
      {peak && <Marker x={peak.x} y={peak.y} color="#7CE38B" />}
    </div>
  );
}

// 원 + 십자 마커 한 개.
function Marker({ x, y, color }) {
  const r = 12;
  const common = { position: 'absolute', background: color, pointerEvents: 'none' };
  return (
    <>
      {/* 원 */}
      <span
        style={{
          position: 'absolute',
          left: x - r,
          top: y - r,
          width: r * 2,
          height: r * 2,
          border: `3px solid ${color}`,
          borderRadius: '50%',
          boxSizing: 'border-box',
          pointerEvents: 'none',
        }}
      />
      {/* 가로선 */}
      <span
        style={{
          ...common,
          left: x - (r + 6),
          top: y - 1,
          width: (r + 6) * 2,
          height: 2,
        }}
      />
      {/* 세로선 */}
      <span
        style={{
          ...common,
          left: x - 1,
          top: y - (r + 6),
          width: 2,
          height: (r + 6) * 2,
        }}
      />
    </>
  );
}
