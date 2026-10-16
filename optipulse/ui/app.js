/**
 * OptiPulse Frontend UI Logic & Telemetry Engine
 */

let currentTelemetry = null;
let activeFilter = 'all';
let autoRefreshTimer = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  fetchTelemetry();
  setupEventListeners();
  toggleAutoRefresh(true);
});

function setupEventListeners() {
  document.getElementById('btnCleanRam')?.addEventListener('click', purgeRAM);
  document.getElementById('btnRescan')?.addEventListener('click', () => fetchTelemetry(true));
  document.getElementById('btnExportJson')?.addEventListener('click', exportDiagnosticJson);
  
  // Filter tabs
  document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', (e) => {
      document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active-tab', 'bg-slate-800', 'text-white'));
      e.currentTarget.classList.add('active-tab', 'bg-slate-800', 'text-white');
      activeFilter = e.currentTarget.dataset.filter;
      renderRecommendations(currentTelemetry?.Recommendations || []);
    });
  });

  // Auto-refresh switch
  const autoToggle = document.getElementById('chkAutoRefresh');
  if (autoToggle) {
    autoToggle.addEventListener('change', (e) => toggleAutoRefresh(e.target.checked));
  }
}

function toggleAutoRefresh(enabled) {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
  if (enabled) {
    autoRefreshTimer = setInterval(() => fetchTelemetry(false), 5000);
  }
}

async function fetchTelemetry(showToastNotification = false) {
  const refreshIcon = document.getElementById('rescanIcon');
  if (refreshIcon) refreshIcon.classList.add('animate-spin');

  try {
    const res = await fetch('/api/telemetry?t=' + Date.now());
    if (!res.ok) throw new Error('API offline');
    const data = await res.json();
    currentTelemetry = data;
    renderDashboard(data);
    if (showToastNotification) {
      showToast('System Audited', 'All hardware sensors & diagnostics refreshed successfully.', 'emerald');
    }
  } catch (err) {
    console.error('Failed to load telemetry:', err);
    showToast('Telemetry Error', 'Could not communicate with OptiPulse local server.', 'rose');
  } finally {
    if (refreshIcon) {
      setTimeout(() => refreshIcon.classList.remove('animate-spin'), 600);
    }
  }
}

function renderDashboard(data) {
  // 1. Header & System Metadata
  document.getElementById('osName').innerText = data.OS?.OSName || 'Operating System';
  document.getElementById('osPlatform').innerText = data.OS?.Platform || 'OS';
  document.getElementById('lastScanTime').innerText = data.Timestamp || 'Just now';
  document.getElementById('uptimeHours').innerText = (data.OS?.UptimeHours || '0') + 'h uptime';

  // 2. Score Gauge
  const score = data.OptimizationScore || 0;
  updateScoreGauge(score);

  // 3. Memory Card
  const mem = data.Memory || {};
  document.getElementById('ramTotal').innerText = `${mem.TotalGB || 0} GB`;
  document.getElementById('ramFree').innerText = `${mem.FreeGB || 0} GB Free`;
  document.getElementById('ramUsedPct').innerText = `${mem.UsedPercent || 0}%`;
  document.getElementById('ramBar').style.width = `${mem.UsedPercent || 0}%`;
  document.getElementById('ramChannel').innerText = mem.Channel || 'Standard Channel';
  document.getElementById('ramPaging').innerText = `${mem.PagesPerSec || 0} pages/sec`;
  document.getElementById('ramSwap').innerText = `${mem.SwapUsedGB || 0} GB / ${mem.SwapTotalGB || 0} GB`;

  // 4. CPU Card
  const cpu = data.CPU || {};
  document.getElementById('cpuModel').innerText = cpu.Model || 'CPU';
  document.getElementById('cpuCores').innerText = `${cpu.PhysicalCores || 0} Cores / ${cpu.LogicalThreads || 0} Threads`;
  document.getElementById('cpuUsage').innerText = `${cpu.UsagePercent || 0}%`;
  document.getElementById('cpuBar').style.width = `${Math.min(100, cpu.UsagePercent || 0)}%`;
  document.getElementById('cpuPowerPlan').innerText = cpu.PowerProfile || 'Standard';
  if (document.getElementById('cpuArch')) {
    document.getElementById('cpuArch').innerText = `${data.OS?.Architecture || 'x86_64'} (${cpu.LogicalThreads || 0} Threads)`;
  }

  // 5. GPU Card
  const gpu = data.GPUs?.[0] || {};
  document.getElementById('gpuModel').innerText = gpu.Model || 'Integrated Graphics';
  document.getElementById('gpuDriver').innerText = `Driver ${gpu.DriverVersion || 'Default'}`;
  document.getElementById('gpuVram').innerText = gpu.VramTotalMB === 'Unified with System RAM' 
    ? 'Unified UMA' 
    : `${gpu.VramFreeMB || 0} MB Free (${gpu.VramTotalMB || 0} MB)`;
  document.getElementById('gpuTemp').innerText = gpu.TemperatureC === 'Nominal' ? 'Nominal' : `${gpu.TemperatureC}°C`;
  document.getElementById('gpuAccel').innerText = gpu.Acceleration || 'Standard';

  // 6. Battery & Power Health Card
  const batt = data.Battery || {};
  if (batt.HasBattery) {
    document.getElementById('battPct').innerText = `${batt.Percentage || 0}%`;
    document.getElementById('battStatus').innerText = batt.Status || 'Active';
    document.getElementById('battBar').style.width = `${Math.min(100, batt.Percentage || 0)}%`;
    
    // Cycles
    document.getElementById('battCycles').innerText = batt.CycleCount 
      ? `${batt.CycleCount.toLocaleString()} Cycles` 
      : 'Sensor N/A';
    
    // Health %
    if (batt.HealthPercent) {
      document.getElementById('battHealth').innerText = `${batt.HealthPercent}% Maximum Capacity`;
      document.getElementById('battHealth').className = batt.HealthPercent >= 80 
        ? 'text-emerald-400 font-mono font-semibold text-[11px]' 
        : (batt.HealthPercent >= 70 ? 'text-amber-400 font-mono font-semibold text-[11px]' : 'text-rose-400 font-mono font-semibold text-[11px]');
    } else {
      document.getElementById('battHealth').innerText = 'Health N/A';
    }

    // Capacity Wh
    if (batt.DesignCapacityWh && batt.FullChargeCapacityWh) {
      document.getElementById('battCapacity').innerText = `${batt.FullChargeCapacityWh} Wh / ${batt.DesignCapacityWh} Wh`;
    } else {
      document.getElementById('battCapacity').innerText = 'Li-Ion Chemistry';
    }

    // Condition Pill
    const cond = batt.Condition || 'Normal';
    const condPill = document.getElementById('battConditionPill');
    if (condPill) {
      condPill.innerText = cond.toUpperCase();
      if (cond.toLowerCase().includes('normal') || cond.toLowerCase().includes('healthy')) {
        condPill.className = 'px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
      } else if (cond.toLowerCase().includes('fair') || cond.toLowerCase().includes('degraded')) {
        condPill.className = 'px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/20';
      } else {
        condPill.className = 'px-2 py-0.5 text-xs font-semibold rounded bg-rose-500/10 text-rose-400 border border-rose-500/20';
      }
    }
  } else {
    document.getElementById('battPct').innerText = 'AC Power';
    document.getElementById('battStatus').innerText = 'Desktop / Wall Powered';
    document.getElementById('battBar').style.width = '100%';
    document.getElementById('battCycles').innerText = 'No Battery (Wall Power)';
    document.getElementById('battHealth').innerText = '100% Constant Delivery';
    document.getElementById('battCapacity').innerText = 'Grid Powered';
  }

  // 7. Storage & Drive Health Card
  const storage = data.Storage || {};
  const primaryDrive = storage.Drives?.[0] || {};
  document.getElementById('diskTotal').innerText = `${primaryDrive.TotalGB || 0} GB`;
  document.getElementById('diskFree').innerText = `${primaryDrive.FreeGB || 0} GB Free`;
  document.getElementById('diskBar').style.width = `${primaryDrive.PercentUsed || 0}%`;
  document.getElementById('diskMount').innerText = `${primaryDrive.Mount || '/'} (${primaryDrive.FileSystem || 'SSD'})`;
  document.getElementById('diskUsed').innerText = `${primaryDrive.UsedGB || 0} GB (${primaryDrive.PercentUsed || 0}%)`;

  // 8. AI & Dev Stack Card
  const ai = data.AIStack || {};
  const torch = ai.PyTorch || {};
  document.getElementById('torchStatus').innerText = torch.Installed ? `v${torch.Version}` : 'Not Installed';
  document.getElementById('torchDevice').innerText = torch.AccelerationDevice || 'None';
  document.getElementById('cudaPill').innerText = torch.CudaAvailable ? 'CUDA ACTIVE' : (torch.MpsAvailable ? 'MPS ACTIVE' : 'CPU ONLY');
  document.getElementById('cudaPill').className = torch.CudaAvailable || torch.MpsAvailable 
    ? 'px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
    : 'px-2 py-0.5 text-xs font-semibold rounded bg-amber-500/10 text-amber-400 border border-amber-500/20';

  const ollama = ai.Ollama || {};
  document.getElementById('ollamaStatus').innerText = ollama.Installed ? (ollama.Running ? 'Daemon Running' : 'Installed (Idle)') : 'Not Installed';
  
  const docker = ai.Docker || {};
  document.getElementById('dockerStatus').innerText = docker.Installed ? (docker.Running ? 'Active' : 'Installed (Stopped)') : 'Not Installed';

  // 9. Render Recommendations
  renderRecommendations(data.Recommendations || []);
}

function updateScoreGauge(score) {
  const scoreText = document.getElementById('scoreValue');
  const scoreCircle = document.getElementById('scoreProgress');
  const scoreRating = document.getElementById('scoreRating');
  const scoreDesc = document.getElementById('scoreDescription');

  if (scoreText) scoreText.innerText = score;

  // Circumference = 2 * PI * r = 2 * 3.14159 * 80 ~= 502
  const maxDash = 502;
  const offset = maxDash - (maxDash * (score / 100));
  if (scoreCircle) {
    scoreCircle.style.strokeDashoffset = offset;
    if (score >= 90) {
      scoreCircle.style.stroke = '#10b981'; // Emerald
      scoreRating.innerText = 'PEAK OPTIMIZATION';
      scoreRating.className = 'text-xs font-bold uppercase tracking-wider text-emerald-400';
      scoreDesc.innerText = 'Hardware channels, memory buffers, and acceleration are running at maximum throughput.';
    } else if (score >= 75) {
      scoreCircle.style.stroke = '#06b6d4'; // Cyan
      scoreRating.innerText = 'GOOD OPTIMIZATION';
      scoreRating.className = 'text-xs font-bold uppercase tracking-wider text-cyan-400';
      scoreDesc.innerText = 'System is healthy with minor tuning suggestions available below.';
    } else if (score >= 55) {
      scoreCircle.style.stroke = '#f59e0b'; // Amber
      scoreRating.innerText = 'THROTTLED';
      scoreRating.className = 'text-xs font-bold uppercase tracking-wider text-amber-400';
      scoreDesc.innerText = 'Identified memory or power bottlenecks affecting developer performance.';
    } else {
      scoreCircle.style.stroke = '#f43f5e'; // Rose
      scoreRating.innerText = 'ACTION REQUIRED';
      scoreRating.className = 'text-xs font-bold uppercase tracking-wider text-rose-400';
      scoreDesc.innerText = 'Significant hardware or configuration bottlenecks detected.';
    }
  }
}

function renderRecommendations(recs) {
  const container = document.getElementById('recommendationsList');
  if (!container) return;

  const filtered = recs.filter(r => {
    if (activeFilter === 'action') return r.severity === 'critical' || r.severity === 'warning';
    if (activeFilter === 'optimal') return r.severity === 'optimal';
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="p-8 text-center text-slate-500 glass-panel rounded-2xl">
        <p class="text-sm">No recommendations match the selected filter.</p>
      </div>`;
    return;
  }

  container.innerHTML = filtered.map(r => {
    let badgeClass = 'bg-slate-800 text-slate-300 border-slate-700';
    let icon = '💡';
    if (r.severity === 'critical') {
      badgeClass = 'bg-rose-500/10 text-rose-400 border-rose-500/30';
      icon = '⚡';
    } else if (r.severity === 'warning') {
      badgeClass = 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      icon = '⚠️';
    } else if (r.severity === 'optimal') {
      badgeClass = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      icon = '✓';
    } else if (r.severity === 'tip') {
      badgeClass = 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      icon = '🚀';
    }

    return `
      <div class="glass-panel rounded-2xl p-5 border border-slate-800 transition hover:border-slate-700 space-y-3">
        <div class="flex items-center justify-between gap-3">
          <div class="flex items-center gap-2.5">
            <span class="text-base">${icon}</span>
            <span class="text-xs font-semibold px-2.5 py-0.5 rounded-full border ${badgeClass} uppercase tracking-wider">
              ${r.severity}
            </span>
            <span class="text-xs text-slate-400 font-mono">${r.category}</span>
          </div>
        </div>
        <div>
          <h3 class="text-base font-bold text-slate-100">${r.title}</h3>
          <p class="text-xs text-slate-300 mt-1 leading-relaxed">${r.description}</p>
        </div>
        <div class="pt-2 border-t border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs">
          <div class="text-slate-400">
            <span class="text-slate-500 font-medium">Action:</span> 
            <span class="text-slate-200 font-mono select-all">${r.action}</span>
          </div>
        </div>
        <div class="p-2.5 rounded-xl bg-slate-950/60 border border-slate-900 text-xs text-slate-400">
          <span class="text-cyan-400 font-semibold">Dev Impact:</span> ${r.usecase}
        </div>
      </div>
    `;
  }).join('');
}

async function purgeRAM() {
  const btn = document.getElementById('btnCleanRam');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span> Purging RAM...';
  }

  try {
    const res = await fetch('/api/clean-ram', { method: 'POST' });
    if (!res.ok) throw new Error('Purge failed');
    const data = await res.json();
    
    // Refresh UI with returned data
    fetchTelemetry();
    
    const freed = data.CleanResult?.EstimatedFreedMB || 0;
    showToast('RAM Purged Successfully', `Released ~${freed} MB of unreferenced working set memory.`, 'emerald');
  } catch (err) {
    showToast('Purge Failed', err.message, 'rose');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = '<span>🧹</span> Purge Inactive RAM';
    }
  }
}

function exportDiagnosticJson() {
  if (!currentTelemetry) return;
  const str = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(currentTelemetry, null, 2));
  const el = document.createElement('a');
  el.setAttribute("href", str);
  el.setAttribute("download", `optipulse-diagnostic-${Date.now()}.json`);
  document.body.appendChild(el);
  el.click();
  el.remove();
  showToast('Exported', 'Saved diagnostic report JSON.', 'cyan');
}

function showToast(title, msg, color = 'emerald') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const toast = document.createElement('div');
  const borderCol = color === 'emerald' ? 'border-emerald-500/40 text-emerald-400' : (color === 'rose' ? 'border-rose-500/40 text-rose-400' : 'border-cyan-500/40 text-cyan-400');
  toast.className = `glass-panel rounded-xl p-4 border ${borderCol} shadow-2xl max-w-sm toast-animate flex items-start gap-3`;
  toast.innerHTML = `
    <div class="text-lg">⚡</div>
    <div>
      <h4 class="text-xs font-bold text-slate-100 uppercase tracking-wide">${title}</h4>
      <p class="text-xs text-slate-400 mt-0.5">${msg}</p>
    </div>
  `;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.5s ease';
    setTimeout(() => toast.remove(), 500);
  }, 4000);
}
