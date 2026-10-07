/**
 * Abstract product mark: a document outline with three connected vector
 * nodes, standing for chunks placed in an embedding space.
 */
export default function BrandMark({ size = 36 }) {
  return (
    <svg
      className="brand__mark"
      width={size}
      height={size}
      viewBox="0 0 32 32"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M11 7.5h7.2L23 12v12.5H11z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        opacity="0.85"
      />
      <path
        d="M18.2 7.5V12H23"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        opacity="0.85"
      />
      <path
        d="M13.8 20.4l3.1-4 3.2 2.1"
        fill="none"
        stroke="var(--success)"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
      <circle cx="13.8" cy="20.4" r="1.6" fill="currentColor" />
      <circle cx="16.9" cy="16.4" r="1.6" fill="var(--accent-hover)" />
      <circle cx="20.1" cy="18.5" r="1.6" fill="var(--success)" />
    </svg>
  )
}
