import { animate } from "framer-motion";
import { useEffect, useRef, useState } from "react";

// E-4.6: count-up so a refresh visibly CHANGES a number (the breadth/hero
// figures) instead of silently swapping text. Runs under MotionConfig
// reducedMotion="user", which snaps instead of animating when the OS asks.
export function CountUp({ value, format, className, title }: {
  value: number;
  format: (v: number) => string;
  className?: string;
  title?: string;
}) {
  const [display, setDisplay] = useState(value);
  const prev = useRef(value);

  useEffect(() => {
    const from = prev.current;
    prev.current = value;
    if (from === value) {
      setDisplay(value);
      return;
    }
    const controls = animate(from, value, {
      duration: 0.6,
      ease: "easeOut",
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [value]);

  return (
    <span className={className} title={title}>
      {format(display)}
    </span>
  );
}
