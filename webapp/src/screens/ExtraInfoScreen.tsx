import React, { useState } from "react";
import styles from "./ExtraInfoScreen.module.css";
import { FrostedHeader } from "../components/FrostedHeader";
import { GlassCard } from "../components/GlassCard";
import { ModalSheet } from "../components/ModalSheet";

export function ExtraInfoScreen(props: { onBack: () => void; onMenu: (rect: DOMRect) => void }) {
  const [askOpen, setAskOpen] = useState(false);
  return (
    <div className={styles.page}>
      <FrostedHeader
        title="Доп. инфо"
        meta=""
        leftIcon="←"
        rightIcon="…"
        onLeft={props.onBack}
        onRight={props.onMenu}
      />

      <main className={styles.content}>
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
      </main>

      <ModalSheet open={askOpen} onClose={() => setAskOpen(false)} title="Вопрос">
        <textarea className={styles.textarea} placeholder="Ваш вопрос..." />
        <button className={styles.submitBtn}>Отправить</button>
      </ModalSheet>
    </div>
  );
}
