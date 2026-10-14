"""
OptiPulse - Zero-Dependency Local Server & API Engine
Serves the aesthetic Glassmorphism Dashboard and exposes telemetry / optimization REST endpoints.
"""

import os
import sys
import json
import webbrowser
import subprocess
import shutil
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

# Reconfigure stdout/stderr to UTF-8 on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure optipulse root is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from optipulse.core.audit import perform_full_audit
from optipulse.core.cleaner import clean_ram
from optipulse.core.advisor import analyze_system

UI_DIR = os.path.join(CURRENT_DIR, "ui")


class OptiPulseHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/telemetry":
            audit = perform_full_audit()
            analysis = analyze_system(audit)
            payload = {
                **audit,
                "OptimizationScore": analysis["OptimizationScore"],
                "Recommendations": analysis["Recommendations"]
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        # Serve static assets or default to index.html
        if path == "/" or path == "":
            self.path = "/index.html"
            
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/clean-ram":
            result = clean_ram()
            audit = perform_full_audit()
            analysis = analyze_system(audit)
            payload = {
                "CleanResult": result,
                "UpdatedMemory": audit.get("Memory", {}),
                "OptimizationScore": analysis["OptimizationScore"],
                "Recommendations": analysis["Recommendations"]
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        # Silence routine static file request logs to keep terminal clean
        if "GET /api/" in format % args or "POST /api/" in format % args:
            super().log_message(format, *args)


def run_cli_audit():
    """Print a terminal report."""
    audit = perform_full_audit()
    analysis = analyze_system(audit)
    
    score = analysis["OptimizationScore"]
    cpu = audit.get("CPU", {})
    mem = audit.get("Memory", {})
    gpus = audit.get("GPUs", [{}])[0]
    ai = audit.get("AIStack", {})
    
    print("\n" + "=" * 65)
    print("              OPTIPULSE SYSTEM OPTIMIZATION AUDIT")
    print("=" * 65)
    print(f" [+] Optimization Score   : {score} / 100")
    print(f" [+] Operating System     : {audit.get('OS', {}).get('OSName')}")
    print(f" [+] Processor (CPU)      : {cpu.get('Model')} ({cpu.get('PhysicalCores')}C/{cpu.get('LogicalThreads')}T)")
    print(f" [+] Power Governor       : {cpu.get('PowerProfile')}")
    print(f" [+] System RAM           : {mem.get('TotalGB')} GB ({mem.get('FreeGB')} GB Free) - {mem.get('Channel')}")
    print(f" [+] Paging / Swapping    : {mem.get('PagesPerSec')} pages/sec (Swap: {mem.get('SwapUsedGB')} GB)")
    print(f" [+] Primary GPU          : {gpus.get('Model')} (Driver: {gpus.get('DriverVersion')})")
    print(f" [+] GPU Acceleration     : {gpus.get('Acceleration')} (VRAM Free: {gpus.get('VramFreeMB')} MB)")
    
    torch_info = ai.get("PyTorch", {})
    print(f" [+] PyTorch Stack        : {torch_info.get('Version')} (CUDA: {torch_info.get('CudaAvailable')})")
    print(f" [+] AI Device Target     : {torch_info.get('AccelerationDevice')}")
    
    print("\n" + "-" * 65)
    print("              ACTIONABLE OPTIMIZATION PLAYBOOK")
    print("-" * 65)
    for rec in analysis.get("Recommendations", []):
        badge = f"[{rec['severity'].upper()}]"
        print(f" {badge:<11} {rec['title']}")
        print(f"             Action : {rec['action']}")
        print(f"             Usecase: {rec['usecase']}\n")
    print("=" * 65 + "\n")


def start_server(port=7890, open_browser=True):
    """Start local OptiPulse HTTP server and optionally open browser."""
    server_address = ("127.0.0.1", port)
    
    try:
        httpd = HTTPServer(server_address, OptiPulseHandler)
    except OSError:
        # Fallback to alternate port if already in use
        port += 1
        server_address = ("127.0.0.1", port)
        httpd = HTTPServer(server_address, OptiPulseHandler)

    url = f"http://localhost:{port}"
    print(f"[+] OptiPulse Live Server active at: {url}")
    print("   Press Ctrl+C to stop server.")

    if open_browser:
        # Try native Chrome/Edge app mode for seamless desktop experience
        chrome_path = shutil.which("chrome") or shutil.which("google-chrome")
        if not chrome_path and sys.platform == "win32":
            standard_chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            if os.path.exists(standard_chrome):
                chrome_path = standard_chrome

        if chrome_path:
            try:
                subprocess.Popen([chrome_path, f"--app={url}"])
            except Exception:
                webbrowser.open(url)
        else:
            webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] OptiPulse server stopped gracefully.")
        httpd.server_close()


def main():
    parser = argparse.ArgumentParser(description="OptiPulse - Cross-Platform Hardware Telemetry & RAM Optimizer")
    parser.add_argument("--cli", action="store_true", help="Print CLI report to stdout without web UI")
    parser.add_argument("--clean-ram", action="store_true", help="Instantly purge idle RAM working sets and exit")
    parser.add_argument("--port", type=int, default=7890, help="Port to bind web server (default: 7890)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")

    args = parser.parse_args()

    if args.clean_ram:
        res = clean_ram()
        print(f"[+] RAM Purge Completed: {res.get('Method')} - Freed ~{res.get('EstimatedFreedMB')} MB")
        return

    if args.cli:
        run_cli_audit()
        return

    start_server(port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
