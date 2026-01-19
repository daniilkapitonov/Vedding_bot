import React from "react";
import ReactDOM from "react-dom";
import styles from "./ModalSheet.module.css";

export function ModalSheet(props: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!props.open) return null;
  return ReactDOM.createPortal(
    <>
      <div className={styles.backdrop} onClick={props.onClose} />
      <div className={styles.sheet}>
        <div className={styles.panel}>
          <div className={styles.header}>
            <div className={styles.title}>{props.title}</div>
            <button className={styles.close} onClick={props.onClose} aria-label="Close">
              ✕
            </button>
          </div>
          <div className={styles.body}>{props.children}</div>
        </div>
      </div>
    </>,
    document.body
  );
}
