import { useEffect } from "react";
import { createPortal } from "react-dom";
import { CloseIcon } from "./icons";
import "./toast.css";

export type ToastMessage = {
  tone: "success" | "warning" | "error";
  text: string;
};

export function Toast({ message, onDismiss }: {
  message: ToastMessage | null;
  onDismiss: () => void;
}) {
  useEffect(() => {
    if (!message) return;
    const timer = window.setTimeout(onDismiss, 6000);
    return () => window.clearTimeout(timer);
  }, [message, onDismiss]);

  if (!message) return null;
  // Native modal dialogs are in the browser's top layer. Put an error inside
  // the open dialog so its toast stays visible and its close button usable.
  const target = message.tone === "error"
    ? Array.from(document.querySelectorAll("dialog[open]")).at(-1) ?? document.body
    : document.body;
  return createPortal(
    <div className={`toast toast-${message.tone}`} role={message.tone === "error" ? "alert" : "status"} aria-atomic="true">
      <span className="toast-symbol" aria-hidden="true">{message.tone === "success" ? "✓" : "!"}</span>
      <div><strong>{message.tone === "success" ? "Thành công" : message.tone === "error" ? "Không thực hiện được" : "Lưu ý"}</strong><p>{message.text}</p></div>
      <button type="button" aria-label="Đóng thông báo" onClick={onDismiss}><CloseIcon size={18} /></button>
    </div>,
    target,
  );
}
