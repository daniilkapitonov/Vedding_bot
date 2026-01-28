import React from "react";
import styles from "./LoadingScreen.module.css";

export function LoadingScreen(props: { animate?: boolean }) {
  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={`${styles.shimmer} ${props.animate === false ? styles.noAnim : ""}`} />
        <div className={styles.title}>Готовим пространство ✨</div>
        <div className={styles.subtitle}>Это займёт несколько секунд…</div>
      </div>
    </div>
  );
}
