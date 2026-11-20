import type { IconProps } from "./types";

export function AgentsIcon({ size = 20, fillOpacity = 1, className, ...props }: IconProps) {
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
      <circle cx="12" cy="5" r="2.5" />
      <path d="M12 7.5v6M5 17v-3.5h14V17" />
      <circle cx="5" cy="19" r="2" />
      <circle cx="19" cy="19" r="2" />
    </svg>
  );
}
