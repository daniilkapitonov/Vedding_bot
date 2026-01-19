import React, { useMemo, useState } from "react";
import styles from "./EventScreen.module.css";
import { GlassCard } from "../components/GlassCard";
import { FrostedHeader } from "../components/FrostedHeader";
import { daysUntil } from "../utils/date";
import { ModalSheet } from "../components/ModalSheet";
import { BottomBar } from "../components/bottombar";

const WEDDING_ISO = "2026-07-25T16:00:00+03:00";

export function EventScreen(props: { onBack: () => void; onMenu: (rect: DOMRect) => void; onAbout: () => void }) {
  const days = useMemo(() => daysUntil(WEDDING_ISO), []);
  const [askOpen, setAskOpen] = useState(false);

  return (
    <div className={styles.page}>
      <FrostedHeader
        title="Информация о событии"
        meta={`До свадьбы — ${days} дней`}
        leftIcon="←"
        rightIcon="…"
        onLeft={props.onBack}
        onRight={props.onMenu}
      />

      <main className={styles.content}>
        <GlassCard title="Локация" subtitle="La Provincia">
          <div className={styles.text}>Адрес: ул. Итальянская, 10 (пример)</div>
          <div className={styles.mapPlaceholder}>Карта</div>
          <button className={styles.secondaryBtn}>Открыть маршрут</button>
        </GlassCard>

        <GlassCard title="Тайминг">
          <div className={styles.timeline}>
            {[
              ["16:00", "Сбор гостей"],
              ["17:00", "Церемония"],
              ["18:00", "Банкет"],
              ["21:30", "Торт"],
            ].map(([time, label]) => (
              <div key={label} className={styles.timeRow}>
                <span className={styles.timeBadge}>{time}</span>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard title="Дресс-код">
          <div className={styles.text}>Тёплые нейтральные оттенки, пастельные акценты.</div>
          <div className={styles.colorRow}>
            <span className={styles.dot} data-color="olive" />
            <span className={styles.dot} data-color="emerald" />
            <span className={styles.dot} data-color="gold" />
          </div>
        </GlassCard>

        <GlassCard title="Контакты">
          <div className={styles.text}>Организатор: +7 (999) 000‑00‑00</div>
          <button className={styles.secondaryBtn}>Скопировать</button>
        </GlassCard>

        <GlassCard title="Подарки">
          <div className={styles.text}>Лучший подарок — вклад в наше путешествие или сертификат.</div>
        </GlassCard>
        <GlassCard title="Дети">
          <div className={styles.text}>Мы будем рады детям, но отметьте это заранее в анкете.</div>
        </GlassCard>
        <GlassCard title="Вопросы">
          <div className={styles.faqItem}>Можно ли взять +1? — Да, укажите в разделе “Семья”.</div>
          <div className={styles.faqItem}>Есть ли дресс-код? — Тёплые нейтральные оттенки.</div>
          <div className={styles.faqItem}>Можно ли фото? — Конечно, будем рады.</div>
        </GlassCard>
        <button className={styles.askBtn} onClick={() => setAskOpen(true)}>Задать вопрос</button>

        <GlassCard title="Как добавить партнёра">
          <div className={styles.text}>
            Откройте раздел “Семья”, включите «Буду с парой» и отправьте приглашение по ФИО.
            Мы аккуратно всё свяжем.
          </div>
        </GlassCard>
      </main>

      <ModalSheet open={askOpen} onClose={() => setAskOpen(false)} title="Вопрос">
        <textarea className={styles.textarea} placeholder="Ваш вопрос..." />
        <button className={styles.submitBtn}>Отправить</button>
      </ModalSheet>
      <BottomBar
        primaryLabel="Моя анкета"
        secondaryLabel="Информация о мероприятии"
        onPrimary={props.onBack}
        onSecondary={() => {}}
      />
    </div>
  );
}
