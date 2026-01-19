import React from "react";
import ReactDOM from "react-dom";
import styles from "./BottomSheet.module.css";

export function BottomSheet(props: {
  open: boolean;
  onClose: () => void;
  items: Array<{ label: string; onClick: () => void }>;
  anchorRect?: DOMRect | null;
}) {
  if (!props.open) return null;
  const anchor = props.anchorRect;
  const style = anchor
    ? {
        top: Math.round(anchor.bottom + 8),
        left: Math.round(Math.max(12, anchor.left - 140)),
      }
    : undefined;
  return ReactDOM.createPortal(
    <>
      <div className={styles.backdrop} onClick={props.onClose} />
      <div className={anchor ? styles.menu : styles.sheet} style={style}>
        <div className={styles.panel}>
          {anchor ? null : <div className={styles.handle} />}
          {props.items.map((item) => (
            <button
              key={item.label}
              className={styles.item}
              onClick={() => {
                item.onClick();
                props.onClose();
              }}
            >
              {item.label}
              <span>›</span>
            </button>
          ))}
        </div>
      </div>
    </>,
    document.body
  );
}
