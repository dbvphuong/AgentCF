import type { IconProps } from "./types";

export function SkillsIcon({ size = 20, fillOpacity = 1, className, ...props }: IconProps) {
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
      <path d="M14 3.5H6a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-9l-6-6Z" />
      <path d="M14 3.5v6h6M8 15l2.5 2.5L16 12" />
    </svg>
  );
}
