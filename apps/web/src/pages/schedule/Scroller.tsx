import { ChevronDown, ChevronLeft, ChevronRight, ChevronUp } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type HTMLAttributes, type Ref } from "react";

import { cn } from "@/lib/utils";

/**
 * A scroll area with no scroll bar. A small arrow shows at an end only when
 * there is more to see that way; clicking it scrolls on, and holding a dragged
 * card over it keeps scrolling, so a card can reach a column off screen.
 */
export function Scroller({ axis = "x", className, wrapClassName, innerRef, children, ...rest }: HTMLAttributes<HTMLDivElement> & {
  axis?: "x" | "y";
  /** Classes for the outer box that holds the arrows. */
  wrapClassName?: string;
  innerRef?: Ref<HTMLDivElement>;
}) {
  const el = useRef<HTMLDivElement | null>(null);
  const [more, setMore] = useState({ back: false, on: false });
  const check = useCallback(() => {
    const e = el.current;
    if (!e) return;
    const at = axis === "x" ? e.scrollLeft : e.scrollTop;
    const room = axis === "x" ? e.scrollWidth - e.clientWidth : e.scrollHeight - e.clientHeight;
    const next = { back: at > 2, on: at < room - 2 };
    setMore((m) => (m.back === next.back && m.on === next.on ? m : next));
  }, [axis]);
  // Content changes with every render, so the ends are checked again each time.
  useEffect(() => { check(); });
  useEffect(() => {
    const e = el.current;
    if (!e || typeof ResizeObserver === "undefined") return;
    const watch = new ResizeObserver(check);
    watch.observe(e);
    return () => watch.disconnect();
  }, [check]);

  const step = (dir: 1 | -1, amount?: number) => {
    const e = el.current;
    if (!e) return;
    const by = amount ?? (axis === "x" ? e.clientWidth : e.clientHeight) * 0.8;
    e.scrollBy?.(axis === "x" ? { left: dir * by, behavior: amount ? "auto" : "smooth" } : { top: dir * by, behavior: amount ? "auto" : "smooth" });
  };
  const setRef = (node: HTMLDivElement | null) => {
    el.current = node;
    if (typeof innerRef === "function") innerRef(node);
    else if (innerRef) (innerRef as { current: HTMLDivElement | null }).current = node;
  };
  const arrow = (dir: 1 | -1) => {
    const Icon = axis === "x" ? (dir > 0 ? ChevronRight : ChevronLeft) : (dir > 0 ? ChevronDown : ChevronUp);
    const label = axis === "x" ? (dir > 0 ? "Scroll right" : "Scroll left") : (dir > 0 ? "Scroll down" : "Scroll up");
    return (
      <button type="button" aria-label={label} tabIndex={-1}
              className={cn("sch-more", axis, dir > 0 ? "on" : "back")}
              onClick={() => step(dir)}
              onDragOver={(e) => { e.preventDefault(); step(dir, 24); }}>
        <Icon aria-hidden />
      </button>
    );
  };

  return (
    <div className={cn("sch-scroll", wrapClassName)}>
      <div ref={setRef} className={cn("no-scrollbar", className)} onScroll={check} {...rest}>{children}</div>
      {more.back && arrow(-1)}
      {more.on && arrow(1)}
    </div>
  );
}
