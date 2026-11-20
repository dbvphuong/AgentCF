import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { RecordData } from "../../shared/api";

export type ProjectAction = "edit" | "clone" | "toggle" | "delete";

export function ProjectActions({
  project,
  onAction,
}: {
  project: RecordData;
  onAction: (action: ProjectAction, project: RecordData) => void;
}) {
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState<{
    left: number;
    top: number;
  } | null>(null);
  const close = (focus = false) => {
    setPosition(null);
    if (focus) trigger.current?.focus();
  };
  useEffect(() => {
    if (!position) return;
    menu.current
      ?.querySelector<HTMLButtonElement>('[role="menuitem"]')
      ?.focus({ preventScroll: true });
    const outside = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!menu.current?.contains(target) && !trigger.current?.contains(target))
        close();
    };
    const reposition = (event: Event) => {
      if (!menu.current?.contains(event.target as Node)) close();
    };
    document.addEventListener("pointerdown", outside);
    window.addEventListener("resize", reposition);
    window.addEventListener("scroll", reposition, true);
    return () => {
      document.removeEventListener("pointerdown", outside);
      window.removeEventListener("resize", reposition);
      window.removeEventListener("scroll", reposition, true);
    };
  }, [position]);

  const items: { action: ProjectAction; label: string; icon: string }[] = [
    { action: "edit", label: "Sửa", icon: "M12 20h9M16 3l5 5L8 21H3v-5Z" },
    { action: "clone", label: "Nhân bản", icon: "M9 9h12v12H9zM15 9V3H3v12h6" },
    {
      action: "toggle",
      label: project.status === "active" ? "Ngừng hoạt động" : "Kích hoạt lại",
      icon: "M12 2v10M5 5a9 9 0 1 0 14 0",
    },
    {
      action: "delete",
      label: "Xóa",
      icon: "M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7M14 10v7",
    },
  ];
  return (
    <>
      <button
        ref={trigger}
        type="button"
        className={`project-actions-trigger ${position ? "is-open" : ""}`}
        aria-label={`Thao tác Project ${project.name}`}
        aria-haspopup="menu"
        aria-expanded={!!position}
        onClick={() => {
          if (position) {
            close();
            return;
          }
          const rect = trigger.current!.getBoundingClientRect();
          const height = 232;
          const viewport = window.visualViewport;
          const left = viewport?.offsetLeft ?? 0;
          const top = viewport?.offsetTop ?? 0;
          const right = left + (viewport?.width ?? window.innerWidth);
          const bottom = top + (viewport?.height ?? window.innerHeight);
          setPosition({
            left: Math.max(left + 12, Math.min(rect.right - 224, right - 236)),
            top: Math.max(
              top + 12,
              Math.min(
                bottom - height - 12,
                rect.bottom + height + 8 > bottom
                  ? rect.top - height - 8
                  : rect.bottom + 8,
              ),
            ),
          });
        }}
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
        >
          <circle cx="5" cy="12" r="1.7" />
          <circle cx="12" cy="12" r="1.7" />
          <circle cx="19" cy="12" r="1.7" />
        </svg>
      </button>
      {position &&
        createPortal(
          <div
            ref={menu}
            role="menu"
            aria-label={`Thao tác Project ${project.name}`}
            className="project-action-menu"
            style={position}
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                event.stopPropagation();
                close(true);
              }
              if (event.key === "Tab") {
                close(true);
              }
              if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
                event.preventDefault();
                const buttons = Array.from(
                  menu.current!.querySelectorAll<HTMLButtonElement>(
                    '[role="menuitem"]',
                  ),
                );
                const index = buttons.indexOf(
                  document.activeElement as HTMLButtonElement,
                );
                const next =
                  event.key === "Home"
                    ? 0
                    : event.key === "End"
                      ? buttons.length - 1
                      : (index +
                          (event.key === "ArrowDown" ? 1 : -1) +
                          buttons.length) %
                        buttons.length;
                buttons[next].focus();
              }
            }}
          >
            <span className="project-menu-caption">QUẢN LÝ PROJECT</span>
            {items.map((item) => (
              <button
                key={item.action}
                type="button"
                role="menuitem"
                className={`project-menu-item ${item.action === "toggle" ? "project-menu-separated" : ""} ${item.action === "delete" ? "is-danger" : ""}`}
                onClick={() => {
                  close(true);
                  onAction(item.action, project);
                }}
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.65"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d={item.icon} />
                </svg>
                {item.label}
              </button>
            ))}
          </div>,
          document.body,
        )}
    </>
  );
}
