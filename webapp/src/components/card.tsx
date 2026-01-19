import React from "react";

export function Card(props: {title?: string; children: React.ReactNode}) {
  return (
    <div style={{
      background: "var(--card)",
      border: "1px solid var(--border)",
      borderRadius: 18,
      padding: 14,
      boxShadow: "0 10px 30px rgba(0,0,0,0.25)"
    }}>
      {props.title ? <div style={{fontSize: 14, color:"var(--muted)", marginBottom: 10}}>{props.title}</div> : null}
      {props.children}
    </div>
  );
}
