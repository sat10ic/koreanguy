import React from "react";
import { classNames } from "./utils";

export function Panel({ title, right, className, children, testId }) {
  return (
    <section
      data-testid={testId}
      className={classNames(
        "border border-borderDefault bg-surface fadein",
        className
      )}
    >
      {(title || right) && (
        <header className="flex items-center justify-between border-b border-borderDefault px-4 py-2.5">
          <h3 className="text-[10px] font-medium uppercase tracking-overline text-textSecondary">
            {title}
          </h3>
          {right}
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

export function Tag({ children, color = "default", className, testId }) {
  const map = {
    default: "border-borderDefault text-textSecondary",
    bull: "border-bull/60 text-bull",
    bear: "border-bear/60 text-bear",
    warn: "border-warn/60 text-warn",
    saffron: "border-saffron/60 text-saffron",
    purple: "border-purpledot/60 text-purpledot",
    primary: "border-textPrimary/40 text-textPrimary",
    pending: "border-warn/60 text-warn",
    active: "border-bull/60 text-bull",
    exited: "border-bear/60 text-bear",
    discarded: "border-textMuted text-textMuted",
  };
  return (
    <span
      data-testid={testId}
      className={classNames(
        "inline-flex items-center border px-2 py-0.5 text-[10px] font-medium uppercase tracking-overline",
        map[color] || map.default,
        className
      )}
    >
      {children}
    </span>
  );
}

export function GradePill({ grade, className }) {
  const g = grade || "G";
  const cls = (() => {
    if (g.startsWith("A")) return "border-bull/70 text-bull bg-bull/5";
    if (g.startsWith("B")) return "border-emerald-300/60 text-emerald-300 bg-emerald-300/5";
    if (g.startsWith("C")) return "border-warn/60 text-warn bg-warn/5";
    if (g.startsWith("D") || g.startsWith("E")) return "border-orange-400/60 text-orange-400 bg-orange-400/5";
    return "border-bear/60 text-bear bg-bear/5";
  })();
  return (
    <span
      className={classNames(
        "inline-block min-w-[32px] border px-1.5 py-0.5 text-center font-mono text-[11px] font-semibold",
        cls,
        className
      )}
    >
      {g}
    </span>
  );
}

export function StatBlock({ label, value, sub, mono = true, accent }) {
  return (
    <div className="border border-borderDefault bg-surface px-4 py-3">
      <div className="text-[10px] uppercase tracking-overline text-textMuted">
        {label}
      </div>
      <div
        className={classNames(
          "mt-1 text-2xl",
          mono ? "font-mono tnum" : "",
          accent || "text-textPrimary"
        )}
      >
        {value}
      </div>
      {sub && (
        <div className="mt-0.5 text-[11px] text-textSecondary">{sub}</div>
      )}
    </div>
  );
}

export function Empty({ children, testId }) {
  return (
    <div
      data-testid={testId}
      className="flex flex-col items-center justify-center border border-dashed border-borderDefault px-4 py-10 text-textMuted"
    >
      <div className="font-mono text-[11px] uppercase tracking-overline">no data</div>
      {children && (
        <div className="mt-2 max-w-md text-center text-xs leading-relaxed text-textSecondary">
          {children}
        </div>
      )}
    </div>
  );
}

export function Spinner({ label = "loading" }) {
  return (
    <div className="flex items-center gap-2 text-textSecondary">
      <span className="inline-block h-2 w-2 animate-pulse bg-bull" />
      <span className="font-mono text-[11px] uppercase tracking-overline">{label}</span>
    </div>
  );
}

export function Button({ children, onClick, disabled, variant = "default", testId, className }) {
  const map = {
    default:
      "border-borderDefault text-textPrimary hover:bg-surfaceHover hover:text-white",
    primary:
      "border-bull/70 text-bull hover:bg-bull/10",
    danger:
      "border-bear/70 text-bear hover:bg-bear/10",
    ghost: "border-transparent text-textSecondary hover:text-white hover:bg-surfaceHover",
  };
  return (
    <button
      data-testid={testId}
      onClick={onClick}
      disabled={disabled}
      className={classNames(
        "inline-flex items-center gap-2 border px-3 py-1.5 font-mono text-[11px] uppercase tracking-overline transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        map[variant],
        className
      )}
    >
      {children}
    </button>
  );
}
