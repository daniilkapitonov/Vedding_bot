import React from "react";
import styles from "./TimingBlock.module.css";

export function TimingBlock(props: { items: Array<{ time: string; title: string }> }) {
  return (
    <div className={styles.timeline}>
      {props.items.map((item) => (
        <div key={`${item.time}-${item.title}`} className={styles.timeRow}>
          <span className={styles.timeDot} />
          <span className={styles.timeBadge}>{item.time}</span>
          <span>{item.title}</span>
        </div>
      ))}
    </div>
  );
}
