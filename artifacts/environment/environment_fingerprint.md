# Environment & GPU-Driver Fingerprint

**Captured:** 2026-06-18T20:41 -0600
**Reason:** GPU drivers were just updated. Showdown simulation is CPU/Node-bound, but
PyTorch inference/training depends on the CUDA stack. This records the environment and
the sanity checks rerun afterward so new performance comparisons can be trusted.

## Host

| Field | Value |
| --- | --- |
| OS | Windows 11 Home, 10.0.26200 (SP0) |
| CPU | Intel64 Family 6 Model 158 Stepping 13 (8 logical cores) |
| RAM | 15.8 GB |
| GPU | NVIDIA GeForce RTX 2060 SUPER (8192 MiB) |
| NVIDIA driver | **610.62** (newly updated) |

## Toolchain

| Field | Value |
| --- | --- |
| Git commit (HEAD) | `de49cc0f4e234a62324cac6818c48dd73879e610` |
| git core.autocrlf | `true` |
| Node | v24.15.0 |
| npm | 11.12.1 |
| Python executable | `D:\Anaconda\envs\neuralgpu\python.exe` |
| Python version | 3.11.14 |

## Python / CUDA packages

| Package | Version |
| --- | --- |
| torch | 2.5.1+cu121 |
| torch CUDA build | 12.1 |
| torch.cuda.is_available() | **True** |
| CUDA device | NVIDIA GeForce RTX 2060 SUPER |
| cuDNN | 9.1.0 (90100) |
| numpy | 2.3.5 |
| fastapi | 0.136.1 |
| uvicorn | 0.46.0 |

## Pinned simulator dependencies (sim-core/package.json)

| Package | Version |
| --- | --- |
| pokemon-showdown | 0.11.10 |
| @smogon/calc | 0.11.0 |

## CPU vs CUDA split

- **sim-core (Pokémon Showdown battle mechanics + @smogon/calc damage RPC)** runs in
  Node.js on the CPU. It does **not** use CUDA. A GPU-driver update cannot change battle
  outcomes, seeds, or damage rolls; those are deterministic Node computations.
- **PyTorch policy / value / ranker inference and training** is the only consumer of
  CUDA. A driver update can affect this path (availability, kernel correctness, speed).
- Therefore the driver update can only move *model-inference* timing and *training*, not
  branch-search battle accuracy. Latency tables that include model scoring should be
  re-measured before cross-run comparison; pure sim-core branch/leaf counts are unaffected.

## Post-update sanity checks (rerun 2026-06-18)

| Check | Command | Result |
| --- | --- | --- |
| CUDA matmul smoke | `torch.randn(512,512,'cuda') @ x` | OK (returns finite scalar, `cuda.synchronize()` clean) |
| Sim-core parity gate | `run_windows.ps1 -Action validate-sim-core -SimCoreMode native` | `{"ok": true}` |
| Full test suite (Python) | `run_windows.ps1 -Action test -SimCoreMode native` | **177 passed, 1 skipped** |
| Full test suite (sim-core) | (same action, Node `node --test`) | **26 passed, 0 failed** |

No retraining was performed. CUDA, the parity gate, and both test suites are green after
the driver update.

## Caveats

- RAM was read via PowerShell `Win32_ComputerSystem` (15.8 GB); `psutil` is not installed
  in the `neuralgpu` env, so the Python RAM probe failed (non-blocking).
- Driver `610.62` is a notably high version string; it is what `nvidia-smi` reports on this
  host and is recorded verbatim. The CUDA *runtime* visible to PyTorch is 12.1 (the wheel
  build), independent of the display-driver number.
