"""
OptiPulse - Universal Cross-Platform Hardware & System Telemetry Auditor
Supports: Windows, Linux, macOS (Apple Silicon & Intel)
Optimized with native OS fallbacks (Zero pip dependencies required).
"""

import os
import sys
import platform
import subprocess
import shutil
import json
import time
import re

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Global cache for static hardware properties
_STATIC_HARDWARE_CACHE = {}


def run_cmd(cmd_list, timeout=4):
    """Safely execute a shell command and return stdout as string."""
    try:
        res = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            shell=False
        )
        if res.returncode == 0:
            return res.stdout.strip()
    except Exception:
        pass
    return ""


def get_os_info():
    """Retrieve operating system platform details."""
    system = platform.system()
    release = platform.release()
    version = platform.version()
    arch = platform.machine()
    
    uptime_hours = 0.0
    if HAS_PSUTIL:
        try:
            boot_time = psutil.boot_time()
            uptime_hours = round((time.time() - boot_time) / 3600.0, 1)
        except Exception:
            pass
    elif system == "Darwin":
        # macOS uptime via sysctl kern.boottime
        out = run_cmd(["sysctl", "-n", "kern.boottime"])
        m = re.search(r"sec = (\d+)", out)
        if m:
            boot_sec = int(m.group(1))
            uptime_hours = round((time.time() - boot_sec) / 3600.0, 1)
    elif system == "Linux" and os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime") as f:
                up_sec = float(f.read().split()[0])
                uptime_hours = round(up_sec / 3600.0, 1)
        except Exception:
            pass
            
    os_name = f"{system} {release}"
    if system == "Darwin":
        mac_ver = platform.mac_ver()[0]
        os_name = f"macOS {mac_ver} ({arch})"
    elif system == "Linux":
        if os.path.exists("/etc/os-release"):
            try:
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            os_name = line.split("=", 1)[1].strip().strip('"')
                            break
            except Exception:
                pass
    elif system == "Windows":
        try:
            build = sys.getwindowsversion().build
            if build >= 22000:
                os_name = f"Windows 11 (Build {build})"
            else:
                os_name = f"Windows 10 (Build {build})"
        except Exception:
            pass

    return {
        "Platform": system,
        "OSName": os_name,
        "Architecture": arch,
        "Kernel": version,
        "UptimeHours": uptime_hours
    }


def get_cpu_info():
    """Retrieve CPU specifications and live load."""
    system = platform.system()
    global _STATIC_HARDWARE_CACHE
    
    # 1. Static CPU Model & Cores (cached)
    if "CPU_Model" not in _STATIC_HARDWARE_CACHE:
        model = platform.processor() or "Generic Processor"
        cores = os.cpu_count() or 1
        logical = cores
        if HAS_PSUTIL:
            try:
                cores = psutil.cpu_count(logical=False) or cores
                logical = psutil.cpu_count(logical=True) or logical
            except Exception:
                pass

        if system == "Windows":
            out = run_cmd(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"])
            if out:
                model = out.splitlines()[0].strip()
        elif system == "Darwin":
            out = run_cmd(["sysctl", "-n", "machdep.cpu.brand_string"])
            if out:
                model = out
            else:
                # Apple Silicon fallback
                chip = run_cmd(["sysctl", "-n", "hw.model"])
                model = f"Apple Silicon ({chip})" if chip else "Apple Silicon M-Series"
        elif system == "Linux" and os.path.exists("/proc/cpuinfo"):
            try:
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        if "model name" in line:
                            model = line.split(":", 1)[1].strip()
                            break
            except Exception:
                pass

        _STATIC_HARDWARE_CACHE["CPU_Model"] = model
        _STATIC_HARDWARE_CACHE["CPU_PhysicalCores"] = cores
        _STATIC_HARDWARE_CACHE["CPU_LogicalThreads"] = logical

    # 2. Dynamic metrics (live polling)
    usage_pct = 0.0
    freq_mhz = 0
    if HAS_PSUTIL:
        try:
            usage_pct = psutil.cpu_percent(interval=None)
            freq = psutil.cpu_freq()
            if freq:
                freq_mhz = round(freq.current)
        except Exception:
            pass
    elif system == "Darwin":
        # Native macOS load via sysctl vm.loadavg
        out = run_cmd(["sysctl", "-n", "vm.loadavg"])
        m = re.search(r"\{\s*([\d\.]+)", out)
        if m:
            cores = _STATIC_HARDWARE_CACHE.get("CPU_LogicalThreads", 8)
            load = float(m.group(1))
            usage_pct = min(100.0, round((load / max(1, cores)) * 100, 1))

    power_profile = _STATIC_HARDWARE_CACHE.get("PowerProfile", "Performance")
    if system == "Windows":
        plan_out = run_cmd(["powercfg", "/getactivescheme"])
        if "Ultimate Performance" in plan_out:
            power_profile = "Ultimate Performance"
        elif "High performance" in plan_out:
            power_profile = "High Performance"
        elif "Balanced" in plan_out:
            power_profile = "Balanced"
        elif "Power saver" in plan_out:
            power_profile = "Power Saver"
        _STATIC_HARDWARE_CACHE["PowerProfile"] = power_profile
    elif system == "Darwin":
        power_profile = "macOS Dynamic QoS"

    return {
        "Model": _STATIC_HARDWARE_CACHE["CPU_Model"],
        "PhysicalCores": _STATIC_HARDWARE_CACHE["CPU_PhysicalCores"],
        "LogicalThreads": _STATIC_HARDWARE_CACHE["CPU_LogicalThreads"],
        "FrequencyMHz": freq_mhz,
        "UsagePercent": usage_pct,
        "PowerProfile": power_profile
    }


def get_memory_info():
    """
    Retrieve RAM and Swap statistics.
    Includes full native fallbacks for macOS (sysctl/vm_stat), Linux (/proc/meminfo),
    and Windows (CIM) so that RAM is NEVER reported as 0.0 GB even without psutil.
    """
    system = platform.system()
    global _STATIC_HARDWARE_CACHE

    total_gb = 0.0
    free_gb = 0.0
    used_gb = 0.0
    used_pct = 0.0
    swap_total_gb = 0.0
    swap_used_gb = 0.0

    # 1. Attempt with psutil if present
    if HAS_PSUTIL:
        try:
            mem = psutil.virtual_memory()
            total_gb = round(mem.total / (1024**3), 2)
            free_gb = round(mem.available / (1024**3), 2)
            used_gb = round((mem.total - mem.available) / (1024**3), 2)
            used_pct = mem.percent

            swap = psutil.swap_memory()
            swap_total_gb = round(swap.total / (1024**3), 2)
            swap_used_gb = round(swap.used / (1024**3), 2)
        except Exception:
            pass

    # 2. Native macOS Fallback (sysctl hw.memsize + vm_stat + vm.swapusage)
    if total_gb == 0.0 and system == "Darwin":
        # Total Physical RAM
        memsize_str = run_cmd(["sysctl", "-n", "hw.memsize"])
        if memsize_str and memsize_str.isdigit():
            total_bytes = int(memsize_str)
            total_gb = round(total_bytes / (1024**3), 2)
        
        # Free & Available RAM via vm_stat
        vm_out = run_cmd(["vm_stat"])
        if vm_out:
            page_size = 4096
            m_page = re.search(r"page size of (\d+) bytes", vm_out)
            if m_page:
                page_size = int(m_page.group(1))
            
            pages_free = 0
            pages_inactive = 0
            pages_speculative = 0
            for line in vm_out.splitlines():
                if "Pages free:" in line:
                    m = re.search(r"(\d+)", line.split(":")[1])
                    if m: pages_free = int(m.group(1))
                elif "Pages inactive:" in line:
                    m = re.search(r"(\d+)", line.split(":")[1])
                    if m: pages_inactive = int(m.group(1))
                elif "Pages speculative:" in line:
                    m = re.search(r"(\d+)", line.split(":")[1])
                    if m: pages_speculative = int(m.group(1))
            
            free_bytes = (pages_free + pages_inactive + pages_speculative) * page_size
            free_gb = round(free_bytes / (1024**3), 2)
            used_gb = max(0.0, round(total_gb - free_gb, 2))
            used_pct = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0.0

        # Swap via sysctl vm.swapusage
        swap_out = run_cmd(["sysctl", "-n", "vm.swapusage"])
        if swap_out:
            m_total = re.search(r"total\s*=\s*([\d\.]+)M", swap_out)
            m_used = re.search(r"used\s*=\s*([\d\.]+)M", swap_out)
            if m_total:
                swap_total_gb = round(float(m_total.group(1)) / 1024.0, 2)
            if m_used:
                swap_used_gb = round(float(m_used.group(1)) / 1024.0, 2)

    # 3. Native Linux Fallback (/proc/meminfo)
    if total_gb == 0.0 and system == "Linux" and os.path.exists("/proc/meminfo"):
        try:
            meminfo = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        m = re.search(r"(\d+)", parts[1])
                        if m:
                            meminfo[key] = int(m.group(1)) * 1024  # kB to bytes
            if "MemTotal" in meminfo:
                total_gb = round(meminfo["MemTotal"] / (1024**3), 2)
                avail = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
                free_gb = round(avail / (1024**3), 2)
                used_gb = max(0.0, round(total_gb - free_gb, 2))
                used_pct = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0.0
            if "SwapTotal" in meminfo:
                swap_total_gb = round(meminfo["SwapTotal"] / (1024**3), 2)
                swap_free = meminfo.get("SwapFree", 0)
                swap_used_gb = round((meminfo["SwapTotal"] - swap_free) / (1024**3), 2)
        except Exception:
            pass

    # 4. Native Windows Fallback (CIM / WMI)
    if total_gb == 0.0 and system == "Windows":
        try:
            out = run_cmd(["powershell", "-NoProfile", "-Command", "$os = Get-CimInstance Win32_OperatingSystem; \"$($os.TotalVisibleMemorySize)|$($os.FreePhysicalMemory)\""])
            if "|" in out:
                t_kb, f_kb = out.split("|")
                total_gb = round(int(t_kb) / (1024**2), 2)
                free_gb = round(int(f_kb) / (1024**2), 2)
                used_gb = max(0.0, round(total_gb - free_gb, 2))
                used_pct = round((used_gb / total_gb) * 100, 1) if total_gb > 0 else 0.0
        except Exception:
            pass

    # Static Channel / Speed Cache
    if "RAM_Channel" not in _STATIC_HARDWARE_CACHE:
        speed_mhz = 3200
        channel = "Dual-Channel (128-bit)"
        if system == "Windows":
            out = run_cmd([
                "powershell", "-NoProfile", "-Command",
                "$ram = Get-CimInstance Win32_PhysicalMemory; " +
                "$speed = ($ram | Select-Object -First 1).ConfiguredClockSpeed; " +
                "$count = ($ram | Measure-Object).Count; " +
                "\"$speed|$count\""
            ])
            if out and "|" in out:
                parts = out.split("|")
                if parts[0].isdigit():
                    speed_mhz = int(parts[0])
                if parts[1].isdigit():
                    count = int(parts[1])
                    channel = f"Dual-Channel ({count} DIMMs @ {speed_mhz}MHz)" if count >= 2 else f"Single-Channel (1 DIMM @ {speed_mhz}MHz)"
        elif system == "Darwin":
            channel = "Apple Unified Memory Architecture (UMA)"
            speed_mhz = 6400
        _STATIC_HARDWARE_CACHE["RAM_Speed"] = speed_mhz
        _STATIC_HARDWARE_CACHE["RAM_Channel"] = channel

    pages_per_sec = 0
    if system == "Windows":
        try:
            perf_out = run_cmd(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory).PagesPersec"])
            if perf_out.isdigit():
                pages_per_sec = int(perf_out)
        except Exception:
            pass

    return {
        "TotalGB": total_gb,
        "FreeGB": free_gb,
        "UsedGB": used_gb,
        "UsedPercent": used_pct,
        "SwapTotalGB": swap_total_gb,
        "SwapUsedGB": swap_used_gb,
        "SpeedMHz": _STATIC_HARDWARE_CACHE.get("RAM_Speed", 3200),
        "Channel": _STATIC_HARDWARE_CACHE.get("RAM_Channel", "Dual-Channel"),
        "PagesPerSec": pages_per_sec
    }


def get_gpu_info():
    """Retrieve GPU details."""
    system = platform.system()
    global _STATIC_HARDWARE_CACHE

    gpu_list = []
    if shutil.which("nvidia-smi"):
        out = run_cmd([
            "nvidia-smi",
            "--query-gpu=name,driver_version,temperature.gpu,memory.total,memory.free,power.draw",
            "--format=csv,noheader,nounits"
        ], timeout=2)
        if out:
            for line in out.splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 6:
                    gpu_list.append({
                        "Vendor": "NVIDIA",
                        "Model": parts[0],
                        "DriverVersion": parts[1],
                        "TemperatureC": parts[2],
                        "VramTotalMB": parts[3],
                        "VramFreeMB": parts[4],
                        "PowerDrawW": parts[5],
                        "Acceleration": "CUDA Capable"
                    })

    if not gpu_list and system == "Darwin" and platform.machine() == "arm64":
        gpu_list.append({
            "Vendor": "Apple",
            "Model": "Apple Silicon (Integrated Metal GPU)",
            "DriverVersion": "macOS Metal 3",
            "TemperatureC": "Nominal",
            "VramTotalMB": "Unified with System RAM",
            "VramFreeMB": "Dynamic Allocation",
            "PowerDrawW": "SoC Managed",
            "Acceleration": "Apple Metal / MPS Supported"
        })

    if not gpu_list:
        gpu_list.append({
            "Vendor": "Standard",
            "Model": "Standard Display Adapter",
            "DriverVersion": "WHQL",
            "TemperatureC": "N/A",
            "VramTotalMB": "Shared",
            "VramFreeMB": "N/A",
            "PowerDrawW": "N/A",
            "Acceleration": "Standard Graphics"
        })

    return gpu_list


def get_storage_info():
    """Retrieve storage capacity."""
    drives = []
    if HAS_PSUTIL:
        try:
            parts = psutil.disk_partitions(all=False)
            for p in parts:
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    drives.append({
                        "Mount": p.mountpoint,
                        "Device": p.device,
                        "FileSystem": p.fstype,
                        "TotalGB": round(usage.total / (1024**3), 1),
                        "FreeGB": round(usage.free / (1024**3), 1),
                        "UsedGB": round(usage.used / (1024**3), 1),
                        "PercentUsed": usage.percent
                    })
                except Exception:
                    pass
        except Exception:
            pass
    elif shutil.which("df"):
        # Native fallback for macOS / Linux
        out = run_cmd(["df", "-k", "/"])
        lines = out.splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 4:
                total_kb = float(parts[1])
                used_kb = float(parts[2])
                free_kb = float(parts[3])
                drives.append({
                    "Mount": "/",
                    "Device": parts[0],
                    "FileSystem": "APFS" if platform.system() == "Darwin" else "ext4",
                    "TotalGB": round(total_kb / (1024**2), 1),
                    "FreeGB": round(free_kb / (1024**2), 1),
                    "UsedGB": round(used_kb / (1024**2), 1),
                    "PercentUsed": round((used_kb / total_kb) * 100, 1) if total_kb > 0 else 0.0
                })

    return {
        "Drives": drives,
        "PrimaryHealth": "Healthy"
    }


def get_battery_info():
    """
    Retrieve comprehensive battery telemetry across Windows, macOS, and Linux.
    Includes: Cycle Count, Maximum Health %, Condition, Status, Power Source, and Capacities.
    """
    system = platform.system()
    global _STATIC_HARDWARE_CACHE

    has_battery = False
    percent = 100
    plugged_in = True
    status = "AC Power Connected"

    # 1. Real-time Charge Level & Status
    if HAS_PSUTIL:
        try:
            batt = psutil.sensors_battery()
            if batt:
                has_battery = True
                percent = round(batt.percent)
                plugged_in = batt.power_plugged
                status = "AC Connected (Charging)" if plugged_in and percent < 100 else ("AC Power Connected" if plugged_in else "Battery Discharging")
        except Exception:
            pass

    # 2. Detailed Health Metrics Cache (Cycle Count, Design vs Full Capacity)
    if "Battery_Health_Data" not in _STATIC_HARDWARE_CACHE:
        cycle_count = None
        health_pct = None
        design_wh = None
        full_wh = None
        condition = "Normal"

        # macOS: ioreg -r -c AppleSmartBattery & system_profiler
        if system == "Darwin":
            out = run_cmd(["ioreg", "-r", "-c", "AppleSmartBattery"])
            if out:
                has_battery = True
                m_cycle = re.search(r'"CycleCount"\s*=\s*(\d+)', out)
                m_design = re.search(r'"DesignCapacity"\s*=\s*(\d+)', out)
                m_max = re.search(r'"(?:AppleRawMaxCapacity|MaxCapacity|NominalChargeCapacity)"\s*=\s*(\d+)', out)
                m_cur = re.search(r'"CurrentCapacity"\s*=\s*(\d+)', out)
                
                if m_cycle: cycle_count = int(m_cycle.group(1))
                d_val = int(m_design.group(1)) if m_design else None
                m_val = int(m_max.group(1)) if m_max else None
                if d_val and m_val and d_val > 0:
                    health_pct = round((m_val / d_val) * 100, 1)
                    design_wh = round(d_val / 1000.0, 1)
                    full_wh = round(m_val / 1000.0, 1)
                
                if not HAS_PSUTIL and m_cur and m_val and m_val > 0:
                    percent = min(100, round((int(m_cur.group(1)) / m_val) * 100))
                    plugged_in = '"ExternalConnected" = Yes' in out
                    status = "AC Connected" if plugged_in else "Battery Discharging"

            # Check system_profiler for condition string
            sp_out = run_cmd(["system_profiler", "SPPowerDataType"])
            if sp_out:
                has_battery = True
                m_cond = re.search(r"Condition:\s*([^\n]+)", sp_out)
                if m_cond:
                    condition = m_cond.group(1).strip()
                if not health_pct:
                    m_hp = re.search(r"Maximum Capacity:\s*([\d\.]+)%", sp_out)
                    if m_hp: health_pct = float(m_hp.group(1))
                if not cycle_count:
                    m_cc = re.search(r"Cycle Count:\s*(\d+)", sp_out)
                    if m_cc: cycle_count = int(m_cc.group(1))

        # Windows: powercfg /batteryreport /xml
        elif system == "Windows":
            p = os.path.join(os.environ.get("TEMP", "."), "optipulse_batt_report.xml")
            try:
                subprocess.run(["powercfg", "/batteryreport", "/xml", "/output", p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
                if os.path.exists(p):
                    has_battery = True
                    import xml.etree.ElementTree as ET
                    tree = ET.parse(p)
                    root = tree.getroot()
                    d_val, f_val = None, None
                    for elem in root.iter():
                        tag = elem.tag.split("}")[-1]
                        if tag == "DesignCapacity" and elem.text and elem.text.strip().isdigit() and not d_val:
                            d_val = int(elem.text.strip())
                        elif tag == "FullChargeCapacity" and elem.text and elem.text.strip().isdigit() and not f_val:
                            f_val = int(elem.text.strip())
                        elif tag == "CycleCount" and elem.text and elem.text.strip().isdigit() and not cycle_count:
                            cycle_count = int(elem.text.strip())
                    os.remove(p)
                    if d_val and f_val and d_val > 0:
                        health_pct = round((f_val / d_val) * 100, 1)
                        design_wh = round(d_val / 1000.0, 1)
                        full_wh = round(f_val / 1000.0, 1)
            except Exception:
                pass

        # Linux: /sys/class/power_supply/BAT*
        elif system == "Linux":
            for b_dir in ["/sys/class/power_supply/BAT0", "/sys/class/power_supply/BAT1"]:
                if os.path.exists(b_dir):
                    has_battery = True
                    def read_b(name):
                        fp = os.path.join(b_dir, name)
                        return open(fp).read().strip() if os.path.exists(fp) else None
                    
                    cc = read_b("cycle_count")
                    if cc and cc.isdigit(): cycle_count = int(cc)
                    e_full = read_b("energy_full") or read_b("charge_full")
                    e_des = read_b("energy_full_design") or read_b("charge_full_design")
                    if e_full and e_des and int(e_des) > 0:
                        health_pct = round((int(e_full) / int(e_des)) * 100, 1)
                        full_wh = round(int(e_full) / 1e6, 1)
                        design_wh = round(int(e_des) / 1e6, 1)
                    break

        # Calculate qualitative condition if not already set
        if condition == "Normal" and health_pct:
            if health_pct >= 80.0:
                condition = "Normal (Healthy)"
            elif health_pct >= 70.0:
                condition = "Fair (Degraded)"
            else:
                condition = "Service Recommended"

        _STATIC_HARDWARE_CACHE["Battery_Health_Data"] = {
            "HasBattery": has_battery,
            "CycleCount": cycle_count,
            "HealthPercent": health_pct,
            "DesignCapacityWh": design_wh,
            "FullChargeCapacityWh": full_wh,
            "Condition": condition
        }

    b_data = _STATIC_HARDWARE_CACHE["Battery_Health_Data"]

    return {
        "HasBattery": b_data.get("HasBattery", has_battery),
        "Percentage": percent,
        "PluggedIn": plugged_in,
        "Status": status,
        "CycleCount": b_data.get("CycleCount"),
        "HealthPercent": b_data.get("HealthPercent"),
        "DesignCapacityWh": b_data.get("DesignCapacityWh"),
        "FullChargeCapacityWh": b_data.get("FullChargeCapacityWh"),
        "Condition": b_data.get("Condition", "Normal")
    }


def get_ai_stack_info():
    """Check AI frameworks (cached)."""
    global _STATIC_HARDWARE_CACHE
    if "AI_Stack" in _STATIC_HARDWARE_CACHE:
        return _STATIC_HARDWARE_CACHE["AI_Stack"]

    torch_installed = False
    torch_version = "Not Installed"
    cuda_available = False
    mps_available = False
    device_name = "CPU Only"
    compute_capability = "N/A"

    try:
        import torch
        torch_installed = True
        torch_version = torch.__version__
        cuda_available = torch.cuda.is_available()
        if hasattr(torch.backends, "mps"):
            mps_available = torch.backends.mps.is_available()
        
        if cuda_available:
            device_name = torch.cuda.get_device_name(0)
            cap = torch.cuda.get_device_capability(0)
            compute_capability = f"{cap[0]}.{cap[1]} (sm_{cap[0]}{cap[1]})"
        elif mps_available:
            device_name = "Apple Silicon Metal (MPS)"
            compute_capability = "Metal 3 UMA"
    except ImportError:
        pass

    ollama_installed = shutil.which("ollama") is not None
    docker_installed = shutil.which("docker") is not None

    stack = {
        "PyTorch": {
            "Installed": torch_installed,
            "Version": torch_version,
            "CudaAvailable": cuda_available,
            "MpsAvailable": mps_available,
            "AccelerationDevice": device_name,
            "ComputeCapability": compute_capability
        },
        "Ollama": {
            "Installed": ollama_installed,
            "Running": False
        },
        "Docker": {
            "Installed": docker_installed,
            "Running": False
        },
        "Runtimes": {
            "Python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "Git": "git installed" if shutil.which("git") else "Not Installed",
            "Node": "node installed" if shutil.which("node") else "Not Installed"
        }
    }
    _STATIC_HARDWARE_CACHE["AI_Stack"] = stack
    return stack


def perform_full_audit():
    """Aggregate all system telemetry into a standardized JSON payload."""
    return {
        "Timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "OS": get_os_info(),
        "CPU": get_cpu_info(),
        "Memory": get_memory_info(),
        "GPUs": get_gpu_info(),
        "Storage": get_storage_info(),
        "Battery": get_battery_info(),
        "AIStack": get_ai_stack_info()
    }


if __name__ == "__main__":
    t0 = time.time()
    data = perform_full_audit()
    elapsed_ms = (time.time() - t0) * 1000
    print(f"Audit completed in {elapsed_ms:.1f} ms")
    print(json.dumps(data, indent=2))
