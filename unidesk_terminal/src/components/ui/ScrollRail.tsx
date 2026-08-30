import { useEffect, useRef, useState, type ReactNode } from "react";

/* Horizontal rail with a right-edge fade that only appears when there is
   actually more content to scroll to — a fade on a fully-visible row would
   falsely imply more exists. */
export function ScrollRail({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [overflowing, setOverflowing] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setOverflowing(el.scrollWidth - el.clientWidth - el.scrollLeft > 4);
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    el.addEventListener("scroll", check);
    return () => {
      ro.disconnect();
      el.removeEventListener("scroll", check);
    };
  }, [children]);

  return (
    <div
      ref={ref}
      className={`flex gap-3 overflow-x-auto pb-1 ${overflowing ? "scroll-fade-x" : ""}`}
    >
      {children}
    </div>
  );
}
