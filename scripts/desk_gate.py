"""Desk wave-gate: mechanical checks every desk wave must pass before commit.

Adopted from github.com/plugin87/ux-ui-agent-skills doctrine:
  - "gates don't prove pixels" -> this script is the MECHANICAL half; the
    orchestrator still does the rendered DOM/browser pass (RENDER AND LOOK).
  - all-or-nothing: prints PASS n/n or FAIL with exact findings; no partial credit.

Checks:
  1. HARDCODE LINT - raw hex colors in desk/src components outside the token
     files. The v5 system is tokens-only; a raw hex is how legacy islands and
     off-palette drift re-enter.
  2. CONTRAST GATE - WCAG 2.2 ratios for the locked v5 token pairs that have
     already burned us once (GLM found 3 P0s by hand). Any pair below its
     threshold fails the wave.
  3. LOCKED-FILE DIFF - money-math files must show zero working-tree diff.

Usage:  python scripts/desk_gate.py        (from repo root)
Exit 0 = all gates pass. Exit 1 = failures printed.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESK_SRC = ROOT / "manas_os" / "desk" / "src"
TOKEN_FILES = {"tokens.v5.css", "tokens.css"}  # raw hex allowed only in token definition files
# NOTE: legacy tokens.css is still imported by main.jsx — a SECOND theme source that
# violates the single-theme rule; queued for retirement (see HANDOFF_INDEX #14).
# files where legacy hex persists on purpose (shrink this list over time; never grow it)
HEX_ALLOWLIST_FILES: set[str] = {"App.css"}
TEST_FILE_RE = re.compile(r"\.test\.[jt]sx?$")

LOCKED_FILES = [
    "manas_os/scanner/gates.py",
    "manas_os/risk/plan.py",
    "manas_os/regime/snapshot.py",
    "manas_os/regime/governor.py",
    "manas_os/scanner/candidates.py",
    "manas_os/agents/sizer.py",
]

HEX_RE = re.compile(r"(?<![\w&])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    lo, hi = min(la, lb), max(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def read_tokens() -> dict[str, str]:
    css = (DESK_SRC / "styles" / "tokens.v5.css").read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for m in re.finditer(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b", css):
        out[m.group(1)] = m.group(2)
    return out


# token pairs the desk actually renders as text-on-bg (extend as GLM/audits find more)
# (foreground_token, background_token, min_ratio, why)
CONTRAST_PAIRS = [
    ("--v5-ink", "--v5-canvas", 4.5, "body text on canvas"),
    ("--v5-ink", "--v5-panel", 4.5, "body text on panel"),
    ("--v5-ink-dim", "--v5-panel", 4.5, "secondary text on panel"),
    ("--v5-ink-mute", "--v5-panel", 3.0, "muted labels (large-text bar)"),
    ("--v5-teal-ink", "--v5-panel", 4.5, "teal accent text"),
    ("--v5-amber-ink", "--v5-panel", 4.5, "amber accent text (GLM P0 class)"),
    ("--v5-on-accent", "--v5-teal", 4.5, "text on teal accent"),
    ("--v5-on-accent", "--v5-amber", 4.5, "text on amber accent"),
]


def gate_hardcodes() -> list[str]:
    fails: list[str] = []
    for path in DESK_SRC.rglob("*"):
        if path.suffix not in {".jsx", ".js", ".css", ".tsx", ".ts"}:
            continue
        if path.name in TOKEN_FILES or path.name in HEX_ALLOWLIST_FILES or TEST_FILE_RE.search(path.name):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if "sourceMappingURL" in line:
                continue
            # lint code, not commentary: strip // line comments and single-line
            # /* */ blocks (e.g. task refs like "#13b" parse as 3-digit hex)
            stripped = re.sub(r"/\*.*?\*/", "", line)
            stripped = re.sub(r"//.*$", "", stripped)
            for m in HEX_RE.finditer(stripped):
                fails.append(f"{path.relative_to(ROOT)}:{i}: raw hex {m.group(0)} (use a tokens.v5 var)")
    return fails


def gate_contrast() -> list[str]:
    fails: list[str] = []
    tokens = read_tokens()
    for fg, bg, min_ratio, why in CONTRAST_PAIRS:
        if fg not in tokens or bg not in tokens:
            fails.append(f"contrast: token missing ({fg if fg not in tokens else bg}) - pair skipped is a FAIL, not a skip")
            continue
        ratio = contrast(tokens[fg], tokens[bg])
        if ratio < min_ratio:
            fails.append(f"contrast: {fg} on {bg} = {ratio:.2f} < {min_ratio} ({why})")
    return fails


def gate_locked_diff() -> list[str]:
    res = subprocess.run(
        ["git", "diff", "--stat", "--", *LOCKED_FILES],
        capture_output=True, text=True, cwd=ROOT,
    )
    out = res.stdout.strip()
    return [f"LOCKED FILE DIFF:\n{out}"] if out else []


def main() -> int:
    gates = [
        ("hardcode-lint", gate_hardcodes),
        ("contrast", gate_contrast),
        ("locked-files", gate_locked_diff),
    ]
    all_fails: list[str] = []
    passed = 0
    for name, fn in gates:
        fails = fn()
        if fails:
            print(f"[FAIL] {name} ({len(fails)} finding(s))")
            for f in fails[:40]:
                print(f"   {f}")
            if len(fails) > 40:
                print(f"   ... and {len(fails) - 40} more")
            all_fails.extend(fails)
        else:
            print(f"[pass] {name}")
            passed += 1
    total = len(gates)
    if all_fails:
        print(f"\nGATE: {passed}/{total} - FAIL ({len(all_fails)} findings)")
        return 1
    print(f"\nGATE: {total}/{total} - PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
