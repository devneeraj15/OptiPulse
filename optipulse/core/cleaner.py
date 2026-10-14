"""
OptiPulse - Universal Cross-Platform Memory & Cache Cleaner
Supports: Windows (Win32 WorkingSet Trim), macOS (purge), Linux (drop_caches / user trim)
"""

import os
import sys
import platform
import subprocess
import gc


def clean_ram_windows():
    """Flush working sets of idle background processes using Win32 API."""
    import ctypes
    from ctypes import wintypes
    
    psapi = ctypes.WinDLL('psapi.dll')
    kernel32 = ctypes.WinDLL('kernel32.dll')
    
    EmptyWorkingSet = psapi.EmptyWorkingSet
    EmptyWorkingSet.argtypes = [wintypes.HANDLE]
    EmptyWorkingSet.restype = wintypes.BOOL
    
    OpenProcess = kernel32.OpenProcess
    OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    OpenProcess.restype = wintypes.HANDLE
    
    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL
    
    PROCESS_QUERY_INFORMATION = 0x0400
    PROCESS_SET_QUOTA = 0x0100
    
    try:
        import psutil
        procs = list(psutil.process_iter(['pid', 'name', 'memory_info']))
        initial_rss = sum(p.info['memory_info'].rss for p in procs if p.info['memory_info'])
    except Exception:
        initial_rss = 0
        procs = []

    # Run Python Garbage Collection
    gc.collect()

    trimmed_count = 0
    if procs:
        for p in procs:
            pid = p.info['pid']
            name = (p.info['name'] or "").lower()
            if pid <= 4 or "system" in name or "idle" in name:
                continue
            h_proc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
            if h_proc:
                try:
                    if EmptyWorkingSet(h_proc):
                        trimmed_count += 1
                finally:
                    CloseHandle(h_proc)

    try:
        import psutil
        final_rss = sum(p.memory_info().rss for p in psutil.process_iter(['memory_info']) if p.is_running())
        freed_mb = max(0, round((initial_rss - final_rss) / (1024**2), 1))
    except Exception:
        freed_mb = 0.0

    return {
        "Platform": "Windows",
        "Method": "Win32 EmptyWorkingSet API + Garbage Collection",
        "ProcessesTrimmed": trimmed_count,
        "EstimatedFreedMB": freed_mb
    }


def clean_ram_macos():
    """Trigger macOS native disk/memory cache purge."""
    gc.collect()
    freed_mb = 0.0
    try:
        res = subprocess.run(["purge"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        success = (res.returncode == 0)
    except Exception:
        success = False

    return {
        "Platform": "macOS",
        "Method": "macOS native purge cache utility",
        "Success": success,
        "EstimatedFreedMB": "Standby cache released"
    }


def clean_ram_linux():
    """Flush Linux file system dirty buffers and drop page cache if permitted."""
    gc.collect()
    # 1. sync filesystem
    subprocess.run(["sync"])
    
    method = "User-space buffer synchronization & GC"
    # Check if root or sudo available to drop caches
    if os.geteuid() == 0 and os.path.exists("/proc/sys/vm/drop_caches"):
        try:
            with open("/proc/sys/vm/drop_caches", "w") as f:
                f.write("3\n")
            method = "Kernel drop_caches (PageCache, dentries, and inodes)"
        except Exception:
            pass

    return {
        "Platform": "Linux",
        "Method": method,
        "Success": True,
        "EstimatedFreedMB": "Buffers synchronized and trimmed"
    }


def clean_ram():
    """Universal cross-platform RAM purge entrypoint."""
    system = platform.system()
    if system == "Windows":
        return clean_ram_windows()
    elif system == "Darwin":
        return clean_ram_macos()
    elif system == "Linux":
        return clean_ram_linux()
    else:
        gc.collect()
        return {"Platform": system, "Method": "Python GC collect", "EstimatedFreedMB": 0}


if __name__ == "__main__":
    result = clean_ram()
    print("OptiPulse RAM Cleaner Result:", result)
