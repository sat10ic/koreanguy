"""Scratch browser-evidence capture for the evidence-desk wave.

Verification tooling for the orchestrator, not product code. Deleted at wave
close (CANONICAL.md section 7 scratch-script rule). Requires: the production
API on 127.0.0.1:8100 (python traderlog/run_api.py), ui/dist built, and the
playwright python package (already used by the test suite).

Usage: python capture.py [1920,1080]          # screenshots + geometry
       python capture.py [1920,1080] verify   # deterministic computed-style checks
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8100"
TABS = ["FEED", "TRADERS", "LEDGER", "BREADTH", "IDEAS", "LIBRARY"]
OUT = Path(__file__).resolve().parent


def health_ok() -> bool:
    try:
        with urlopen(f"{BASE}/api/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def capture(viewport: list[int]) -> tuple[list, list]:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
        page = ctx.new_page()
        issues: list[str] = []
        page.on(
            "console",
            lambda m: issues.append(f"{m.type}: {m.text}")
            if m.type in ("error", "warning")
            else None,
        )
        page.on("pageerror", lambda e: issues.append(str(e)))
        results = []
        for tab in TABS:
            page.goto(f"{BASE}/?tab={tab}", wait_until="networkidle")
            page.wait_for_timeout(700)
            shot = OUT / f"{'-'.join(map(str, viewport))}-{tab.lower()}.png"
            page.screenshot(path=str(shot))
            geo = page.evaluate(
                """() => {
                  const th = [...document.querySelectorAll('.feed-thumbs img, .media-box img')];
                  return {
                    docW: document.documentElement.scrollWidth,
                    vw: window.innerWidth,
                    overflowingPanels: [...document.querySelectorAll('.panel')]
                      .filter(p => p.scrollWidth > p.clientWidth + 1).length,
                    thumbs: th.length,
                    thumbBroken: th.filter(i => i.complete && i.naturalWidth === 0).length,
                  };
                }"""
            )
            results.append({"tab": tab, "shot": shot.name, **geo})
        browser.close()
        return results, issues


VERIFY_CHECKS = """() => {
  const px = (el, prop) => parseFloat(getComputedStyle(el)[prop]) || 0;
  const report = {};
  report.bodyFs = px(document.body, 'fontSize');

  // 1. No label text below 11px (glyph-only elements like carets excluded).
  const tooSmall = [];
  for (const el of document.querySelectorAll('body *')) {
    const style = getComputedStyle(el);
    const fs = px(el, 'fontSize');
    if (fs > 0 && fs < 11) {
      const text = (el.textContent || '').trim();
      const isGlyph = /^[\\u25B4\\u25B5\\u25B8\\u25BC\\u25BD\\u25BE\\u25BF\\u25C0\\u25C2\\u25C6\\u25A0\\u25CF\\u26A0\\u2713\\u2717\\u2192\\u2197]+$/.test(text);
      if (text && !isGlyph) tooSmall.push({ tag: el.tagName, cls: el.className, fs, text: text.slice(0, 40) });
    }
  }
  report.sub11pxLabels = tooSmall;

  // 2. Radius must be 0 everywhere; any box-shadow must be hard (blur 0).
  const roundness = [];
  const blurry = [];
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    const r = Math.max(px(el, 'borderTopLeftRadius'), px(el, 'borderTopRightRadius'),
                       px(el, 'borderBottomLeftRadius'), px(el, 'borderBottomRightRadius'));
    if (r > 0) roundness.push({ cls: el.className, r });
    if (s.boxShadow && s.boxShadow !== 'none' && /\\d+px \\d+px \\d+px/.test(s.boxShadow)) {
      const m = s.boxShadow.match(/([\\d.]+)px ([\\d.]+)px ([\\d.]+)px/);
      if (m && parseFloat(m[3]) > 0) blurry.push({ cls: el.className, shadow: s.boxShadow.slice(0, 60) });
    }
  }
  report.roundness = roundness;
  report.blurryShadows = blurry;

  // 3. No serif family in use; prose (long text) must not be uppercased.
  const serif = [];
  const upperProse = [];
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if (/\\bserif\\b/i.test(s.fontFamily) && !/sans-?serif/i.test(s.fontFamily)) {
      serif.push({ cls: el.className, fam: s.fontFamily });
    }
    const text = (el.textContent || '').trim();
    if (s.textTransform === 'uppercase' && text.length > 60) {
      upperProse.push({ cls: el.className, text: text.slice(0, 60) });
    }
  }
  report.serif = serif;
  report.upperProse = upperProse;

  // 4. Grid: .page centered 1680 at 1920 viewport; doc width == viewport.
  const pg = document.querySelector('.page');
  report.pageW = pg ? Math.round(pg.getBoundingClientRect().width) : null;
  report.pageX = pg ? Math.round(pg.getBoundingClientRect().x) : null;
  report.docW = document.documentElement.scrollWidth;
  report.vw = window.innerWidth;

  // 5. Nested 2px boxes: elements with a 2px solid border whose nearest
  //    .panel ancestor is also 2px-bordered, excluding known controls.
  const nested = [];
  for (const el of document.querySelectorAll('.panel *')) {
    const s = getComputedStyle(el);
    const bt = s.borderTopWidth;
    if (bt === '2px') {
      const isControl = el.closest('button, select, input, a');
      if (!isControl) nested.push({ tag: el.tagName, cls: el.className });
    }
  }
  report.nested2px = nested;

  // 6. Mono on prose: elements whose font-family is monospace AND that carry
  //    long sentence-like text.
  const monoProse = [];
  for (const el of document.querySelectorAll('body *')) {
    const s = getComputedStyle(el);
    if (!/mono/i.test(s.fontFamily)) continue;
    const text = (el.textContent || '').trim();
    const looksProse = /[a-z]{4}/.test(text) && /\\s/.test(text) && text.length > 24;
    if (looksProse) monoProse.push({ cls: el.className, text: text.slice(0, 50) });
  }
  report.monoProse = monoProse;

  // 7. Chart renderer reality: ECharts paints SVG (SVG renderer), Vega-Lite
  //    emits SVG. Charts must render (or show compact empties), no zero-size
  //    containers.
  const chartSvgs = [...document.querySelectorAll('.chart-wrap svg')].map((s) => ({
    w: Math.round(s.getBoundingClientRect().width),
    h: Math.round(s.getBoundingClientRect().height),
  })).filter((s) => s.w > 0);
  const ariaCharts = [...document.querySelectorAll('[role="img"][aria-label]')]
    .map((e) => (e.getAttribute('aria-label') || '').slice(0, 70))
    .filter((t) => t.length > 0);
  const emptyBlocks = [...document.querySelectorAll('.chart-empty')].map((e) =>
    (e.textContent || '').trim().slice(0, 80)
  );
  report.charts = {
    chartSvgs,
    ariaCharts,
    emptyBlocks,
    chartWraps: document.querySelectorAll('.chart-wrap').length,
    zeroSizeCharts: [...document.querySelectorAll('.chart-wrap > *')]
      .filter((el) => el.getBoundingClientRect().width === 0).length,
  };

  return report;
}"""


def verify(vp: list[int]) -> dict:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": vp[0], "height": vp[1]})
        page = ctx.new_page()
        out = {}
        for tab in TABS:
            page.goto(f"{BASE}/?tab={tab}", wait_until="networkidle")
            page.wait_for_timeout(500)
            out[tab] = page.evaluate(VERIFY_CHECKS)
        browser.close()
        return out


def main() -> None:
    vp = json.loads(sys.argv[1]) if len(sys.argv) > 1 else [1920, 1080]
    if not health_ok():
        print("API not ready at", BASE)
        sys.exit(2)
    results, issues = capture(vp)
    print(json.dumps({"viewport": vp, "results": results, "console_issues": issues}, indent=1))


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "verify":
        vp = json.loads(sys.argv[1])
        if not health_ok():
            print("API not ready at", BASE)
            sys.exit(2)
        print(json.dumps({"viewport": vp, "checks": verify(vp)}, indent=1))
    else:
        main()