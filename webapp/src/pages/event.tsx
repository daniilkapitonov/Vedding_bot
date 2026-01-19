import React, { useEffect, useState } from "react";
import { Card } from "../components/card";
import { api } from "../api";

export default function EventPage(props: { locked: boolean }) {
  const [content, setContent] = useState<string>("Загрузка...");
  const [updatedAt, setUpdatedAt] = useState<string>("");

  useEffect(() => {
    api.eventInfo().then((r:any) => {
      setContent(r.content);
      setUpdatedAt(r.updated_at);
    }).catch(()=>setContent("Не удалось загрузить информацию."));
  }, []);

  return (
    <div style={{padding: 14, display:"flex", flexDirection:"column", gap: 12}}>
      <Card title="Общая информация о мероприятии">
        <div style={{whiteSpace:"pre-wrap", lineHeight: 1.45}}>{content}</div>
        {updatedAt ? <div style={{marginTop: 10, fontSize: 12, color:"var(--muted)"}}>Обновлено: {updatedAt}</div> : null}
      </Card>
      {props.locked ? (
        <Card title="Примечание">
          <div style={{fontSize: 13, color:"var(--muted)"}}>
            Вы указали, что не сможете присутствовать. Раздел доступен только для чтения.
          </div>
        </Card>
      ) : null}
    </div>
  );
}
