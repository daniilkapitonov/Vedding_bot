import React, { useEffect, useState } from "react";
import { Card } from "../components/card";
import { api } from "../api";

export default function Extra(props: { locked: boolean; side: string | null }) {
  const [knownSince, setKnownSince] = useState<string>("both");
  const [memory, setMemory] = useState("");
  const [fact, setFact] = useState("");
  const [photos, setPhotos] = useState<string>("");
  const [msg, setMsg] = useState<string>("");

  useEffect(() => {
    api.getProfile().then((p:any) => {
      setKnownSince(p.extra_known_since || p.side || "both");
      setMemory(p.extra_memory || "");
      setFact(p.extra_fact || "");
      setPhotos((p.photos || []).join("\n"));
    });
  }, []);

  const who = knownSince === "groom" ? "женихом" : knownSince === "bride" ? "невестой" : "обоими";

  async function save() {
    setMsg("");
    try {
      const list = photos.split("\n").map(s=>s.trim()).filter(Boolean).slice(0,5);
      await api.saveExtra({
        extra_known_since: knownSince,
        extra_memory: memory,
        extra_fact: fact,
        photos: list
      });
      setMsg("Сохранено.");
    } catch {
      setMsg("Ошибка сохранения.");
    }
  }

  return (
    <div style={{padding: 14, display:"flex", flexDirection:"column", gap: 12}}>
      <Card title="Дополнительная информация">
        {props.locked ? (
          <div style={{fontSize: 13, color:"var(--muted)"}}>
            Недоступно, потому что вы указали “не смогу присутствовать”.
          </div>
        ) : (
          <div style={{display:"grid", gap:10}}>
            <label>
              <div style={lbl}>С кем вы знакомы ближе?</div>
              <select value={knownSince} onChange={e=>setKnownSince(e.target.value)} style={inp}>
                <option value="groom">С женихом</option>
                <option value="bride">С невестой</option>
                <option value="both">С обоими</option>
              </select>
            </label>

            <label>
              <div style={lbl}>Самое яркое воспоминание, связанное с {who}</div>
              <textarea value={memory} onChange={e=>setMemory(e.target.value)} style={{...inp, height: 90}}/>
            </label>

            <label>
              <div style={lbl}>Интересный факт о {who}</div>
              <textarea value={fact} onChange={e=>setFact(e.target.value)} style={{...inp, height: 70}}/>
            </label>

            <label>
              <div style={lbl}>До 5 фото (Telegram file_id, по одному в строке)</div>
              <textarea value={photos} onChange={e=>setPhotos(e.target.value)} style={{...inp, height: 110}}/>
              <div style={{fontSize: 12, color:"var(--muted)", marginTop: 6}}>
                В MVP фото добавляем через отправку в бота: он вернёт file_id, вставьте сюда.
              </div>
            </label>

            {msg ? <div style={{fontSize: 13, color:"var(--muted)"}}>{msg}</div> : null}
            <button onClick={save} style={btn}>Сохранить</button>
          </div>
        )}
      </Card>
    </div>
  );
}

const lbl: React.CSSProperties = {fontSize:12, color:"var(--muted)", marginBottom: 6};
const inp: React.CSSProperties = {
  width:"100%",
  padding:"10px 12px",
  borderRadius: 14,
  border:"1px solid var(--border)",
  background:"rgba(255,255,255,0.04)",
  color:"var(--text)",
  outline:"none"
};
const btn: React.CSSProperties = {
  padding:"12px 12px",
  borderRadius: 16,
  border:"1px solid var(--border)",
  background:"var(--card2)",
  color:"var(--text)",
  fontWeight: 700,
  cursor:"pointer"
};
