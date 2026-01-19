import React, { useEffect, useState } from "react";
import { Card } from "../components/card";
import { api } from "../api";

export default function Me(props: { locked: boolean }) {
  const [p, setP] = useState<any>(null);

  useEffect(() => {
    api.getProfile().then(setP).catch(()=>setP({error:true}));
  }, []);

  return (
    <div style={{padding: 14, display:"flex", flexDirection:"column", gap: 12}}>
      <Card title="О себе">
        {!p ? "Загрузка..." : p.error ? "Не удалось загрузить." : (
          <div style={{display:"grid", gap:8}}>
            <Row k="RSVP" v={p.rsvp_status}/>
            <Row k="ФИО" v={p.full_name}/>
            <Row k="Дата рождения" v={p.birth_date}/>
            <Row k="Пол" v={p.gender}/>
            <Row k="Телефон" v={p.phone}/>
            <Row k="Сторона" v={p.side}/>
            <Row k="Родственник" v={p.is_relative ? "Да" : "Нет"}/>
            <Row k="Еда" v={p.food_pref}/>
            <Row k="Аллергии" v={p.food_allergies}/>
            <Row k="Алкоголь" v={(p.alcohol_prefs || []).join(", ")}/>
            <Row k="Пара (linked)" v={p.partner_guest_id ? String(p.partner_guest_id) : "—"}/>
            <Row k="Пара (pending)" v={p.partner_pending_full_name ? `${p.partner_pending_full_name} / ${p.partner_pending_birth_date}` : "—"}/>
          </div>
        )}
      </Card>
      <Card title="Правки">
        <div style={{fontSize: 13, color:"var(--muted)"}}>
          В MVP редактирование анкеты делаем через повторный Onboarding (кнопка “Поменять решение/данные” на главной).
          Следующим шагом вынесем редактирование в этот раздел.
        </div>
      </Card>
    </div>
  );
}

function Row(props: {k: string; v: any}) {
  return (
    <div style={{display:"flex", justifyContent:"space-between", gap: 10}}>
      <div style={{fontSize: 12, color:"var(--muted)"}}>{props.k}</div>
      <div style={{fontSize: 13, textAlign:"right"}}>{props.v ?? "—"}</div>
    </div>
  );
}
