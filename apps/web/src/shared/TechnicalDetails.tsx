import { useState } from "react";

export function TechnicalDetails({ values }: { values: Record<string, unknown> }) {
  const [error, setError] = useState("");
  return <details className="technical-details">
    <summary>Chi tiết kỹ thuật</summary>
    {error && <p role="status">{error}</p>}
    <dl>{Object.entries(values).filter(([, value]) => value != null && value !== "").map(([label, value]) => {
      const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
      return <div key={label}>
        <dt>{label}</dt><dd><pre style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{text}</pre>
          <button type="button" className="btn btn-outline btn-sm" onClick={event => {
            event.stopPropagation();
            navigator.clipboard.writeText(text).then(() => setError("Đã sao chép.")).catch(() => setError("Hãy chọn và sao chép nội dung trực tiếp."));
          }}>Sao chép {label}</button>
        </dd>
      </div>;
    })}</dl>
  </details>;
}
