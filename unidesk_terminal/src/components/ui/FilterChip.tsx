interface FilterChipProps {
  label: string;
  active: boolean;
  onClick: () => void;
}

export function FilterChip({ label, active, onClick }: FilterChipProps) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      className={`shrink-0 rounded-chip border px-2.5 py-1 text-caption font-medium transition-colors duration-150 ease-out ${
        active
          ? "border-accent-border bg-accent-bg text-accent-strong"
          : "border-border-subtle text-ink-tertiary hover:border-border hover:text-ink-secondary"
      }`}
    >
      {label}
    </button>
  );
}
