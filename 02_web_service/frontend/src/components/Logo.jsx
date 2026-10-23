import '../styles/logo.css';

// XRAY.zip 텍스트 로고 (이미지 없이 CSS만).
// XRAY = 밝은 아이보리/화이트, .zip = 코랄 핑크.
// size: 'sm' | 'md' | 'lg' (기본 md)
export default function Logo({ size = 'md', className = '' }) {
  return (
    <span className={`xz-logo xz-logo--${size} ${className}`} aria-label="XRAY.zip">
      <span className="xz-logo__scan" aria-hidden="true" />
      <span className="xz-logo__main">XRAY</span>
      <span className="xz-logo__zip">.zip</span>
    </span>
  );
}
