import React from "react";
import styles from "./BottomBar.module.css";

export function BottomBar(props: {
  primaryLabel: string;
  secondaryLabel: string;
  onPrimary: () => void;
  onSecondary: () => void;
}) {
  return (
    <nav className={styles.bar}>
      <button className={`${styles.btn} ${styles.btnSecondary}`} onClick={props.onSecondary}>
        {props.secondaryLabel}
      </button>
      <button className={`${styles.btn} ${styles.btnPrimary}`} onClick={props.onPrimary}>
        {props.primaryLabel}
      </button>
    </nav>
  );
}
