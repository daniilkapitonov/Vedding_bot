import React from "react";
import styles from "./Toast.module.css";

export function Toast(props: { message: string; variant?: "ok" | "error" }) {
  if (!props.message) return null;
  return (
    <div className={`${styles.toast} ${props.variant === "error" ? styles.error : ""}`}>
      {props.message}
    </div>
  );
}
