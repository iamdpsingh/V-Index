export function RolewispMark({
  className = '',
  size = 26,
}: {
  className?: string;
  size?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      {/* Primary upper-left framing stroke */}
      <path
        d="M 5 21 V 7 H 17"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Fine offset lower-right stroke resolving into the open corner aperture */}
      <path
        d="M 23 11 V 23 H 11"
        stroke="currentColor"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {/* Focal dot denoting index precision */}
      <circle cx="14" cy="14" r="1.5" fill="currentColor" opacity="0.75" />
    </svg>
  );
}

