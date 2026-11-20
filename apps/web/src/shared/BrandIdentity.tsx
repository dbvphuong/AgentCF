/** Static vector identity: no animation or font download on the navigation path. */
export function BrandIdentity() {
  return (
    <>
      <svg className="brand-symbol" width="36" height="36" viewBox="0 0 36 36" fill="none" aria-hidden="true">
        <rect x="0.5" y="0.5" width="35" height="35" rx="10" fill="currentColor" />
        <g stroke="#fff" strokeWidth="2.4" strokeLinecap="square" strokeLinejoin="round">
          <path d="M16 11.5H12a6.5 6.5 0 0 0 0 13h4" />
          <path d="M21 24.5v-13h8M21 17.5h6" />
        </g>
      </svg>
      <img className="brand-wordmark" src="/logos/agent-cf-wordmark.svg" alt="Agent CF" width="134" height="32" />
    </>
  );
}
