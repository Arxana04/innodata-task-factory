# Innodata AI Hackathon — Validation & Infrastructure Report

## Executive Summary
This document records the official validation evidence for five independent Harbor coding tasks
generated from Click 8.5.1 (commit `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1`).

All evaluations were executed using **Harbor 0.25.0** inside reproducible **Docker** environments
with strict network isolation (`network_mode = "no-network"`).

---

## 1. Baseline Verification
- **Target Repository:** `https://github.com/pallets/click.git`
- **Pinned Commit:** `cf19179e8e2fd54c601378cec9e0d21bb12b6fb1` (Click 8.5.1)
- **Local macOS Run:** 2433 passed, 25 skipped, 1 xfailed (0 failures)
- **Docker Debian Run:** 2434 passed, 24 skipped, 1 xfailed (0 failures)
- **Key Finding:** Installing `less` inside minimal Debian `python:3.12-slim-bookworm` is required for Click's pager tests (`test_echo_via_pager.py`).

---

## 2. Harbor Validation Matrix (10 Runs)

| Task ID | Run Type | Agent | Features Passed | Regressions Passed | Reward | Duration | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `datetime-bounds` | `nop` | nop | 0/3 | 123/2 | **0.0** (exp: 0.0) | 22.54s | **PASS** |
| `datetime-bounds` | `oracle` | oracle | 3/3 | 123/2 | **1.0** (exp: 1.0) | 21.5s | **PASS** |
| `envvar-delimiter` | `nop` | nop | 0/3 | 4/3 | **0.0** (exp: 0.0) | 21.19s | **PASS** |
| `envvar-delimiter` | `oracle` | oracle | 3/3 | 4/3 | **1.0** (exp: 1.0) | 21.87s | **PASS** |
| `exclusive-options` | `nop` | nop | 0/3 | 3/3 | **0.0** (exp: 0.0) | 20.94s | **PASS** |
| `exclusive-options` | `oracle` | oracle | 3/3 | 3/3 | **1.0** (exp: 1.0) | 21.53s | **PASS** |
| `key-value-type` | `nop` | nop | 0/3 | 33/3 | **0.0** (exp: 0.0) | 20.97s | **PASS** |
| `key-value-type` | `oracle` | oracle | 3/3 | 33/3 | **1.0** (exp: 1.0) | 21.35s | **PASS** |
| `option-help-sections` | `nop` | nop | 0/2 | 3/3 | **0.0** (exp: 0.0) | 21.15s | **PASS** |
| `option-help-sections` | `oracle` | oracle | 2/2 | 3/3 | **1.0** (exp: 1.0) | 21.39s | **PASS** |

---

## 3. Deliberately Broken Reference Behavior Check
- **Task Evaluated:** `datetime-bounds`
- **Mutation Injected:** Altered min boundary check from '<' to '<='
- **Feature Tests Passed:** 1
- **Feature Tests Failed:** 2
- **Regressions Passed:** 123
- **Reward Dropped To:** `0.3333333333333333` (Normal: `1.0`)
- **Outcome:** PASS (Breakage accurately detected by verifier)
- **Conclusion:** Confirms acceptance test suite is non-vacuous and enforces correct boundary logic.
