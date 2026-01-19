import React, { useMemo } from "react";

function daysUntil(dateISO: string): number {
  // Count full days in UTC+3-ish by using date components
  const target = new Date(dateISO);
  const now = new Date();
  const diff = target.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000*60*60*24)));
}

export function Topbar(props: { weddingISO: string }) {
  const d = useMemo(() => daysUntil(props.weddingISO), [props.weddingISO]);
  return (
    <div style={{
      position:"sticky", top:0, zIndex: 10,
      background:"rgba(11,18,32,0.82)",
      backdropFilter:"blur(10px)",
      borderBottom:"1px solid var(--border)",
      padding:"12px 14px",
      display:"flex",
      alignItems:"center",
      justifyContent:"space-between"
    }}>
      <div style={{display:"flex", flexDirection:"column", gap:2}}>
        <div style={{fontSize: 13, color:"var(--muted)"}}>До свадьбы</div>
        <div style={{fontSize: 18, fontWeight: 700}}>{d} дней</div>
      </div>
      <div style={{textAlign:"right"}}>
        <div style={{fontSize: 13, color:"var(--muted)"}}>Дата</div>
        <div style={{fontSize: 15, fontWeight: 600}}>25.07.2026</div>
      </div>
    </div>
  );
}
