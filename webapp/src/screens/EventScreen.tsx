import React, { useEffect, useMemo, useRef, useState } from "react";
import styles from "./EventScreen.module.css";
import { GlassCard } from "../components/GlassCard";
import { FrostedHeader } from "../components/FrostedHeader";
import { daysUntil } from "../utils/date";
import { ModalSheet } from "../components/ModalSheet";
import { BottomBar } from "../components/bottombar";
import { Toast } from "../components/Toast";
import { openLink, openTelegramLink } from "../utils/telegram";
import { sendQuestion, api } from "../api";
import { TimingBlock } from "../components/TimingBlock";

const WEDDING_ISO = "2026-07-25T16:00:00+03:00";

export function EventScreen(props: { onBack: () => void; onMenu: (rect: DOMRect) => void; onAbout: () => void }) {
  const days = useMemo(() => daysUntil(WEDDING_ISO), []);
  const [askOpen, setAskOpen] = useState(false);
  const [toast, setToast] = useState("");
  const [toastVariant, setToastVariant] = useState<"ok" | "error">("ok");
  const [question, setQuestion] = useState("");
  const mapRef = useRef<HTMLDivElement | null>(null);
  const [content, setContent] = useState<any | null>(null);
  const [timing, setTiming] = useState<Array<{ time: string; title: string }>>([]);
  const [timingError, setTimingError] = useState(false);

  const locationName = "La Provincia";
  const locationAddress = "Калужская площадь, 1, стр. 4";
  const locationLink = "https://yandex.ru/maps/-/CLhPUAjv";
  const contactPhone = "+7 (906) 775-29-69";
  const contactTg = "https://t.me/D_Kapa";
  const fallback = {
    dresscode_text: "Тёплые нейтральные оттенки, пастельные акценты.",
    contacts_text: "Организатор: +7 (906) 775-29-69, TG: @D_Kapa",
    gifts_text: "Лучший подарок — вклад в наше путешествие или сертификат.",
    faq_text: "Можно ли взять +1? — Да, укажите в разделе “Семья”.\nЕсть ли дресс-код? — Тёплые нейтральные оттенки.\nМожно ли фото? — Конечно, будем рады.",
    how_to_add_partner_text: "Откройте раздел «Семья» и отправьте приглашение по Telegram нику (@username).",
    event_location_text: "",
  };

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
    script.src = "https://api-maps.yandex.ru/services/constructor/1.0/js/?um=constructor%3Ab0b94f16c23bda1e16a4c603476f8b802833b55f665d0cafa83c9d467c00ba24&width=100%25&height=100%25&lang=ru_RU&scroll=true";
    container.appendChild(script);
    return () => {
      container.innerHTML = "";
    };
  }, []);

  useEffect(() => {
    api.eventContent()
      .then((data: any) => setContent(data || {}))
      .catch(() => setContent({}));
    api.eventTimingMe()
      .then((res: any) => {
        setTimingError(false);
        setTiming(res?.items || []);
      })
      .catch(() => {
        setTimingError(true);
        setTiming([]);
        setToastVariant("error");
        setToast("Не удалось загрузить расписание");
        setTimeout(() => setToast(""), 2200);
      });
  }, []);

  function renderTextBlock(value?: string) {
    if (!value) return null;
    const lines = value.split("\n");
    return (
      <div className={styles.textBlock}>
        {lines.map((line, idx) => {
          const trimmed = line.trim();
        if (!trimmed) return <div key={idx} className={styles.textSpacer} />;
        if (trimmed.startsWith("- ")) {
          return (
            <div key={idx} className={styles.bulletItem}>
              <span className={styles.bulletDot} />
              <span>{trimmed.slice(2)}</span>
            </div>
          );
        }
        return <div key={idx} className={styles.textLine}>{trimmed}</div>;
      })}
    </div>
  );
}

  function parseSections(rawText?: string) {
    if (!rawText) return {};
    const lines = rawText.split("\n");
    const map: Record<string, string[]> = {};
    let current = "";
    const isHeading = (line: string) => {
      const t = line.trim();
      if (!t) return false;
      if (t.length > 40) return false;
      if (t.includes(":")) return false;
      const known = ["Дресс-код", "Контакты", "Подарки", "Вопросы", "FAQ", "Как добавить партнёра", "Локация"];
      return known.includes(t) || /^[A-ZА-ЯЁ][^.!?]{2,40}$/.test(t);
    };
    lines.forEach((ln) => {
      const t = ln.trim();
      if (isHeading(t)) {
        current = t;
        if (!map[current]) map[current] = [];
      } else if (current) {
        map[current].push(ln);
      }
    });
    return map;
  }

  const rawCombined =
    content?.full_text ||
    content?.raw_text ||
    [
      content?.event_location_text,
      content?.dresscode_text,
      content?.contacts_text,
      content?.gifts_text,
      content?.faq_text,
      content?.how_to_add_partner_text
    ].filter(Boolean).join("\n");
  const parsed = parseSections(rawCombined || "");
  const getSection = (title: string, fallbackText: string) => {
    const body = parsed[title];
    if (body && body.length) {
      return body.join("\n");
    }
    return fallbackText;
  };

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
          {renderTextBlock(getSection("Локация", content?.event_location_text || fallback.event_location_text))}
          <div className={styles.mapContainer} ref={mapRef} />
          <button className={styles.secondaryBtn} onClick={() => openLink(locationLink)}>Открыть маршрут</button>
        </GlassCard>

        <GlassCard title="Тайминг">
          {timing.length ? (
            <TimingBlock items={timing} />
          ) : timingError ? (
            <div className={styles.text}>Не удалось загрузить расписание.</div>
          ) : (
            <div className={styles.text}>Расписание уточняется.</div>
          )}
        </GlassCard>

        <GlassCard title="Дресс-код">
          {renderTextBlock(getSection("Дресс-код", content?.dresscode_text || fallback.dresscode_text))}
          <div className={styles.dressGradientBar} />
        </GlassCard>

        <GlassCard title="Контакты">
          {renderTextBlock(getSection("Контакты", content?.contacts_text || fallback.contacts_text))}
          <button className={styles.secondaryBtn} onClick={() => copyText(contactPhone)}>Скопировать</button>
        </GlassCard>

        <GlassCard title="Подарки">
          {renderTextBlock(getSection("Подарки", content?.gifts_text || fallback.gifts_text))}
        </GlassCard>
        <GlassCard title="Вопросы">
          {renderTextBlock(getSection("Вопросы", content?.faq_text || fallback.faq_text))}
        </GlassCard>
        <button className={styles.askBtn} onClick={() => setAskOpen(true)}>Задать вопрос</button>

        <GlassCard title="Как добавить партнёра">
          {renderTextBlock(getSection("Как добавить партнёра", content?.how_to_add_partner_text || fallback.how_to_add_partner_text))}
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
