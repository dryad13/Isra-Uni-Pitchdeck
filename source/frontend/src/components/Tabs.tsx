import { useCallback, useRef } from "react";

export type TabItem = {
  id: string;
  label: string;
  badge?: React.ReactNode;
};

type Variant = "default" | "toolbar" | "filter";

type Props = {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  variant?: Variant;
  ariaLabel?: string;
  className?: string;
};

function variantClass(variant: Variant) {
  switch (variant) {
    case "toolbar":
      return "tabs-variant-toolbar";
    case "filter":
      return "tabs-variant-filter";
    default:
      return "tabs-variant-default";
  }
}

export default function Tabs({
  items,
  activeId,
  onChange,
  variant = "default",
  ariaLabel,
  className = "",
}: Props) {
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent, index: number) => {
      let next = index;
      if (e.key === "ArrowRight") next = (index + 1) % items.length;
      else if (e.key === "ArrowLeft") next = (index - 1 + items.length) % items.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = items.length - 1;
      else return;
      e.preventDefault();
      const item = items[next];
      if (item) {
        onChange(item.id);
        tabRefs.current[next]?.focus();
      }
    },
    [items, onChange],
  );

  return (
    <div
      className={`tabs-unified ${variantClass(variant)} ${className}`.trim()}
      role="tablist"
      aria-label={ariaLabel}
    >
      {items.map((item, index) => {
        const active = item.id === activeId;
        return (
          <button
            key={item.id}
            ref={(el) => {
              tabRefs.current[index] = el;
            }}
            type="button"
            role="tab"
            className={`tabs-unified-tab${active ? " tabs-unified-tab-active" : ""}`}
            aria-selected={active}
            tabIndex={active ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={(e) => onKeyDown(e, index)}
          >
            {item.label}
            {item.badge}
          </button>
        );
      })}
    </div>
  );
}
