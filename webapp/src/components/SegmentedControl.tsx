import React from "react";
import styles from "./SegmentedControl.module.css";

export type SegValue = "yes" | "no" | "maybe";

const OPTIONS: { label: string; value: SegValue }[] = [
  { label: "Да", value: "yes" },
  { label: "Нет", value: "no" },
  { label: "Пока не знаю", value: "maybe" },
];

export function SegmentedControl(props: {
  value: SegValue;
  onChange: (value: SegValue) => void;
}) {
  return (
    <div className={styles.wrap} role="group" aria-label="RSVP">
      {OPTIONS.map((opt) => {
        const active = opt.value === props.value;
        return (
          <button
            key={opt.value}
            className={`${styles.btn} ${active ? styles.btnActive : ""}`}
            aria-pressed={active}
            onClick={() => props.onChange(opt.value)}
          >
            {opt.label}
            {active ? <span className={styles.mark} aria-hidden="true" /> : null}
          </button>
        );
      })}
    </div>
  );
}
