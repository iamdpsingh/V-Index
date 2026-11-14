// components/RolewispLogo.tsx — Original ribbon R symbol and wordmark

export function RolewispSymbol({
  size = 32,
  className = '',
  color = '#F28B75', // Coral accent from design tokens
}: {
  size?: number;
  className?: string;
  color?: string;
}) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 48 48"
      width={size}
      height={size}
      fill="none"
      stroke={color}
      strokeWidth="7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M10 39V16C10 9 16 5 23 5C31 5 37 10 37 17C37 24 31 29 23 29H20L36 43" />
    </svg>
  );
}

// Backwards compatibility alias
export const RolewispMark = RolewispSymbol;

export function RolewispLockup({
  size = 32,
  className = '',
}: {
  size?: number;
  className?: string;
}) {
  return (
    <div className={`rolewisp-brand-lockup ${className}`}>
      <RolewispSymbol size={size} />
      <span className="brand-name">Rolewisp</span>
    </div>
  );
}
