"""CF Client modern desktop onboarding and resident user-session application."""

import json
import logging
import os
import platform
from queue import Queue, Empty
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog
from urllib.parse import urlparse
import webbrowser

import customtkinter as ctk
import httpx

from agent_cf_client.config import ClientConfig
from agent_cf_client.connection.client_session import ClientSessionManager
from agent_cf_client.desktop.daemon import ClientDaemon
from agent_cf_client.desktop.links import parse_connection_link
from agent_cf_client.desktop.metrics import SystemMetrics
from agent_cf_client.desktop.native_tray import WindowsTray
from agent_cf_client.desktop.windows import profile_dir, startup_enabled, set_startup, register_protocol


# ---------------------------------------------------------------------------
# Brand Palette (Agent CF Violet Theme)
# ---------------------------------------------------------------------------
VIOLET_PRIMARY = ("#6e5797", "#8268ad")
VIOLET_HOVER = ("#5c4782", "#9b82c4")
VIOLET_SUBTLE = ("#f3effa", "#291f3e")
VIOLET_SUBTLE_HOVER = ("#e7dff5", "#382955")
VIOLET_SUBTLE_BORDER = ("#e3daf0", "#463467")
VIOLET_SUBTLE_TEXT = ("#5a437e", "#ddd3ea")

CARD_BG = ("#ffffff", "#20192f")
CARD_BORDER = ("#ece6f3", "#382c50")
CANVAS_BG = ("#f8f7fa", "#151020")
PROGRESS_TRACK = ("#eeeaf5", "#2d2342")

TEXT_PRIMARY = ("#241e30", "#f7f4fa")
TEXT_MUTED = ("#766e84", "#a39bb0")

SUCCESS_BG = ("#e8f8f0", "#13382c")
SUCCESS_TEXT = ("#0d7847", "#4ade80")

WARNING_BG = ("#fff8eb", "#3d2b10")
WARNING_TEXT = ("#925505", "#fbbf24")

DANGER_BG = ("#fdf0f2", "#3a1d28")
DANGER_TEXT = ("#ad213f", "#fca5a5")


class LogViewerWindow(ctk.CTkToplevel):
    def __init__(self, parent, folder: Path):
        super().__init__(parent)
        self.folder = folder
        self.log_path = folder / "client.log"
        self.title("Nhật ký hoạt động (Logs) - CF Client")
        self.geometry("680x480")
        self.minsize(520, 360)
        self.configure(fg_color=CANVAS_BG)

        ico_path = Path(__file__).resolve().with_name("cf_logo.ico")
        if ico_path.is_file():
            self.iconbitmap(str(ico_path))

        self.after(100, self.lift)

        # Header
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(14, 6))

        title_box = ctk.CTkFrame(top, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="Nhật ký CF Client", font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_box, text=f"File: {self.log_path.name}", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(anchor="w")

        self.autoscroll_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(top, text="Tự cuộn xuống", variable=self.autoscroll_var, font=ctk.CTkFont(size=11), checkbox_height=18, checkbox_width=18, fg_color=VIOLET_PRIMARY).pack(side="right")

        # Text Box
        self.textbox = ctk.CTkTextbox(self, font=ctk.CTkFont(family="Consolas", size=11), wrap="none", corner_radius=8, border_width=1, border_color=CARD_BORDER)
        self.textbox.pack(fill="both", expand=True, padx=18, pady=8)

        # Bottom Actions
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=18, pady=(6, 14))

        ctk.CTkButton(bottom, text="Làm mới", command=self.reload, width=90, fg_color=CARD_BG, hover_color=VIOLET_SUBTLE_HOVER, text_color=TEXT_PRIMARY, border_width=1, border_color=CARD_BORDER, corner_radius=6).pack(side="left", padx=(0, 8))
        self.copy_btn = ctk.CTkButton(bottom, text="Sao chép tất cả", command=self.copy_all, width=120, fg_color=CARD_BG, hover_color=VIOLET_SUBTLE_HOVER, text_color=TEXT_PRIMARY, border_width=1, border_color=CARD_BORDER, corner_radius=6)
        self.copy_btn.pack(side="left", padx=(0, 8))
        ctk.CTkButton(bottom, text="Mở file log", command=self.open_file, width=100, fg_color=CARD_BG, hover_color=VIOLET_SUBTLE_HOVER, text_color=TEXT_PRIMARY, border_width=1, border_color=CARD_BORDER, corner_radius=6).pack(side="left")

        ctk.CTkButton(bottom, text="Đóng", command=self.destroy, width=80, fg_color=VIOLET_PRIMARY, hover_color=VIOLET_HOVER, text_color="#ffffff", corner_radius=6).pack(side="right")

        self.reload()

    def reload(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        if self.log_path.exists():
            try:
                lines = self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                content = "\n".join(lines[-1000:])
                self.textbox.insert("1.0", content)
            except Exception as e:
                self.textbox.insert("1.0", f"Không đọc được file log: {e}")
        else:
            self.textbox.insert("1.0", "Chưa có file log (client.log sẽ được tạo khi có hoạt động).")
        self.textbox.configure(state="disabled")
        if self.autoscroll_var.get():
            self.textbox.see("end")

    def copy_all(self):
        self.clipboard_clear()
        self.clipboard_append(self.textbox.get("1.0", "end"))
        self.copy_btn.configure(text="Đã chép! ✓")
        self.after(1500, lambda: self.copy_btn.configure(text="Sao chép tất cả"))

    def open_file(self):
        if self.log_path.exists() and sys.platform == "win32":
            os.startfile(str(self.log_path))


class ClientWindow:
    def __init__(self, root, folder=None, link=None, background=False):
        self.root = root
        self.folder = folder or profile_dir()
        self.folder.mkdir(parents=True, exist_ok=True)
        self.events = Queue()
        self.manager = ClientSessionManager(self.folder / "credentials.dpapi", protect_credentials=True)
        self.daemon = None
        self.closing = False
        self.operation = False
        self.preview_key = None
        self.metrics_reader = SystemMetrics()
        self.log_window = None
        self.last_metrics_sample = 0
        self.run_id = None

        creds = self.manager.get_credentials()
        self.server = ctk.StringVar(value=creds["server_url"] if creds else "http://127.0.0.1:8000")
        self.code = ctk.StringVar()
        self.name = ctk.StringVar(value=platform.node())
        self.status = ctk.StringVar(value="Chưa kết nối · Trên Web Center chọn PC → Connect PC")
        self.error = ctk.StringVar()
        self.autostart = ctk.BooleanVar(value=startup_enabled())

        ctk.set_appearance_mode("System")
        root.title("CF Client")
        root.geometry("440x515")
        root.minsize(430, 490)
        root.configure(fg_color=CANVAS_BG)

        # Set official CF Logo icon
        ico_path = Path(__file__).resolve().with_name("cf_logo.ico")
        if ico_path.is_file():
            try:
                root.iconbitmap(str(ico_path))
            except Exception:
                pass
            if sys.platform == "win32":
                try:
                    import ctypes
                    hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()
                    hicon = ctypes.windll.user32.LoadImageW(None, str(ico_path), 1, 32, 32, 0x0010)
                    hicon_sm = ctypes.windll.user32.LoadImageW(None, str(ico_path), 1, 16, 16, 0x0010)
                    if hicon:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
                    if hicon_sm:
                        ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon_sm)
                except Exception:
                    pass

        root.protocol("WM_DELETE_WINDOW", self.hide)
        root.bind("<Alt-k>", lambda event: self.connect())
        root.bind("<Control-q>", lambda event: self.request_exit())
        root.bind("<Control-l>", lambda event: self.show_logs())

        frame = ctk.CTkFrame(root, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=16)

        # ---------------------------------------------------------------------
        # 1. Header (Logo CF + Title + Machine tag)
        # ---------------------------------------------------------------------
        header = ctk.CTkFrame(frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        # Brand Logo Canvas (36x36)
        png_path = Path(__file__).resolve().with_name("cf_logo_36.png")
        if not png_path.is_file():
            png_path = Path(__file__).resolve().with_name("cf_logo.png")
        if png_path.is_file():
            try:
                self.logo_img = tk.PhotoImage(file=str(png_path))
                if self.logo_img.width() > 36:
                    factor = max(1, self.logo_img.width() // 36)
                    self.logo_img = self.logo_img.subsample(factor, factor)
                logo_canvas = tk.Canvas(header, width=36, height=36, highlightthickness=0, bg=root._apply_appearance_mode(CANVAS_BG))
                logo_canvas.create_image(18, 18, image=self.logo_img)
                logo_canvas.pack(side="left", padx=(0, 10))
            except Exception:
                pass

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.pack(side="left")
        ctk.CTkLabel(title_box, text="CF Client", font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Cầu nối Web Center với PC Runner", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED).pack(anchor="w")

        # Machine badge
        host_badge = ctk.CTkFrame(header, fg_color=VIOLET_SUBTLE, corner_radius=8, border_width=1, border_color=VIOLET_SUBTLE_BORDER)
        host_badge.pack(side="right", pady=4)
        ctk.CTkLabel(host_badge, text=f"PC: {self.name.get()}", font=ctk.CTkFont(size=11, weight="bold"), text_color=VIOLET_SUBTLE_TEXT).pack(padx=10, pady=4)

        # ---------------------------------------------------------------------
        # 5. Footer: Startup Checkbox + Thu xuống khay Button (anchored at bottom)
        # ---------------------------------------------------------------------
        footer = ctk.CTkFrame(frame, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        ctk.CTkCheckBox(footer, text="Khởi động cùng Windows", variable=self.autostart, command=self.change_startup, font=ctk.CTkFont(size=11), fg_color=VIOLET_PRIMARY, checkbox_height=16, checkbox_width=16).pack(side="left")

        ctk.CTkButton(
            footer,
            text="Thu xuống khay",
            command=self.hide,
            fg_color=VIOLET_SUBTLE,
            hover_color=VIOLET_SUBTLE_HOVER,
            text_color=VIOLET_SUBTLE_TEXT,
            border_width=1,
            border_color=VIOLET_SUBTLE_BORDER,
            height=28,
            corner_radius=6,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(side="right")

        # ---------------------------------------------------------------------
        # 4. Action Buttons (anchored right above footer)
        # ---------------------------------------------------------------------
        actions_frame = ctk.CTkFrame(frame, fg_color="transparent")
        actions_frame.pack(fill="x", side="bottom", pady=(0, 10))

        self.web_button = ctk.CTkButton(actions_frame, text="Mở Web Center ↗", command=self.open_web, fg_color=VIOLET_PRIMARY, hover_color=VIOLET_HOVER, height=36, font=ctk.CTkFont(size=12, weight="bold"), corner_radius=8)
        self.web_button.pack(fill="x", pady=(0, 6))
        if not creds:
            self.web_button.configure(state="disabled")

        ctk.CTkButton(actions_frame, text="Xem nhật ký hoạt động", command=self.show_logs, fg_color=CARD_BG, hover_color=VIOLET_SUBTLE_HOVER, text_color=TEXT_PRIMARY, border_width=1, border_color=CARD_BORDER, height=32, corner_radius=6, font=ctk.CTkFont(size=11, weight="bold")).pack(fill="x")

        if not os.environ.get("AGENT_CF_CLIENT_EXE"):
            ctk.CTkButton(actions_frame, text="Đăng ký mở từ Web", command=self.register, fg_color="transparent", hover_color=VIOLET_SUBTLE_HOVER, text_color=VIOLET_SUBTLE_TEXT, height=24, corner_radius=6, font=ctk.CTkFont(size=11)).pack(fill="x", pady=(4, 0))

        # ---------------------------------------------------------------------
        # 2. Status & Connection Card
        # ---------------------------------------------------------------------
        self.status_card = ctk.CTkFrame(frame, corner_radius=10, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        self.status_card.pack(fill="x", pady=(0, 10))

        status_top = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_top.pack(fill="x", padx=16, pady=(12, 6))

        # Status Pill Badge (e.g. ● Trực tuyến)
        self.status_badge = ctk.CTkFrame(status_top, fg_color=SUCCESS_BG, corner_radius=8)
        self.status_badge.pack(side="left")
        self.status_badge_text = ctk.CTkLabel(self.status_badge, text="● Trực tuyến", font=ctk.CTkFont(size=11, weight="bold"), text_color=SUCCESS_TEXT)
        self.status_badge_text.pack(padx=8, pady=3)

        # Server Host display
        self.server_host_label = ctk.CTkLabel(status_top, text=self._format_server_host(), font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.server_host_label.pack(side="right")

        # Main Status Text
        self.status_label = ctk.CTkLabel(self.status_card, textvariable=self.status, font=ctk.CTkFont(size=13, weight="bold"), text_color=TEXT_PRIMARY, wraplength=380, justify="left")
        self.status_label.pack(anchor="w", padx=16, pady=(0, 12))

        # Connect button (shown only during pairing preview)
        self.connect_button = ctk.CTkButton(self.status_card, text="Xác nhận kết nối", command=self.connect, fg_color=VIOLET_PRIMARY, hover_color=VIOLET_HOVER, height=34, font=ctk.CTkFont(size=12, weight="bold"), corner_radius=8)

        # Error Banner (Hidden when error is empty)
        self.error_frame = ctk.CTkFrame(self.status_card, fg_color=DANGER_BG, corner_radius=8, border_width=1, border_color=("#f9cdd5", "#5c2130"))
        self.error_label = ctk.CTkLabel(self.error_frame, textvariable=self.error, text_color=DANGER_TEXT, font=ctk.CTkFont(size=12), wraplength=380, justify="left")
        self.error_label.pack(padx=12, pady=8)

        # ---------------------------------------------------------------------
        # 3. System Telemetry Card
        # ---------------------------------------------------------------------
        self.telemetry_card = ctk.CTkFrame(frame, corner_radius=10, fg_color=CARD_BG, border_width=1, border_color=CARD_BORDER)
        self.telemetry_card.pack(fill="x", pady=(0, 10))

        telem_header = ctk.CTkFrame(self.telemetry_card, fg_color="transparent")
        telem_header.pack(fill="x", padx=16, pady=(10, 4))
        ctk.CTkLabel(telem_header, text="Tài nguyên PC", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_MUTED).pack(side="left")

        # CPU Row
        cpu_row = ctk.CTkFrame(self.telemetry_card, fg_color="transparent")
        cpu_row.pack(fill="x", padx=16, pady=(4, 2))
        ctk.CTkLabel(cpu_row, text="CPU", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.cpu_label = ctk.CTkLabel(cpu_row, text="--%", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_PRIMARY)
        self.cpu_label.pack(side="right")
        self.cpu_bar = ctk.CTkProgressBar(self.telemetry_card, height=6, corner_radius=3, fg_color=PROGRESS_TRACK, progress_color=VIOLET_PRIMARY)
        self.cpu_bar.pack(fill="x", padx=16, pady=(0, 8))
        self.cpu_bar.set(0)

        # RAM Row
        ram_row = ctk.CTkFrame(self.telemetry_card, fg_color="transparent")
        ram_row.pack(fill="x", padx=16, pady=(2, 2))
        ctk.CTkLabel(ram_row, text="RAM", font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_PRIMARY).pack(side="left")
        self.ram_label = ctk.CTkLabel(ram_row, text="-- / -- GB (--%)", font=ctk.CTkFont(size=11), text_color=TEXT_MUTED)
        self.ram_label.pack(side="right")
        self.ram_bar = ctk.CTkProgressBar(self.telemetry_card, height=6, corner_radius=3, fg_color=PROGRESS_TRACK, progress_color=VIOLET_PRIMARY)
        self.ram_bar.pack(fill="x", padx=16, pady=(0, 12))
        self.ram_bar.set(0)

        self.tray = WindowsTray(lambda action: self.events.put(("tray", action)))
        if link:
            self.accept_link(link)
        elif creds:
            self.start_daemon()
        if background:
            root.after(1000, self.hide)
        root.after(200, self.poll)

    def _format_server_host(self):
        try:
            parsed = urlparse(self.server.get().strip())
            return f"Server: {parsed.netloc or '127.0.0.1:8000'}"
        except Exception:
            return "Server: 127.0.0.1:8000"

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        if self.tray.available:
            self.root.withdraw()
        else:
            self.root.iconify()

    def show_logs(self):
        if self.log_window is None or not self.log_window.winfo_exists():
            self.log_window = LogViewerWindow(self.root, self.folder)
        else:
            self.log_window.lift()
            self.log_window.focus()
            self.log_window.reload()

    def accept_link(self, value):
        self.show()
        try:
            link = parse_connection_link(value)
            if self.operation:
                self.error.set("Đang xử lý kết nối, vui lòng đợi rồi thử lại.")
                return
            if self.daemon and self.daemon.busy:
                raise ValueError("Đang có công việc. Chờ việc kết thúc trước khi ghép nối PC khác.")
            self.server.set(link.server_url)
            self.code.set(link.pairing_code)
            self.server_host_label.configure(text=self._format_server_host())
            self.preview_key = None
            self.web_button.configure(state="normal")
            self.review()
        except ValueError as exc:
            self.error.set(str(exc))

    def network(self, action, name):
        self.operation = True
        self.connect_button.configure(state="disabled")
        self.error.set("")
        def run():
            try:
                self.events.put((name, action()))
            except Exception as exc:
                logging.warning("Connection operation failed: %s (%s)", name, exc)
                message = None
                if isinstance(exc, (ConnectionError, ValueError)) and str(exc).strip():
                    message = str(exc).strip()
                elif hasattr(exc, "response"):
                    try:
                        message = exc.response.json().get("detail")
                    except Exception:
                        pass
                if not message:
                    message = "Không kết nối được hoặc mã không hợp lệ/đã dùng/hết hạn. Kiểm tra Server hoặc tạo mã mới trên Web."
                self.events.put(("operation_error", message))
        threading.Thread(target=run, name="CF Client Connect", daemon=True).start()

    def review(self):
        try:
            server = ClientConfig(server_url=self.server.get().strip()).server_url.rstrip("/")
            code = self.code.get().strip()
            if not code:
                raise ValueError("Nhập mã ghép nối từ Connect PC trên Web")
            key = (server, code)
            self.status.set("Đang kiểm tra mã ghép nối…")
            def inspect():
                with httpx.Client(timeout=10) as client:
                    response = client.post(server + "/v1/pairing-codes/inspect", json={"pairing_code": code})
                    if response.status_code != 200:
                        detail = None
                        try:
                            detail = response.json().get("detail")
                        except Exception:
                            pass
                        raise ConnectionError(detail or "Mã ghép nối không hợp lệ, đã dùng hoặc hết hạn.")
                    return key, response.json()
            self.network(inspect, "preview")
        except ValueError as exc:
            self.error.set(str(exc))

    def connect(self):
        if self.operation:
            return
        code = self.code.get().strip()
        if not code:
            creds = self.manager.get_credentials()
            if creds and self.server.get().rstrip("/") == creds["server_url"].rstrip("/"):
                self.start_daemon()
            else:
                self.error.set("Mở Connect PC trên Web để lấy mã ghép nối.")
            return
        if self.daemon and self.daemon.busy:
            self.error.set("Chờ việc hiện tại kết thúc trước khi đổi kết nối.")
            return
        key = (self.server.get().strip().rstrip("/"), code)
        if self.preview_key != key:
            self.review()
            return
        if self.manager.get_credentials() and not messagebox.askokcancel("Thay kết nối PC", "Ghép nối mới sẽ thay kết nối hiện tại của Client này. Tiếp tục?", parent=self.root):
            return
        def pair():
            if self.daemon:
                self.daemon.shutdown()
                self.daemon.thread.join(timeout=15)
                if self.daemon.thread.is_alive():
                    raise RuntimeError("Client is still draining")
            from agent_cf_client.desktop.identity import device_identity
            return self.manager.pair(key[0], key[1], client_version="0.3.4", machine_fingerprint=platform.node(), **device_identity(self.folder))
        self.network(pair, "paired")

    def start_daemon(self):
        if self.daemon and self.daemon.thread and self.daemon.thread.is_alive():
            self.show()
            return
        self.daemon = ClientDaemon(self.manager, self.folder, lambda event: self.events.put(("status", event)))
        self.daemon.start()

    def paste_link(self):
        value = simpledialog.askstring("Liên kết từ Web Center", "Dán liên kết kết nối được sao chép từ Connect PC:", parent=self.root)
        if value:
            self.accept_link(value.strip())

    def open_web(self):
        try:
            server = ClientConfig(server_url=self.server.get().strip()).server_url.rstrip("/")
            webbrowser.open(server + ("/#runs/" + self.run_id if self.run_id else "/#pc"))
        except ValueError as exc:
            self.error.set(str(exc))

    def register(self):
        try:
            register_protocol()
            self.status.set("Đã đăng ký. Trên Web bấm Mở CF Client để ghép nối.")
        except OSError:
            self.error.set("Không đăng ký được liên kết Windows. Hãy dùng bộ cài CF Client.")

    def change_startup(self):
        try:
            set_startup(self.autostart.get())
        except OSError:
            self.error.set("Không cập nhật được tùy chọn khởi động Windows.")
            self.autostart.set(startup_enabled())

    def request_exit(self):
        if self.daemon and self.daemon.busy and not messagebox.askokcancel("Đợi công việc hoàn tất", "Client sẽ ngừng nhận việc và thoát sau khi việc hiện tại kết thúc. Tiếp tục?", parent=self.root):
            return
        self.closing = True
        self.status.set("Đang ngừng nhận việc và chờ công việc hiện tại…")
        if self.daemon:
            self.daemon.shutdown()

    def poll(self):
        # 1. Check inbox requests
        inbox = self.folder / "requests"
        if inbox.exists():
            for path in list(inbox.glob("*.json"))[:8]:
                try:
                    if path.stat().st_size > 8192:
                        continue
                    item = json.loads(path.read_text(encoding="utf-8"))
                    if not isinstance(item, dict) or (item.get("link") is not None and not isinstance(item["link"], str)):
                        raise ValueError("Invalid connection request")
                    self.accept_link(item["link"]) if item.get("link") else self.show()
                except (OSError, ValueError, KeyError):
                    self.error.set("Yêu cầu mở Client không hợp lệ.")
                finally:
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        logging.warning("Connection inbox is temporarily locked")

        # 2. Update telemetry metrics every 2 seconds
        now = time.monotonic()
        if now - self.last_metrics_sample >= 2.0:
            self.last_metrics_sample = now
            try:
                sample = self.metrics_reader.sample()
                if "cpu_percent" in sample:
                    cpu = sample["cpu_percent"]
                    self.cpu_label.configure(text=f"{cpu}%")
                    self.cpu_bar.set(min(1.0, max(0.0, cpu / 100.0)))
                if "ram_percent" in sample:
                    ram = sample["ram_percent"]
                    used_gb = round(sample.get("memory_used_bytes", 0) / (1024**3), 1)
                    tot_gb = round(sample.get("memory_total_bytes", 0) / (1024**3), 1)
                    self.ram_label.configure(text=f"{used_gb} / {tot_gb} GB ({ram}%)")
                    self.ram_bar.set(min(1.0, max(0.0, ram / 100.0)))
            except Exception:
                pass

        # 3. Process events queue
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind in ("preview", "paired", "operation_error"):
                    self.operation = False
                    self.connect_button.configure(state="normal")
                if kind == "preview":
                    key, data = value
                    if key == (self.server.get().strip().rstrip("/"), self.code.get().strip()):
                        self.preview_key = key
                        self.name.set(data["name"])
                        self.status.set("Yêu cầu ghép nối từ Web Center")
                elif kind == "paired":
                    self.name.set(value["runner"]["name"])
                    self.code.set("")
                    self.preview_key = None
                    self.status.set("Đã ghép nối; đang mở phiên Client…")
                    self.web_button.configure(state="normal")
                    self.start_daemon()
                elif kind == "operation_error":
                    self.error.set(value)
                elif kind == "status":
                    self.status.set(value["message"])
                    self.run_id = value.get("run_id", self.run_id)
                    self.tray.tooltip(value["message"])
                    if value["state"] == "error":
                        self.error.set(value["message"])
                elif kind == "tray":
                    {"show": self.show, "exit": self.request_exit}[value]()
        except Empty:
            pass

        # 4. Update UI element visibilities and indicators
        # Connect button (shown only during pairing preview)
        if self.preview_key:
            if not self.connect_button.winfo_ismapped():
                self.connect_button.pack(fill="x", padx=16, pady=(0, 12))
        else:
            if self.connect_button.winfo_ismapped():
                self.connect_button.pack_forget()

        # Error banner
        err = self.error.get().strip()
        if err:
            if not self.error_frame.winfo_ismapped():
                self.error_frame.pack(fill="x", padx=16, pady=(4, 12))
        else:
            if self.error_frame.winfo_ismapped():
                self.error_frame.pack_forget()

        # Status badge & indicator
        st = self.status.get().lower()
        is_online = False
        if err:
            self.status_badge.configure(fg_color=DANGER_BG)
            self.status_badge_text.configure(text="● Gián đoạn", text_color=DANGER_TEXT)
            is_online = False
        elif "đã kết nối" in st or "sẵn sàng" in st or "hoàn thành" in st:
            self.status_badge.configure(fg_color=SUCCESS_BG)
            self.status_badge_text.configure(text="● Trực tuyến", text_color=SUCCESS_TEXT)
            is_online = True
        elif "đang thực hiện" in st or "running" in st:
            self.status_badge.configure(fg_color=VIOLET_SUBTLE)
            self.status_badge_text.configure(text="⚡ Đang chạy", text_color=VIOLET_SUBTLE_TEXT)
            is_online = True
        elif "đang kết nối" in st or "kiểm tra" in st or "chờ" in st or "paused" in st or "yêu cầu" in st:
            self.status_badge.configure(fg_color=WARNING_BG)
            self.status_badge_text.configure(text="● Chờ kết nối", text_color=WARNING_TEXT)
            is_online = False
        else:
            self.status_badge.configure(fg_color=VIOLET_SUBTLE)
            self.status_badge_text.configure(text="● Chưa kết nối", text_color=TEXT_MUTED)
            is_online = False

        if self.closing and (not self.daemon or not self.daemon.thread.is_alive()):
            self.tray.close()
            self.root.destroy()
            return
        self.tray.set_status(online=is_online, tooltip_text=self.status.get())
        self.root.after(200, self.poll)
