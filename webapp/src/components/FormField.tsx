import React from "react";
import styles from "./FormField.module.css";

export function FormField(props: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className={styles.field}>
      <div className={styles.label}>{props.label}</div>
      {props.children}
    </label>
  );
}
