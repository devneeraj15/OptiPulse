#!/usr/bin/env bash
# OptiPulse Linux Launcher
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

echo "================================================================"
echo "     OPTIPULSE - HARDWARE TELEMETRY & OPTIMIZATION CENTER"
echo "================================================================"

if ! command -v python3 &> /dev/null; then
    echo "[-] python3 is not installed or not in PATH."
    exit 1
fi

echo "[*] Launching OptiPulse on Linux..."
python3 -m optipulse
