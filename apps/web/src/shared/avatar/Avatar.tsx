import { useState } from "react";
import type { CSSProperties } from "react";

export type AvatarSize = "xs" | "sm" | "md" | "lg" | "xl" | number;
export type AvatarStatus = "online" | "offline" | "busy" | "idle";
export type AvatarShape = "circle" | "rounded";

export interface AvatarProps {
  name: string;
  src?: string;
  size?: AvatarSize;
  status?: AvatarStatus;
  shape?: AvatarShape;
  className?: string;
  style?: CSSProperties;
}

const SIZE_MAP: Record<string, number> = {
  xs: 20,
  sm: 24,
  md: 32,
  lg: 40,
  xl: 48,
};

const FONT_SIZE_MAP: Record<string, number> = {
  xs: 9,
  sm: 11,
  md: 13,
  lg: 16,
  xl: 19,
};

const GRADIENTS = [
  "linear-gradient(135deg, #8268ad, #554474)",
  "linear-gradient(135deg, #6e5797, #42325c)",
  "linear-gradient(135deg, #9b7ec9, #6e5797)",
  "linear-gradient(135deg, #7c62a8, #302747)",
  "linear-gradient(135deg, #8f74b8, #4c3c66)",
];

function getInitials(name: string): string {
  if (!name) return "?";
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) {
    return parts[0].substring(0, 2).toUpperCase();
  }
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function getGradient(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % GRADIENTS.length;
  return GRADIENTS[index];
}

export function Avatar({
  name,
  src,
  size = "md",
  status,
  shape = "circle",
  className = "",
  style,
}: AvatarProps) {
  const [imgError, setImgError] = useState(false);
  const px = typeof size === "number" ? size : SIZE_MAP[size] || 32;
  const fontSize =
    typeof size === "number" ? Math.round(size * 0.42) : FONT_SIZE_MAP[size] || 13;
  const borderRadius = shape === "circle" ? "50%" : "22%";
  const initials = getInitials(name);
  const background = getGradient(name);

  const containerStyle: CSSProperties = {
    position: "relative",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    width: px,
    height: px,
    borderRadius,
    flexShrink: 0,
    userSelect: "none",
    ...style,
  };

  const statusDotSize = Math.max(6, Math.round(px * 0.28));

  return (
    <div
      className={`app-avatar ${className}`}
      style={containerStyle}
      title={name}
      aria-label={name}
    >
      {src && !imgError ? (
        <img
          src={src}
          alt={name}
          onError={() => setImgError(true)}
          style={{
            width: "100%",
            height: "100%",
            borderRadius,
            objectFit: "cover",
            display: "block",
          }}
        />
      ) : (
        <div
          style={{
            width: "100%",
            height: "100%",
            borderRadius,
            background,
            color: "#ffffff",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 650,
            fontSize,
            letterSpacing: "0.5px",
            boxShadow: "inset 0 1px 1px rgba(255, 255, 255, 0.2)",
          }}
        >
          {initials}
        </div>
      )}

      {status && (
        <span
          className={`avatar-status-dot status-${status}`}
          style={{
            position: "absolute",
            bottom: 0,
            right: 0,
            width: statusDotSize,
            height: statusDotSize,
            borderRadius: "50%",
            border: "2px solid #ffffff",
            boxSizing: "content-box",
            backgroundColor:
              status === "online"
                ? "var(--success, #22c55e)"
                : status === "busy"
                  ? "var(--danger, #ef4444)"
                  : status === "idle"
                    ? "var(--warning, #f59e0b)"
                    : "#a69fad",
          }}
        />
      )}
    </div>
  );
}
