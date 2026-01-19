import React, { useEffect, useState } from "react";
import styles from "./ProfileScreen.module.css";
import { FrostedHeader } from "../components/FrostedHeader";
import { GlassCard } from "../components/GlassCard";
import { loadTempProfile, TempProfile } from "../api";
import { getTelegramUser } from "../utils/telegram";
import { BottomBar } from "../components/bottombar";

function getLocalId(): number {
  const key = "wedding.telegram_id";
  const raw = localStorage.getItem(key);
  if (raw) return Number(raw);
  const generated = 100000 + Math.floor(Math.random() * 900000);
  localStorage.setItem(key, String(generated));
  return generated;
}

function loadLocalProfile(): TempProfile | null {
  const raw = localStorage.getItem("wedding.profile");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function ProfileScreen(props: { onBack: () => void; onMenu: (rect: DOMRect) => void; onEvent: () => void }) {
  const [profile, setProfile] = useState<TempProfile | null>(null);
  const tgUser = getTelegramUser();

  useEffect(() => {
    const local = loadLocalProfile();
    if (local) setProfile(local);
    const telegramId = getLocalId();
    loadTempProfile(telegramId).then((remote) => {
      if (remote) setProfile(remote);
    }).catch(() => {});
  }, []);

  const isYes = profile?.rsvp === "yes";
  const isNo = profile?.rsvp === "no";
  const statusText = isNo ? "Жаль, что не получится" : profile?.rsvp === "maybe" ? "Пока не знаете" : "Вы с нами 💚";
  const name = profile?.fullName || profile?.full_name || "—";
  const sideMap: Record<string, string> = {
    groom: "Жених",
    bride: "Невеста",
    both: "Оба",
    Жених: "Жених",
    Невеста: "Невеста",
    Оба: "Оба",
  };
  const genderMap: Record<string, string> = {
    male: "Мужской",
    female: "Женский",
    other: "Другое",
    Мужской: "Мужской",
    Женский: "Женский",
    Другое: "Другое",
  };
  const foodMap: Record<string, string> = {
    meat: "Мясо",
    fish: "Рыба",
    veg: "Вегетарианское",
    vegetarian: "Вегетарианское",
    vegan: "Веган",
    Мясо: "Мясо",
    Рыба: "Рыба",
    Вегетарианское: "Вегетарианское",
    Веган: "Веган",
  };
  const sideLabel = profile?.side ? sideMap[profile.side] || "—" : "—";
  const genderLabel = profile?.gender ? genderMap[profile.gender] || "—" : "—";
  const foodLabel = profile?.food ? foodMap[profile.food] || "—" : "—";
  const photoUrl = tgUser?.photo_url || "";

  return (
    <div className={styles.page}>
      <FrostedHeader title="О себе" leftIcon="←" rightIcon="…" onLeft={props.onBack} onRight={props.onMenu} />
      <main className={styles.content}>
        <GlassCard title="Профиль">
          <div className={styles.avatarWrap}>
            {photoUrl ? (
              <img className={styles.avatarImg} src={photoUrl} alt="Avatar" />
            ) : (
              <div className={`${styles.avatar} ${isYes ? styles.avatarYes : isNo ? styles.avatarNo : styles.avatarMaybe}`}>
                <svg viewBox="0 0 24 24" className={styles.heartIcon}>
                  <path d="M12 20s-7-4.6-9.5-8.2C.8 8.8 2.3 5.6 5.4 5.2c1.9-.3 3.6.6 4.6 2 1-1.4 2.7-2.3 4.6-2 3.1.4 4.6 3.6 2.9 6.6C19 15.4 12 20 12 20z" />
                </svg>
              </div>
            )}
          </div>
          <div className={styles.line}><span>ФИО</span><strong>{name}</strong></div>
          <div className={styles.line}><span>Телефон</span><strong>{profile?.phone || "—"}</strong></div>
          <div className={styles.line}><span>Пол</span><strong>{genderLabel}</strong></div>
          <div className={styles.line}><span>Сторона</span><strong>{sideLabel}</strong></div>
          <div className={`${styles.status} ${isYes ? styles.statusYes : ""}`}>{statusText}</div>
        </GlassCard>

        <GlassCard title="Предпочтения">
          {isNo ? (
            <div className={styles.mutedNote}>Не требуется</div>
          ) : (
            <>
              <div className={styles.line}><span>Еда</span><strong>{foodLabel}</strong></div>
              <div className={styles.line}><span>Аллергии</span><strong>{profile?.allergies || "—"}</strong></div>
              <div className={styles.line}><span>Алкоголь</span><strong>{(profile?.alcohol || []).join(", ") || "—"}</strong></div>
            </>
          )}
        </GlassCard>
      </main>
      <BottomBar
        primaryLabel="Моя анкета"
        secondaryLabel="Информация о мероприятии"
        onPrimary={props.onBack}
        onSecondary={props.onEvent}
      />
    </div>
  );
}
