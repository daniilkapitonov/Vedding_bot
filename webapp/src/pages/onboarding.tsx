import React, { useState } from "react";
import { Card } from "../components/card";
import { api } from "../api";

const alcoholOptions = [
  "wine", "beer", "sparkling", "vodka", "whiskey", "cocktails", "any", "none"
];

export default function Onboarding(props: { onDone: () => void }) {
  const [rsvp, setRsvp] = useState<"yes"|"no"|"maybe">("yes");
  const [fullName, setFullName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState<"male"|"female"|"other">("male");
  const [phone, setPhone] = useState("");
  const [side, setSide] = useState<"groom"|"bride"|"both">("groom");
  const [isRelative, setIsRelative] = useState(false);
  const [food, setFood] = useState<"fish"|"meat"|"vegan">("meat");
  const [allergies, setAllergies] = useState("");
  const [alcohol, setAlcohol] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function toggleAlcohol(k: string) {
    setAlcohol(prev => prev.includes(k) ? prev.filter(x=>x!==k) : [...prev, k]);
  }

  async function submit() {
    setErr(null);
    setSaving(true);
    try {
      if (rsvp === "no") {
        // Minimum: only name required
        if (!fullName.trim()) throw new Error("Укажите Имя и Фамилию");
        await api.saveProfile({
          rsvp_status: rsvp,
          full_name: fullName.trim(),
          birth_date: birthDate ? birthDate : null,
          gender: null,
          phone: null,
          side: null,
          is_relative: false,
          food_pref: null,
          food_allergies: null,
          alcohol_prefs: []
        });
        props.onDone();
        return;
      }

      if (!fullName.trim()) throw new Error("Укажите ФИО");
      if (!birthDate) throw new Error("Укажите дату рождения");

      await api.saveProfile({
        rsvp_status: rsvp,
        full_name: fullName.trim(),
        birth_date: birthDate,
        gender,
        phone: phone || null,
        side,
        is_relative: isRelative,
        food_pref: food,
        food_allergies: allergies || null,
        alcohol_prefs: alcohol
      });
      props.onDone();
    } catch (e: any) {
      setErr(e?.message || "Ошибка");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{padding: 14, display:"flex", flexDirection:"column", gap: 12}}>
      <Card title="Сможете присутствовать?">
        <div style={{display:"flex", gap:8, flexWrap:"wrap"}}>
          {[
            {k:"yes", t:"Да"},
            {k:"no", t:"Нет"},
            {k:"maybe", t:"Пока не знаю"},
          ].map(x=>(
            <button key={x.k} onClick={()=>setRsvp(x.k as any)} style={{
              padding:"10px 12px",
              borderRadius: 14,
              border:"1px solid var(--border)",
              background: rsvp===x.k ? "var(--card2)" : "transparent",
              cursor:"pointer"
            }}>{x.t}</button>
          ))}
        </div>
      </Card>

      <Card title={rsvp==="no" ? "Минимальные данные" : "Основная анкета"}>
        <div style={{display:"grid", gap:10}}>
          <label>
            <div style={{fontSize:12, color:"var(--muted)"}}>ФИО</div>
            <input value={fullName} onChange={e=>setFullName(e.target.value)} style={inp}/>
          </label>

          <label>
            <div style={{fontSize:12, color:"var(--muted)"}}>Дата рождения</div>
            <input type="date" value={birthDate} onChange={e=>setBirthDate(e.target.value)} style={inp}/>
          </label>

          {rsvp !== "no" ? (
            <>
              <label>
                <div style={{fontSize:12, color:"var(--muted)"}}>Пол</div>
                <select value={gender} onChange={e=>setGender(e.target.value as any)} style={inp}>
                  <option value="male">Мужской</option>
                  <option value="female">Женский</option>
                  <option value="other">Другое</option>
                </select>
              </label>

              <label>
                <div style={{fontSize:12, color:"var(--muted)"}}>Телефон</div>
                <input value={phone} onChange={e=>setPhone(e.target.value)} placeholder="+7 ..." style={inp}/>
              </label>

              <label>
                <div style={{fontSize:12, color:"var(--muted)"}}>С чьей стороны</div>
                <select value={side} onChange={e=>setSide(e.target.value as any)} style={inp}>
                  <option value="groom">Жених</option>
                  <option value="bride">Невеста</option>
                  <option value="both">Общий</option>
                </select>
              </label>

              <label style={{display:"flex", alignItems:"center", gap:10}}>
                <input type="checkbox" checked={isRelative} onChange={e=>setIsRelative(e.target.checked)} />
                <div>Родственник</div>
              </label>

              <label>
                <div style={{fontSize:12, color:"var(--muted)"}}>Еда</div>
                <select value={food} onChange={e=>setFood(e.target.value as any)} style={inp}>
                  <option value="meat">Мясо</option>
                  <option value="fish">Рыба</option>
                  <option value="vegan">Vegan</option>
                </select>
              </label>

              <label>
                <div style={{fontSize:12, color:"var(--muted)"}}>Аллергии/ограничения</div>
                <textarea value={allergies} onChange={e=>setAllergies(e.target.value)} style={{...inp, height: 80}}/>
              </label>

              <div>
                <div style={{fontSize:12, color:"var(--muted)", marginBottom: 8}}>Алкоголь (можно несколько)</div>
                <div style={{display:"flex", flexWrap:"wrap", gap:8}}>
                  {alcoholOptions.map(k => (
                    <button key={k} onClick={()=>toggleAlcohol(k)} style={{
                      padding:"8px 10px",
                      borderRadius: 14,
                      border:"1px solid var(--border)",
                      background: alcohol.includes(k) ? "var(--card2)" : "transparent",
                      cursor:"pointer",
                      fontSize: 12
                    }}>
                      {k === "any" ? "Без разницы" : k === "none" ? "Не пью" : k}
                    </button>
                  ))}
                </div>
              </div>
            </>
          ) : null}

          {err ? <div style={{color:"var(--danger)", fontSize: 13}}>{err}</div> : null}
          <button onClick={submit} disabled={saving} style={btn}>
            {saving ? "Сохраняю..." : (rsvp === "no" ? "Сохранить решение" : "Сохранить анкету")}
          </button>
        </div>
      </Card>
    </div>
  );
}

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
  background:"linear-gradient(135deg, rgba(42,171,238,0.35), rgba(0,168,132,0.20))",
  color:"var(--text)",
  fontWeight: 700,
  cursor:"pointer"
};
