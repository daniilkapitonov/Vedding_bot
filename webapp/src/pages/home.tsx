import React, { useEffect, useMemo, useState } from "react";
import styles from "./home.module.css";

type RSVP = "yes" | "no" | null;

const WEDDING_ISO = "2026-07-25T16:00:00+03:00";

export default function Home() {
  const [rsvp, setRsvp] = useState<RSVP>("yes");
  const [showMenu, setShowMenu] = useState(false);
  const [showAbout, setShowAbout] = useState(false);

  useTelegramTheme();

  const daysLeft = useMemo(() => {
    const target = new Date(WEDDING_ISO);
    const now = new Date();
    const diff = target.getTime() - now.getTime();
    return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
  }, []);

  return (
    <div className={styles.page}>
      <FrostedHeader
        days={daysLeft}
        date="25.07.2026"
        onInfo={() => setShowAbout(true)}
        onMenu={() => setShowMenu(true)}
      />

      <main className={styles.content}>
        <Card className={styles.heroCard}>
          <div className={styles.heroImage}>
            <div className={styles.heroFrame}>
              <div className={styles.heroPlaceholder} />
            </div>
          </div>
        </Card>

        <div className={styles.welcome}>Добро пожаловать на нашу свадьбу</div>

        <Card className={styles.rsvpCard}>
          <div className={styles.cardTitleRow}>
            <CalendarIcon />
            <div className={styles.cardTitle}>
              <span className={styles.cardLabel}>Ваш ответ:</span>
              <span className={styles.cardValue}>{rsvp === "no" ? "Не приду" : "Приду"}</span>
            </div>
          </div>
          <div className={styles.rsvpButtons}>
            <PrimaryButton active={rsvp !== "no"} onClick={() => setRsvp("yes")}>
              Приду
            </PrimaryButton>
            <SecondaryButton active={rsvp === "no"} onClick={() => setRsvp("no")}>
              Не приду
            </SecondaryButton>
          </div>
        </Card>

        <Card className={styles.summaryCard}>
          <div className={styles.cardTitleRow}>
            <UserIcon />
            <div className={styles.cardTitle}>Мои данные</div>
          </div>
          <div className={styles.summaryLine}>Приглашено гостей: 2 человека</div>
          <div className={styles.summaryLineMuted}>Выбор меню: Обычное</div>
        </Card>
      </main>

      <BottomBar
        left={{ label: "Главная", active: true }}
        right={{ label: "О событии", active: false }}
      />

      <BottomSheet open={showMenu} onClose={() => setShowMenu(false)} title="Меню">
        <SheetButton>Доп. инфо</SheetButton>
        <SheetButton>Семья</SheetButton>
        <SheetButton>О себе</SheetButton>
      </BottomSheet>

      <Modal open={showAbout} onClose={() => setShowAbout(false)} title="О событии">
        <p className={styles.modalText}>
          Добро пожаловать на нашу свадьбу! Подробности и обновления будут появляться здесь.
        </p>
      </Modal>
    </div>
  );
}

function useTelegramTheme() {
  useEffect(() => {
    const tg = (window as any)?.Telegram?.WebApp;
    if (!tg?.themeParams) return;
    const root = document.documentElement;
    const tp = tg.themeParams;
    if (tp.bg_color) root.style.setProperty("--tg-bg", tp.bg_color);
    if (tp.text_color) root.style.setProperty("--tg-text", tp.text_color);
    if (tp.hint_color) root.style.setProperty("--tg-hint", tp.hint_color);
  }, []);
}

function FrostedHeader(props: {
  days: number;
  date: string;
  onInfo: () => void;
  onMenu: () => void;
}) {
  return (
    <header className={styles.header}>
      <button className={styles.iconButton} onClick={props.onInfo} aria-label="Info">
        i
      </button>
      <div className={styles.headerCenter}>
        <div className={styles.headerTitle}>До свадьбы — {props.days} дней</div>
        <div className={styles.headerSub}>25.07.2026</div>
      </div>
      <button className={styles.iconButton} onClick={props.onMenu} aria-label="Menu">
        …
      </button>
    </header>
  );
}

function Card(props: { children: React.ReactNode; className?: string }) {
  return <section className={`${styles.card} ${props.className || ""}`}>{props.children}</section>;
}

function PrimaryButton(props: { active?: boolean; onClick?: () => void; children: React.ReactNode }) {
  return (
    <button
      className={`${styles.primaryButton} ${props.active ? styles.isActive : ""}`}
      onClick={props.onClick}
    >
      {props.children}
    </button>
  );
}

function SecondaryButton(props: { active?: boolean; onClick?: () => void; children: React.ReactNode }) {
  return (
    <button
      className={`${styles.secondaryButton} ${props.active ? styles.isActiveAlt : ""}`}
      onClick={props.onClick}
    >
      {props.children}
    </button>
  );
}

function BottomBar(props: {
  left: { label: string; active: boolean };
  right: { label: string; active: boolean };
}) {
  return (
    <nav className={styles.bottomBar}>
      <button className={`${styles.bottomButton} ${props.left.active ? styles.bottomActive : ""}`}>
        {props.left.label}
      </button>
      <button className={`${styles.bottomButton} ${props.right.active ? styles.bottomActiveAlt : ""}`}>
        {props.right.label}
      </button>
    </nav>
  );
}

function BottomSheet(props: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!props.open) return null;
  return (
    <div className={styles.sheetOverlay} onClick={props.onClose}>
      <div className={styles.sheet} onClick={(e) => e.stopPropagation()}>
        <div className={styles.sheetTitle}>{props.title}</div>
        <div className={styles.sheetBody}>{props.children}</div>
      </div>
    </div>
  );
}

function SheetButton(props: { children: React.ReactNode }) {
  return <button className={styles.sheetButton}>{props.children}</button>;
}

function Modal(props: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  if (!props.open) return null;
  return (
    <div className={styles.modalOverlay} onClick={props.onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.modalTitle}>{props.title}</div>
        {props.children}
      </div>
    </div>
  );
}

function CalendarIcon() {
  return (
    <span className={styles.iconBadge} aria-hidden>
      <svg viewBox="0 0 24 24" className={styles.icon}>
        <rect x="3.5" y="5.5" width="17" height="15" rx="3" />
        <path d="M7 4v4M17 4v4M3.5 9.5h17" />
      </svg>
    </span>
  );
}

function UserIcon() {
  return (
    <span className={styles.iconBadge} aria-hidden>
      <svg viewBox="0 0 24 24" className={styles.icon}>
        <circle cx="9" cy="9" r="3.2" />
        <rect x="4" y="14" width="10" height="6" rx="3" />
        <circle cx="18" cy="10" r="2.2" />
        <rect x="15.5" y="14.5" width="5" height="5.5" rx="2.5" />
      </svg>
    </span>
  );
}
