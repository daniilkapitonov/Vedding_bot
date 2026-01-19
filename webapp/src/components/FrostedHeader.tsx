import React, { useLayoutEffect, useRef } from "react";
import styles from "./FrostedHeader.module.css";

export function FrostedHeader(props: {
  title: string;
  meta?: string;
  leftIcon: React.ReactNode;
  rightIcon: React.ReactNode;
  onLeft: () => void;
  onRight: (anchorRect: DOMRect) => void;
}) {
  const rightRef = useRef<HTMLButtonElement | null>(null);

  useLayoutEffect(() => {
    // no-op: ensures ref is set before first interaction
  }, []);

  return (
    <header className={styles.header}>
      <div className={styles.row}>
        <button className={styles.iconBtn} onClick={props.onLeft} aria-label="Left action">
          {props.leftIcon}
        </button>
        <div className={styles.center}>
          <div className={styles.title}>{props.title}</div>
          {props.meta ? <div className={styles.meta}>{props.meta}</div> : null}
        </div>
        <button
          ref={rightRef}
          className={styles.iconBtn}
          onClick={() => {
            const rect = rightRef.current?.getBoundingClientRect();
            if (rect) props.onRight(rect);
          }}
          aria-label="Menu"
        >
          {props.rightIcon}
        </button>
      </div>
    </header>
  );
}
