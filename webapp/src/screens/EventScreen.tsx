import React, { useEffect, useMemo, useRef, useState } from "react";
import styles from "./EventScreen.module.css";
import { GlassCard } from "../components/GlassCard";
import { FrostedHeader } from "../components/FrostedHeader";
import { daysUntil } from "../utils/date";
import { ModalSheet } from "../components/ModalSheet";
import { BottomBar } from "../components/bottombar";
import { Toast } from "../components/Toast";
import { openLink, openTelegramLink } from "../utils/telegram";
import { sendQuestion } from "../api";

const WEDDING_ISO = "2026-07-25T16:00:00+03:00";

export function EventScreen(props: { onBack: () => void; onMenu: (rect: DOMRect) => void; onAbout: () => void }) {
  const days = useMemo(() => daysUntil(WEDDING_ISO), []);
  const [askOpen, setAskOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [toastVariant, setToastVariant] = useState<"ok" | "error">("ok");
  const [question, setQuestion] = useState("");
  const mapRef = useRef<HTMLDivElement | null>(null);

  const locationName = "La Provincia";
  const locationAddress = "Калужская площадь, 1, стр. 4";
  const locationLink = "https://yandex.ru/maps/-/CLhPUAjv";
  const contactPhone = "+7 (906) 775-29-69";
  const contactTg = "https://t.me/D_Kapa";

  async function copyText(value: string) {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(value);
      } else {
        const input = document.createElement("input");
        input.value = value;
        document.body.appendChild(input);
        input.select();
        document.execCommand("copy");
        document.body.removeChild(input);
      }
      setToastVariant("ok");
      setToast("Скопировано");
      setTimeout(() => setToast(""), 2000);
    } catch {
      setToastVariant("error");
      setToast("Не удалось скопировать");
      setTimeout(() => setToast(""), 2200);
    }
  }

  useEffect(() => {
    const container = mapRef.current;
    if (!container) return;
    container.innerHTML = "";
    const script = document.createElement("script");
    script.async = true;
    script.charset = "utf-8";
    script.src = "https://api-maps.yandex.ru/services/constructor/1.0/js/?um=constructor%3Ab0b94f16c23bda1e16a4c603476f8b802833b55f665d0cafa83c9d467c00ba24&width=320&height=240&lang=ru_RU&scroll=true";
    container.appendChild(script);
    return () => {
      container.innerHTML = "";
    };
  }, []);

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
        <GlassCard title="Локация" subtitle={locationName}>
          <div className={styles.text}>Адрес: {locationAddress}</div>
          <div className={styles.mapContainer} ref={mapRef} />
          <button className={styles.secondaryBtn} onClick={() => openLink(locationLink)}>Открыть маршрут</button>
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
          <div className={styles.text}>Организатор: {contactPhone}</div>
          <div className={styles.text}>
            TG: <button className={styles.linkBtn} onClick={() => openTelegramLink(contactTg)}>@D_Kapa</button>
          </div>
          <button className={styles.secondaryBtn} onClick={() => copyText(contactPhone)}>Скопировать</button>
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
        <textarea
          className={styles.textarea}
          placeholder="Ваш вопрос..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
        />
        <button
          className={styles.submitBtn}
          onClick={async () => {
            const text = question.trim();
            if (!text) return;
            try {
              await sendQuestion(text);
              setToastVariant("ok");
              setToast("Отправлено");
              setQuestion("");
              setAskOpen(false);
            } catch (e: any) {
              const msg = String(e?.message || "");
              setToastVariant("error");
              setToast(msg.includes("Missing initData") ? "Откройте через Telegram" : "Не удалось отправить");
            } finally {
              setTimeout(() => setToast(""), 2200);
            }
          }}
        >
          Отправить
        </button>
      </ModalSheet>
      <Toast message={toast} variant={toastVariant} />
      <BottomBar
        primaryLabel="Моя анкета"
        secondaryLabel="Информация о мероприятии"
        onPrimary={props.onBack}
        onSecondary={() => {}}
      />
    </div>
  );
}
