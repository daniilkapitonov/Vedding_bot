import React, { useState } from "react";
import { Card } from "../components/card";
import { api } from "../api";

export default function Family(props: { locked: boolean }) {
  const [name, setName] = useState("");
  const [bd, setBd] = useState("");
  const [msg, setMsg] = useState("");

  async function link() {
    setMsg("");
    try {
      if (!name.trim() || !bd) throw new Error();
      await api.linkPartner({ full_name: name.trim(), birth_date: bd });
      setMsg("Запрос сохранён. Если человек уже зарегистрирован — связь появится автоматически.");
    } catch {
      setMsg("Ошибка. Проверьте ФИО и дату рождения.");
    }
  }

  return (
    <div style={{padding: 14, display:"flex", flexDirection:"column", gap: 12}}>
      <Card title="Пара и дети">
        {props.locked ? (
          <div style={{fontSize: 13, color:"var(--muted)"}}>
            Недоступно, потому что вы указали “не смогу присутствовать”.
          </div>
        ) : (
          <div style={{display:"grid", gap:10}}>
            <div style={{fontSize: 13, color:"var(--muted)"}}>
              Партнёр: укажите ФИО и дату рождения. Система свяжет вас, если партнёр уже зарегистрирован.
            </div>
            <label>
              <div style={lbl}>ФИО партнёра</div>
              <input value={name} onChange={e=>setName(e.target.value)} style={inp}/>
            </label>
            <label>
              <div style={lbl}>Дата рождения партнёра</div>
              <input type="date" value={bd} onChange={e=>setBd(e.target.value)} style={inp}/>
            </label>
            {msg ? <div style={{fontSize: 13, color:"var(--muted)"}}>{msg}</div> : null}
            <button onClick={link} style={btn}>Сохранить</button>

            <div style={{marginTop: 12, fontSize: 13, color:"var(--muted)"}}>
              Дети (с Telegram) добавим в следующей итерации: нужен UX “пригласить ребёнка/аккаунт” либо “связать по ФИО+ДР”.
            </div>
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
