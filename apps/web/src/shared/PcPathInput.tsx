import { useEffect, useRef, useState } from "react";
import { Modal, Notice } from "./ui";
import { request, resource } from "./api";
import type { RecordData } from "./api";

export function PcPathInput({ id, value, runnerId, onChange, directoryOnly = false, initialDirectory = "", canBrowse = true }: {
  id: string; value: string; runnerId: string; onChange: (value: string) => void; directoryOnly?: boolean; initialDirectory?: string; canBrowse?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [directory, setDirectory] = useState("");
  const [listing, setListing] = useState<RecordData | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => () => { generation.current++; }, []);
  const close = () => { generation.current++; setOpen(false); setBusy(false); };
  const browse = async (path: string) => {
    const current = ++generation.current;
    setBusy(true); setError(""); setListing(null);
    try {
      const endpoint = `${resource("/v1/runners", runnerId)}/skill-files`;
      const pending = await request<RecordData>(endpoint, "POST", { path: path.trim() || null });
      for (let i = 0; i < 60; i++) {
        if (generation.current !== current) return;
        const state = await request<RecordData>(resource(endpoint, pending.id));
        if (generation.current !== current) return;
        if (state.status === "completed") {
          if (state.result.error) throw Error(state.result.error);
          setListing(state.result); setDirectory(state.result.path); return;
        }
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      throw Error("PC chưa phản hồi. Kiểm tra Client đang chạy bản mới hoặc dán đường dẫn trực tiếp.");
    } catch (e) {
      if (generation.current === current) setError((e as Error).message);
    } finally {
      if (generation.current === current) setBusy(false);
    }
  };
  return <>
    <div className="toolbar">
      <input id={id} value={value} placeholder={directoryOnly ? "Dán đường dẫn thư mục chủ đề đã có trên PC" : "Đường dẫn tuyệt đối tới file .md chính"} autoComplete="off"
        onChange={e => onChange(e.target.value)} style={{ flex: 1, minWidth: 0 }} />
      <button type="button" className="btn btn-outline" disabled={!runnerId || !canBrowse} title={!canBrowse ? "PC chưa online; mở Client/kết nối PC hoặc dán đường dẫn." : undefined} onClick={() => {
        const path = value || initialDirectory;
        setOpen(true); setDirectory(path); void browse(path);
      }}>{directoryOnly ? "Chọn thư mục…" : "Chọn file…"}</button>
    </div>
    <small>{directoryOnly ? "Dùng thư mục chủ đề đã chuẩn bị. Các bước cùng nhận đường dẫn này; không tự tạo thư mục khác." : "Chọn PC rồi nhập đường dẫn hoặc chọn file .md chính. Giữ nguyên các file ref bên cạnh Skill."}</small>
    {!!runnerId && !canBrowse && <small className="muted">PC chưa online hoặc kết nối đã bị gỡ. Kết nối Client để chọn trên PC; bạn vẫn có thể dán đường dẫn.</small>}
    {open && <Modal title={directoryOnly ? "Chọn thư mục chủ đề trên PC" : "Chọn file Skill trên PC"} onClose={close}>
      <div className="toolbar">
        <input aria-label="Thư mục trên PC" value={directory} onChange={e => setDirectory(e.target.value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); if (!busy) void browse(directory); } }} />
        <button type="button" className="btn btn-outline" disabled={busy} onClick={() => void browse(directory)}>Mở thư mục</button>
      </div>
      {error && <Notice error>{error}</Notice>}
      {busy && <Notice>Đang chờ Client trên PC đọc danh sách file…</Notice>}
      {listing && <>
        <div className="toolbar">
          <button type="button" className="btn btn-outline" onClick={() => void browse(listing.parent)}>Lên thư mục cha</button>
          {listing.roots?.map((root: string) => <button type="button" className="btn btn-outline" key={root} onClick={() => void browse(root)}>{root}</button>)}
        </div>
        <p><code>{listing.path}</code></p>
        <div style={{ maxHeight: "40vh", overflow: "auto" }}>
          {listing.entries.filter((entry: RecordData) => !directoryOnly || entry.is_dir).map((entry: RecordData) => <div key={entry.path}>
            <button type="button" className="link-button" onClick={() => {
              if (entry.is_dir) void browse(entry.path);
              else { onChange(entry.path); close(); }
            }}>{entry.is_dir ? "📁 " : "📄 "}{entry.name}</button>
          </div>)}
          {!listing.entries.length && <p>Không có thư mục hoặc file .md.</p>}
        </div>
        {listing.truncated && <p>Chỉ hiện 500 mục đầu. Nhập thư mục cụ thể hơn hoặc dán đường dẫn file.</p>}
        {directoryOnly && <div className="form-actions"><button type="button" className="btn btn-primary" onClick={() => { onChange(listing.path); close(); }}>Dùng thư mục này</button></div>}
      </>}
    </Modal>}
  </>;
}

