import type { IconProps } from "./types";

export function SettingsIcon({ size = 20, fillOpacity = 1, className, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      fillOpacity={fillOpacity}
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
      {...props}
    >
      <path d="M3.5 6h3M11 6h9.5M3.5 12H14M18.5 12h2M3.5 18h5M13 18h7.5" />
      <circle cx="9" cy="6" r="2" />
      <circle cx="16.5" cy="12" r="2" />
      <circle cx="11" cy="18" r="2" />
    </svg>
  );
}
