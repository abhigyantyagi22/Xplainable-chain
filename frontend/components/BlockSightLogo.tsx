interface BlockSightLogoProps {
  className?: string;
}

/**
 * Block Sight brand mark.
 *
 * Combines three ideas into one unique glyph:
 *   - Shield  → security / fraud protection (the original mark)
 *   - Eye     → "Sight": watching every transaction
 *   - Hexagonal pupil → "Block": a crypto/blockchain block at the centre of vision
 *
 * Uses `currentColor` so it inherits the surrounding text colour.
 */
export default function BlockSightLogo({ className }: BlockSightLogoProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-label="Block Sight logo"
      role="img"
    >
      {/* Shield outline */}
      <path
        d="M16 2.5 L27 6.5 V15 C27 22 22 27 16 29.5 C10 27 5 22 5 15 V6.5 Z"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Eye almond */}
      <path
        d="M8.5 15 Q16 8.8 23.5 15 Q16 21.2 8.5 15 Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
        fill="none"
      />
      {/* Hexagonal "block" pupil */}
      <path
        d="M16 11.7 L19 13.4 V16.6 L16 18.3 L13 16.6 V13.4 Z"
        fill="currentColor"
      />
    </svg>
  );
}
