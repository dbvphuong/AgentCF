import type { IconProps } from "./types";

export function RobotsIcon({ size = 20, fillOpacity = 1, className, ...props }: IconProps) {
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
      <rect x="3.5" y="7.5" width="17" height="13" rx="3" />
      <path d="M12 7.5V5M1.5 12v4M22.5 12v4M9 17h6" />
      <circle cx="12" cy="3.5" r="1.5" />
      <circle cx="8.5" cy="12.5" r="1" fill="currentColor" stroke="none" />
      <circle cx="15.5" cy="12.5" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
