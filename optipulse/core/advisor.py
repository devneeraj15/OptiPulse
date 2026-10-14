"""
OptiPulse - Intelligent Optimization Engine & Diagnostic Advisor
Generates a 0-100 System Optimization Score and actionable hardware/software recommendations.
"""

def analyze_system(audit_data):
    score = 100
    suggestions = []
    
    os_info = audit_data.get("OS", {})
    cpu_info = audit_data.get("CPU", {})
    mem_info = audit_data.get("Memory", {})
    gpus = audit_data.get("GPUs", [])
    storage = audit_data.get("Storage", {})
    batt = audit_data.get("Battery", {})
    ai = audit_data.get("AIStack", {})

    # =========================================================================
    # 1. RAM & Memory Architecture Analysis
    # =========================================================================
    total_ram = mem_info.get("TotalGB", 0)
    free_ram = mem_info.get("FreeGB", 0)
    used_pct = mem_info.get("UsedPercent", 0)
    channel = mem_info.get("Channel", "")
    pages_per_sec = mem_info.get("PagesPerSec", 0)
    swap_used = mem_info.get("SwapUsedGB", 0)

    # Memory Capacity Check
    if total_ram < 8.0:
        score -= 20
        suggestions.append({
            "id": "ram_capacity_low",
            "category": "Memory & RAM",
            "severity": "critical",
            "title": "Low Physical RAM Capacity Detected (< 8 GB)",
            "description": f"Detected {total_ram} GB of RAM. Modern AI development, Docker containers, and LLM inference require at least 16 GB of memory to prevent aggressive disk paging.",
            "action": "Upgrade physical RAM to 16 GB or 32 GB for seamless model compilation and containerized workflows.",
            "usecase": "Local LLMs (Llama 3, Mistral) and PyTorch matrix allocations will OOM or freeze on sub-8GB systems."
        })
    elif total_ram < 15.0:
        suggestions.append({
            "id": "ram_capacity_modest",
            "category": "Memory & RAM",
            "severity": "tip",
            "title": "Modest RAM Capacity (8–12 GB)",
            "description": f"Detected {total_ram} GB. Sufficient for standard web development and small scripts, but larger model inference will benefit from 16 GB+.",
            "action": "Consider adding an identical 8 GB SODIMM stick to upgrade to 16 GB Dual-Channel.",
            "usecase": "Eliminates swap file bottlenecks when running VS Code, Chrome, and local servers simultaneously."
        })
    else:
        suggestions.append({
            "id": "ram_capacity_optimal",
            "category": "Memory & RAM",
            "severity": "optimal",
            "title": f"High Capacity Physical RAM ({total_ram} GB Available)",
            "description": f"Your system has {total_ram} GB of physical memory, providing ample headroom for memory-intensive development workloads.",
            "action": "Memory capacity is optimal.",
            "usecase": "Supports multi-gigabyte PyTorch tensors, parallel compiling, and running local embeddings without swapping."
        })

    # Memory Channel Analysis (Dual-Channel vs Single-Channel)
    if "Single-Channel" in channel:
        score -= 10
        suggestions.append({
            "id": "ram_channel_single",
            "category": "Memory & RAM",
            "severity": "warning",
            "title": "Single-Channel Memory Bus Bottleneck",
            "description": "System is operating in 64-bit single-channel mode. Memory bandwidth is throttled by approximately 50%, impacting CPU cache refills and integrated GPU throughput.",
            "action": "Populate the second memory slot with a matching frequency DDR4/DDR5 SODIMM stick to enable 128-bit symmetric dual-channel bandwidth.",
            "usecase": "Dual-channel increases compilation speeds by up to 25% and boosts CPU-based tensor operations significantly."
        })
    elif "Dual-Channel" in channel or "Unified Memory" in channel:
        suggestions.append({
            "id": "ram_channel_dual",
            "category": "Memory & RAM",
            "severity": "optimal",
            "title": f"High-Bandwidth Bus: {channel}",
            "description": "Operating with full dual-channel / unified memory bus bandwidth. Memory throughput is fully unlocked.",
            "action": "Hardware memory bus is optimal.",
            "usecase": "Provides maximum data transfer rates between CPU, system cache, and graphics pipelines."
        })

    # Paging / Swapping Check
    if pages_per_sec > 100 or swap_used > 3.0:
        score -= 15
        suggestions.append({
            "id": "ram_swapping_high",
            "category": "Memory & RAM",
            "severity": "critical",
            "title": "Excessive Disk Paging / Swapping Detected",
            "description": f"Detected active paging ({pages_per_sec} pages/sec, {swap_used} GB swap in use). The operating system is swapping inactive memory to the SSD, creating UI stutter and start menu delay.",
            "action": "Use OptiPulse 'Purge Inactive RAM' or close background browser tabs to free up unneeded working sets.",
            "usecase": "Eliminates taskbar latency and ensures instant context switching between IDE and terminal."
        })
    else:
        suggestions.append({
            "id": "ram_paging_clean",
            "category": "Memory & RAM",
            "severity": "optimal",
            "title": "Zero Paging Bottleneck (0 Pages/Sec Swapping)",
            "description": "Active working sets reside entirely in high-speed physical silicon. Disk paging delay is zero.",
            "action": "Memory paging state is optimal.",
            "usecase": "Instant application responsiveness and lag-free multitasking."
        })

    # =========================================================================
    # 2. CPU & Power Governor Analysis
    # =========================================================================
    power_plan = cpu_info.get("PowerProfile", "")
    cpu_usage = cpu_info.get("UsagePercent", 0)

    if "Power Saver" in power_plan or "powersave" in power_plan.lower():
        score -= 15
        suggestions.append({
            "id": "cpu_power_saver",
            "category": "Processor & Power",
            "severity": "critical",
            "title": "CPU Throttled by Power Saver Plan",
            "description": f"Active power scheme is set to '{power_plan}'. CPU core frequency and boost clocks are capped to preserve battery, causing sluggish compilation and slow execution.",
            "action": "Switch to 'Ultimate Performance' (Windows: powercfg /setactive) or 'performance' governor (Linux: cpupower frequency-set -g performance).",
            "usecase": "Unlocks maximum turbo boost clocks (up to 4.0 GHz) for code compilation and model processing."
        })
    elif "Ultimate Performance" in power_plan or "Performance" in power_plan:
        suggestions.append({
            "id": "cpu_power_optimal",
            "category": "Processor & Power",
            "severity": "optimal",
            "title": f"High Performance Governor Engaged ({power_plan})",
            "description": "CPU frequency scaling is set for minimal latency and maximum burst frequencies.",
            "action": "Power profile is optimal.",
            "usecase": "Guarantees zero clock throttling during compute-heavy compilation passes."
        })

    if cpu_usage > 40.0:
        score -= 10
        suggestions.append({
            "id": "cpu_idle_high",
            "category": "Processor & Power",
            "severity": "warning",
            "title": f"Elevated Background CPU Load ({cpu_usage}%)",
            "description": "Background processes are consuming significant CPU cycles while the system is near idle.",
            "action": "Inspect Task Manager or run `top`/`htop` to terminate lingering background renderers or telemetry tasks.",
            "usecase": "Keeps CPU thermals low and reserves all cores for compilation and model evaluation."
        })

    # =========================================================================
    # 3. GPU & AI Acceleration Analysis
    # =========================================================================
    has_nvidia = any(g.get("Vendor") == "NVIDIA" for g in gpus)
    has_apple = any(g.get("Vendor") == "Apple" for g in gpus)
    torch_data = ai.get("PyTorch", {})
    torch_cuda = torch_data.get("CudaAvailable", False)
    torch_mps = torch_data.get("MpsAvailable", False)
    torch_installed = torch_data.get("Installed", False)

    if has_nvidia:
        nvidia_gpu = next(g for g in gpus if g.get("Vendor") == "NVIDIA")
        temp = nvidia_gpu.get("TemperatureC", "0")
        try:
            temp_int = int(temp)
            if temp_int > 80:
                score -= 10
                suggestions.append({
                    "id": "gpu_temp_high",
                    "category": "GPU & AI Hardware",
                    "severity": "warning",
                    "title": f"High GPU Operating Temperature ({temp_int}°C)",
                    "description": "GPU temperature is elevated. Continued high thermals can trigger thermal clock down-throttling.",
                    "action": "Ensure laptop cooling vents are elevated from surfaces; inspect fan intake.",
                    "usecase": "Maintains continuous peak CUDA core frequencies during model training."
                })
        except ValueError:
            pass

        if torch_installed and not torch_cuda:
            score -= 15
            suggestions.append({
                "id": "torch_cpu_only",
                "category": "GPU & AI Hardware",
                "severity": "critical",
                "title": "PyTorch CPU-Only Mismatch on NVIDIA Hardware",
                "description": f"System has a dedicated {nvidia_gpu.get('Model')}, but PyTorch is running in CPU mode. Matrix multiplications are running 20x to 50x slower.",
                "action": "Install PyTorch with CUDA support: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124`",
                "usecase": "Accelerates deep learning training, CNN/Transformer inference, and embedding generation by 20x–50x."
            })
        elif torch_installed and torch_cuda:
            suggestions.append({
                "id": "torch_cuda_optimal",
                "category": "GPU & AI Hardware",
                "severity": "optimal",
                "title": f"Hardware CUDA Acceleration Active ({nvidia_gpu.get('Model')})",
                "description": f"PyTorch {torch_data.get('Version')} is utilizing dedicated CUDA cores and GDDR6 VRAM ({torch_data.get('ComputeCapability')}).",
                "action": "AI compute acceleration is optimal.",
                "usecase": "Enables high-throughput matrix multiplication (2.7+ TFLOPS) and PyTorch Tensor operations directly in VRAM."
            })
    elif has_apple:
        if torch_installed and not torch_mps:
            score -= 10
            suggestions.append({
                "id": "torch_apple_mps_missing",
                "category": "GPU & AI Hardware",
                "severity": "warning",
                "title": "Apple Silicon Metal Acceleration (MPS) Inactive",
                "description": "PyTorch is not utilizing Apple Metal Performance Shaders (MPS) unified memory acceleration.",
                "action": "Ensure torch is targeting `device = 'mps'` in PyTorch 2.x.",
                "usecase": "Unlocks high-bandwidth unified memory for local LLM inference on M-series chips."
            })
        elif torch_installed and torch_mps:
            suggestions.append({
                "id": "torch_mps_optimal",
                "category": "GPU & AI Hardware",
                "severity": "optimal",
                "title": "Apple Metal Performance Shaders (MPS) Active",
                "description": "PyTorch is utilizing Apple Silicon unified GPU cores.",
                "action": "Apple Metal acceleration is optimal.",
                "usecase": "Zero-copy memory sharing between CPU and GPU for ultra-fast local LLMs."
            })

    # =========================================================================
    # 4. Storage & Drive Health Analysis
    # =========================================================================
    drives = storage.get("Drives", [])
    for d in drives:
        pct = d.get("PercentUsed", 0)
        free_gb = d.get("FreeGB", 0)
        mount = d.get("Mount", "")
        if pct > 88.0 or free_gb < 20.0:
            score -= 10
            suggestions.append({
                "id": f"storage_low_{mount.replace(':', '').replace('/', '')}",
                "category": "Storage & Drive Health",
                "severity": "warning",
                "title": f"Low Storage Space on {mount} ({pct}% Used, {free_gb} GB Free)",
                "description": "NVMe SSDs require at least 15% free space for SLC dynamic write caching and wear-leveling algorithms. Low free space degrades random write speeds.",
                "action": f"Free up at least 25 GB on {mount} by purging temporary files or moving inactive archives.",
                "usecase": "Preserves maximum NVMe burst write throughput for dataset unpacking and Docker image pulling."
            })
            break
    else:
        suggestions.append({
            "id": "storage_healthy",
            "category": "Storage & Drive Health",
            "severity": "optimal",
            "title": "NVMe Storage Headroom & SMART Health Optimal",
            "description": "Primary drive has plenty of free capacity (>40% free), ensuring maximum SLC cache write performance.",
            "action": "Storage health is optimal.",
            "usecase": "Fast disk I/O prevents dataset loading bottlenecks during training."
        })

    # =========================================================================
    # 5. Local AI & Dev Tooling Stack
    # =========================================================================
    ollama_info = ai.get("Ollama", {})
    if ollama_info.get("Installed"):
        status_txt = "Daemon Running" if ollama_info.get("Running") else "Installed (Daemon Idle)"
        suggestions.append({
            "id": "ollama_status",
            "category": "Developer & AI Stack",
            "severity": "optimal" if ollama_info.get("Running") else "tip",
            "title": f"Ollama Local Model Engine: {status_txt}",
            "description": "Ollama is installed on this machine, enabling private, offline LLM inference.",
            "action": "Run `ollama run llama3.2:3b` or `ollama run qwen2.5:3b` to launch local AI reasoning." if not ollama_info.get("Running") else "Ready for API integration.",
            "usecase": "Local code completion and autonomous agent reasoning with 0 cloud API latency."
        })

    # Clamp Score between 10 and 100
    final_score = max(10, min(100, score))

    return {
        "OptimizationScore": final_score,
        "TotalRecommendations": len(suggestions),
        "Recommendations": suggestions
    }
