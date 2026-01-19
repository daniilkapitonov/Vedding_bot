import React from "react";
import styles from "./ChipsMultiSelect.module.css";

export function ChipsMultiSelect(props: {
  options: string[];
  value: string[];
  onChange: (next: string[]) => void;
  exclusiveLabel?: string;
}) {
  return (
    <div className={styles.chips} role="listbox" aria-multiselectable>
      {props.options.map((opt) => {
        const on = props.value.includes(opt);
        return (
          <button
            key={opt}
            className={`${styles.chip} ${on ? styles.chipOn : ""}`}
            aria-pressed={on}
            onClick={() => {
              const exclusive = props.exclusiveLabel;
              let next = on
                ? props.value.filter((v) => v !== opt)
                : [...props.value, opt];
              if (exclusive) {
                if (opt === exclusive && !on) {
                  next = [exclusive];
                } else if (opt !== exclusive && next.includes(exclusive)) {
                  next = next.filter((v) => v !== exclusive);
                }
              }
              props.onChange(next);
            }}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}
