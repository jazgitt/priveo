import { useRef, type KeyboardEvent, type ReactNode } from "react";

import "./tabs.css";

export interface TabDef {
  id: string;
  label: string;
}

/**
 * A row of tabs with one panel below it. The arrow keys, Home and End move
 * between tabs. Only the active panel is shown, so a page with several
 * sections shows one at a time.
 */
export function Tabs({ tabs, active, onChange, label, children }: {
  tabs: readonly TabDef[];
  active: string;
  onChange: (id: string) => void;
  label: string;
  children: ReactNode;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function move(e: KeyboardEvent, index: number) {
    const last = tabs.length - 1;
    const next = e.key === "ArrowRight" ? (index === last ? 0 : index + 1)
      : e.key === "ArrowLeft" ? (index === 0 ? last : index - 1)
      : e.key === "Home" ? 0
      : e.key === "End" ? last
      : -1;
    if (next < 0) return;
    e.preventDefault();
    onChange(tabs[next].id);
    refs.current[tabs[next].id]?.focus();
  }

  return (
    <>
      <div className="tabs" role="tablist" aria-label={label}>
        {tabs.map((t, i) => (
          <button key={t.id} type="button" role="tab" id={`tab-${t.id}`}
                  className="tab" aria-selected={active === t.id}
                  aria-controls={`panel-${t.id}`} tabIndex={active === t.id ? 0 : -1}
                  ref={(el) => { refs.current[t.id] = el; }}
                  onClick={() => onChange(t.id)} onKeyDown={(e) => move(e, i)}>
            {t.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${active}`} aria-labelledby={`tab-${active}`}>
        {children}
      </div>
    </>
  );
}
