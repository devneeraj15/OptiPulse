# Contributing to OptiPulse 🚀

Thank you for your interest in contributing to **OptiPulse**! We are committed to building the ultimate cross-platform hardware audit and performance optimization engine for AI developers, system engineers, and power users.

---

## 🧭 How to Contribute

1. **Fork the Repository** on GitHub.
2. **Clone your fork locally**:
   ```bash
   git clone https://github.com/<your-username>/OptiPulse.git
   cd OptiPulse
   ```
3. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/awesome-feature
   ```
4. **Make Your Changes**:
   * Add hardware detection improvements in `optipulse/core/audit.py`.
   * Add platform-specific RAM flushing mechanisms in `optipulse/core/cleaner.py`.
   * Expand optimization heuristics in `optipulse/core/advisor.py`.
   * Enhance dashboard aesthetics in `optipulse/ui/`.
5. **Test Your Changes**:
   ```bash
   # Test CLI mode
   python -m optipulse --cli

   # Test Web UI mode
   python -m optipulse
   ```
6. **Commit & Push**:
   ```bash
   git commit -m "feat(advisor): add detection for ROCm GPU acceleration"
   git push origin feature/awesome-feature
   ```
7. **Open a Pull Request** with a description of your improvements.

---

## 🛠️ Code Architecture Principles

* **Zero Mandatory Dependencies**: OptiPulse must always fall back gracefully to standard Python libraries (`subprocess`, `platform`, `ctypes`) if third-party modules like `psutil` are absent.
* **Non-Destructive Actions**: Memory cleanups must only flush inactive standby pages, dirty file cache buffers, and unreferenced working sets. Never terminate active user processes.
* **Cross-Platform Parity**: Whenever adding a feature for Windows, consider equivalent mechanisms for Linux and macOS.

---

## ⚖️ License
By contributing to OptiPulse, you agree that your contributions will be licensed under the [MIT License](LICENSE).
