"""Small native Windows notification icon; UI callbacks are queued by the caller."""

import ctypes as C
from ctypes import wintypes as W
import logging
from pathlib import Path
import threading
import time


class Guid(C.Structure):
    _fields_ = [("a", W.DWORD), ("b", W.WORD), ("c", W.WORD), ("d", W.BYTE * 8)]


class NotifyData(C.Structure):
    _fields_ = [("cbSize", W.DWORD), ("hWnd", W.HWND), ("uID", W.UINT), ("uFlags", W.UINT),
        ("uCallbackMessage", W.UINT), ("hIcon", W.HICON), ("szTip", W.WCHAR * 128),
        ("dwState", W.DWORD), ("dwStateMask", W.DWORD), ("szInfo", W.WCHAR * 256),
        ("uTimeout", W.UINT), ("szInfoTitle", W.WCHAR * 64), ("dwInfoFlags", W.DWORD),
        ("guidItem", Guid), ("hBalloonIcon", W.HICON)]


class WindowsTray:
    def __init__(self, callback):
        self.callback = callback
        self.hwnd = None
        self.ready = threading.Event()
        self.available = False
        self.thread = threading.Thread(target=self.run, name="CF Client Tray", daemon=True)
        self.thread.start()

    def run(self):
        try:
            user = self.user = C.WinDLL("user32", use_last_error=True)
            shell = self.shell = C.WinDLL("shell32", use_last_error=True)
            kernel = C.WinDLL("kernel32", use_last_error=True)
            proc_type = C.WINFUNCTYPE(C.c_ssize_t, W.HWND, W.UINT, W.WPARAM, C.c_ssize_t)

            class WindowClass(C.Structure):
                _fields_ = [("style", W.UINT), ("proc", proc_type), ("extra", C.c_int), ("window_extra", C.c_int),
                    ("instance", W.HINSTANCE), ("icon", W.HICON), ("cursor", W.HANDLE), ("background", W.HANDLE),
                    ("menu", W.LPCWSTR), ("name", W.LPCWSTR)]

            user.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, C.c_ssize_t]
            user.DefWindowProcW.restype = C.c_ssize_t
            user.CreateWindowExW.argtypes = [W.DWORD, W.LPCWSTR, W.LPCWSTR, W.DWORD, C.c_int, C.c_int, C.c_int, C.c_int, W.HWND, W.HMENU, W.HINSTANCE, C.c_void_p]
            user.CreateWindowExW.restype = W.HWND
            user.RegisterClassW.argtypes = [C.POINTER(WindowClass)]
            user.UnregisterClassW.argtypes = [W.LPCWSTR, W.HINSTANCE]
            user.LoadIconW.argtypes = [W.HINSTANCE, C.c_void_p]
            user.LoadIconW.restype = W.HICON
            user.LoadImageW.argtypes = [W.HINSTANCE, W.LPCWSTR, W.UINT, C.c_int, C.c_int, W.UINT]
            user.LoadImageW.restype = W.HANDLE
            user.CreatePopupMenu.restype = W.HMENU
            user.AppendMenuW.argtypes = [W.HMENU, W.UINT, C.c_size_t, W.LPCWSTR]
            user.TrackPopupMenu.argtypes = [W.HMENU, W.UINT, C.c_int, C.c_int, C.c_int, W.HWND, C.c_void_p]
            user.SetForegroundWindow.argtypes = [W.HWND]
            user.DestroyMenu.argtypes = [W.HMENU]
            user.DestroyWindow.argtypes = [W.HWND]
            user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
            shell.Shell_NotifyIconW.argtypes = [W.DWORD, C.POINTER(NotifyData)]
            shell.Shell_NotifyIconW.restype = W.BOOL
            kernel.GetModuleHandleW.argtypes = [W.LPCWSTR]
            kernel.GetModuleHandleW.restype = W.HINSTANCE

            @proc_type
            def callback(hwnd, message, wp, lp):
                if message == 0x8001:
                    if lp in (0x202, 0x203):
                        self.callback("show")
                    elif lp == 0x205:
                        menu = user.CreatePopupMenu()
                        for menu_id, title in ((1, "Mở CF Client"), (3, "Thoát CF Client")):
                            user.AppendMenuW(menu, 0, menu_id, title)
                        point = W.POINT()
                        user.GetCursorPos(C.byref(point))
                        user.SetForegroundWindow(hwnd)
                        selected = user.TrackPopupMenu(menu, 0x100 | 0x2, point.x, point.y, 0, hwnd, None)
                        user.DestroyMenu(menu)
                        if selected:
                            self.callback({1: "show", 3: "exit"}[selected])
                    return 0
                if message == 0x10:
                    user.DestroyWindow(hwnd)
                    return 0
                if message == 2:
                    shell.Shell_NotifyIconW(2, C.byref(self.data))
                    user.PostQuitMessage(0)
                    return 0
                return user.DefWindowProcW(hwnd, message, wp, lp)

            self._callback = callback
            class_name = "AgentCFClientTray"
            wc = WindowClass()
            wc.proc, wc.instance, wc.name = callback, kernel.GetModuleHandleW(None), class_name
            user.RegisterClassW(C.byref(wc))
            self.hwnd = user.CreateWindowExW(0, class_name, "CF Client", 0, 0, 0, 0, 0, None, None, wc.instance, None)
            if not self.hwnd:
                raise C.WinError(C.get_last_error())
            self.data = NotifyData()
            self.data.cbSize, self.data.hWnd, self.data.uID = C.sizeof(NotifyData), self.hwnd, 1
            self.data.uFlags, self.data.uCallbackMessage = 7, 0x8001
            self.hicon_online = None
            self.hicon_offline = None
            online_ico = Path(__file__).resolve().with_name("cf_tray_online.ico")
            offline_ico = Path(__file__).resolve().with_name("cf_tray_offline.ico")
            default_ico = Path(__file__).resolve().with_name("cf_logo.ico")

            if online_ico.is_file():
                self.hicon_online = user.LoadImageW(None, str(online_ico), 1, 16, 16, 0x0010)
            elif default_ico.is_file():
                self.hicon_online = user.LoadImageW(None, str(default_ico), 1, 16, 16, 0x0010)

            if offline_ico.is_file():
                self.hicon_offline = user.LoadImageW(None, str(offline_ico), 1, 16, 16, 0x0010)
            elif default_ico.is_file():
                self.hicon_offline = user.LoadImageW(None, str(default_ico), 1, 16, 16, 0x0010)

            fallback_icon = user.LoadIconW(None, C.c_void_p(32512))
            self.data.hIcon = self.hicon_online or fallback_icon
            self.data.szTip = "CF Client · Đang mở"
            added = False
            for _ in range(5):
                if shell.Shell_NotifyIconW(0, C.byref(self.data)):
                    added = True
                    break
                time.sleep(0.2)
            if not added:
                raise C.WinError(C.get_last_error())
            self.available = True
            self.ready.set()
            message = W.MSG()
            while user.GetMessageW(C.byref(message), None, 0, 0) > 0:
                user.TranslateMessage(C.byref(message))
                user.DispatchMessageW(C.byref(message))
            user.UnregisterClassW(class_name, wc.instance)
            self.available = False
        except Exception:
            logging.exception("Native tray unavailable; keep the desktop window accessible")
            self.ready.set()

    def set_status(self, online: bool, tooltip_text: str = ""):
        if self.available and self.hwnd:
            target_hicon = self.hicon_online if online else self.hicon_offline
            changed = False
            if target_hicon and self.data.hIcon != target_hicon:
                self.data.hIcon = target_hicon
                changed = True
            if tooltip_text:
                tip = ("CF Client · " + tooltip_text).encode("utf-16-le")[:254].decode("utf-16-le", errors="ignore")
                if tip != self.data.szTip:
                    self.data.szTip = tip
                    changed = True
            if changed:
                self.data.uFlags = 7
                self.shell.Shell_NotifyIconW(1, C.byref(self.data))

    def tooltip(self, text):
        if self.available:
            tip = ("CF Client · " + text).encode("utf-16-le")[:254].decode("utf-16-le", errors="ignore")
            if tip == self.data.szTip:
                return
            self.data.szTip = tip
            self.data.uFlags = 7
            self.shell.Shell_NotifyIconW(1, C.byref(self.data))

    def close(self):
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, 0x10, 0, 0)
