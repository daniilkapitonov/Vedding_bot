import React from "react";
import styles from "./GlassCard.module.css";

export function GlassCard(props: { title?: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className={styles.card}>
      <div className={styles.inner}>
        {props.title ? <h3 className={styles.title}>{props.title}</h3> : null}
        {props.subtitle ? <p className={styles.subtitle}>{props.subtitle}</p> : null}
        {props.children}
      </div>
    </section>
  );
}
