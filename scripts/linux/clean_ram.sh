#!/usr/bin/env bash
# OptiPulse Linux RAM Purge Script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

python3 -m optipulse --clean-ram
