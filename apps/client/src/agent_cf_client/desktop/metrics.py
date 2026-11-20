"""Read actual Windows system CPU/physical-memory usage without extra dependencies."""

import ctypes
from ctypes import wintypes
import sys


class MemoryStatus(ctypes.Structure):
    _fields_ = [('length',wintypes.DWORD),('load',wintypes.DWORD), *[(name,ctypes.c_ulonglong) for name in ('total','available','page_total','page_available','virtual_total','virtual_available','extended_available')]]


class SystemMetrics:
    def __init__(self):
        self.previous = None

    def sample(self):
        if sys.platform != 'win32':
            return {}
        try:
            kernel = ctypes.WinDLL('kernel32',use_last_error=True)
            memory = MemoryStatus()
            memory.length = ctypes.sizeof(memory)
            result = {}
            if kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):
                result.update(memory_total_bytes=memory.total,memory_used_bytes=memory.total-memory.available,ram_percent=round((memory.total-memory.available)*100/memory.total,1))
            idle,kernel_time,user = wintypes.FILETIME(),wintypes.FILETIME(),wintypes.FILETIME()
            if kernel.GetSystemTimes(ctypes.byref(idle),ctypes.byref(kernel_time),ctypes.byref(user)):
                ticks = lambda value: (value.dwHighDateTime << 32) | value.dwLowDateTime
                current=(ticks(idle),ticks(kernel_time)+ticks(user))
                if self.previous:
                    delta=current[1]-self.previous[1]
                    if delta>0:
                        result['cpu_percent']=round(max(0,min(100,100*(1-(current[0]-self.previous[0])/delta))),1)
                self.previous=current
            return result
        except OSError:
            return {} # Unsupported/unavailable readings remain unknown, never synthetic zero.
