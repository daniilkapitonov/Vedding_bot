import React, { useEffect, useMemo, useReducer, useState, useRef } from "react";
import styles from "./HomeScreen.module.css";
import { GlassCard } from "../components/GlassCard";
import { FrostedHeader } from "../components/FrostedHeader";
import { SegmentedControl, SegValue } from "../components/SegmentedControl";
import { FormField } from "../components/FormField";
import { ChipsMultiSelect } from "../components/ChipsMultiSelect";
import { BottomBar } from "../components/bottombar";
import { daysUntil } from "../utils/date";
import { ModalSheet } from "../components/ModalSheet";
import { api, tgInitData, TempProfile, getInviteToken, markWelcomeSeen } from "../api";
import coupleImage from "../assets/married-people-v2.png";
import { Toast } from "../components/Toast";
import { getTelegramUser, getTelegramUserId } from "../utils/telegram";
import { isKeyboardOpen, subscribeKeyboardOpen } from "../utils/keyboard";

const WEDDING_ISO = "2026-07-25T16:00:00+03:00";

type State = {
  rsvp: SegValue;
  fullName: string;
  birthDate: string;
  gender: string;
  phone: string;
  side: string;
  relative: boolean;
  food: string;
  allergies: string;
  alcohol: string[];
};

type Action =
  | { type: "rsvp"; value: SegValue }
  | { type: "field"; key: keyof State; value: string }
  | { type: "toggle"; key: "relative" }
  | { type: "alcohol"; value: string[] }
  | { type: "hydrate"; value: Partial<State> };

const initialState: State = {
  rsvp: "yes",
  fullName: "",
  birthDate: "",
  gender: "",
  phone: "",
  side: "",
  relative: false,
  food: "",
  allergies: "",
  alcohol: [],
};

const alcoholOptions = [
  "Вино красное",
  "Вино белое",
  "Шампанское",
  "Коньяк",
  "Не пью алкоголь",
];

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "rsvp":
      return { ...state, rsvp: action.value };
    case "field":
      return { ...state, [action.key]: action.value };
    case "toggle":
      return { ...state, relative: !state.relative };
    case "alcohol":
      return { ...state, alcohol: action.value };
    case "hydrate":
      return { ...state, ...action.value };
    default:
      return state;
  }
}

function profileStorageKey(userId: number | null) {
  return userId ? `wedding.profile.${userId}` : "wedding.profile.guest";
}

function saveLocalProfile(userId: number | null, data: TempProfile) {
  localStorage.setItem(profileStorageKey(userId), JSON.stringify(data));
}

function loadLocalProfile(userId: number | null): TempProfile | null {
  const raw = localStorage.getItem(profileStorageKey(userId));
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function HomeScreen(props: {
  onNavigate: (route: string) => void;
  onMenu: (rect: DOMRect) => void;
  onAbout: () => void;
}) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [expanded, setExpanded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [toastVariant, setToastVariant] = useState<"ok" | "error">("ok");
  const [pendingRsvp, setPendingRsvp] = useState<SegValue | null>(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const dirtyRef = useRef(false);
  const [rsvpTouched, setRsvpTouched] = useState(false);
  const [showFirstTime, setShowFirstTime] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [welcomeEnabled, setWelcomeEnabled] = useState(true);
  const [forceWelcome, setForceWelcome] = useState(false);
  const [kbOpen, setKbOpen] = useState(isKeyboardOpen());
  const forceWelcomeRef = useRef(false);

  const days = useMemo(() => daysUntil(WEDDING_ISO), []);
  const rsvpStatus =
    state.rsvp === "yes"
      ? "Вы указали, что придёте"
      : state.rsvp === "no"
        ? "Вы указали, что не сможете присутствовать"
        : "Вы указали, что пока не уверены";
  const rsvpWarm =
    state.rsvp === "yes"
      ? "Очень рады, что вы будете с нами 💚"
      : state.rsvp === "no"
        ? "Спасибо, что сообщили. Мы всё понимаем."
        : "Ничего страшного — можно изменить решение позже.";

  useEffect(() => {
    const tgUser = getTelegramUser();
    const tgUserId = getTelegramUserId();
    const local = loadLocalProfile(tgUserId);
    if (local) {
      const alcohol = (local.alcohol || []).map((v) => v === "Не пью" ? "Не пью алкоголь" : v);
      dispatch({ type: "hydrate", value: {
        rsvp: local.rsvp || "yes",
        fullName: local.fullName || local.full_name || "",
        birthDate: local.birthDate || "",
        gender: local.gender || "",
        phone: local.phone || "",
        side: local.side || "",
        relative: Boolean(local.relative),
        food: local.food || "",
        allergies: local.allergies || "",
        alcohol
      }});
      if (local.rsvp === "yes" || local.rsvp === "no" || local.rsvp === "maybe") {
        setRsvpTouched(true);
        setShowFirstTime(false);
      }
    }
    try {
      const cached = localStorage.getItem("wedding.uiSettings");
      if (cached) {
        const data = JSON.parse(cached);
        setWelcomeEnabled(data?.welcome_tooltip_enabled !== false);
      }
    } catch {}
    const initData = tgInitData();
    const inviteToken = getInviteToken();
    if (initData || inviteToken) {
      (async () => {
        try {
          const existsRes: any = await api.profileExists();
          const exists = Boolean(existsRes?.exists);
          forceWelcomeRef.current = !exists;
          setForceWelcome(!exists);
          if (!exists) {
            setShowWelcome(true);
          }
        } catch {}
        try {
          await api.auth();
          const remote: any = await api.getProfile();
          if (!remote) return;
          if (dirtyRef.current) return;
          const alcohol = (remote.alcohol_prefs || []).map((v: string) =>
            v === "Не пью" ? "Не пью алкоголь" : v
          );
          const remoteRsvp = remote.rsvp_status || "";
          if (remoteRsvp === "yes" || remoteRsvp === "no" || remoteRsvp === "maybe") {
            setRsvpTouched(true);
            setShowFirstTime(false);
          } else {
            setShowFirstTime(true);
          }
          const seenKey = `wedding.welcomeSeen.${tgUserId || "guest"}`;
          const localSeen = localStorage.getItem(seenKey);
          if (forceWelcomeRef.current) {
            setShowWelcome(true);
          } else if (!remote.welcome_seen_at && !localSeen) {
            setShowWelcome(true);
          } else {
            setShowWelcome(false);
          }
          dispatch({ type: "hydrate", value: {
            rsvp: remoteRsvp || "yes",
            fullName: remote.full_name || "",
            birthDate: remote.birth_date || "",
            gender: remote.gender || "",
            phone: remote.phone || "",
            side: remote.side || "",
            relative: Boolean(remote.is_relative),
            food: remote.food_pref || "",
            allergies: remote.food_allergies || "",
            alcohol
          }});
        } catch {}
      })();
    }

    if (tgUser && !local?.fullName && !local?.full_name) {
      const name = [tgUser.first_name, tgUser.last_name].filter(Boolean).join(" ").trim();
      if (name) {
        if (!dirtyRef.current) dispatch({ type: "hydrate", value: { fullName: name } });
      }
    }
    if (!local) {
      setShowFirstTime(true);
      const seenKey = `wedding.welcomeSeen.${tgUserId || "guest"}`;
      if (!localStorage.getItem(seenKey)) {
        setShowWelcome(true);
      }
    }
  }, []);

  useEffect(() => {
    return subscribeKeyboardOpen(setKbOpen);
  }, []);

  function confirmRsvpChange(next: SegValue) {
    if (next === state.rsvp) return;
    setPendingRsvp(next);
    setConfirmOpen(true);
    setRsvpTouched(true);
  }

  function buildProfilePayload(nextRsvp?: SegValue) {
    const alcohol = (state.alcohol || []).map((v) => (v === "Не пью" ? "Не пью алкоголь" : v));
    return {
      rsvp_status: nextRsvp || state.rsvp,
      full_name: state.fullName || null,
      birth_date: state.birthDate || null,
      gender: state.gender || null,
      phone: state.phone || null,
      side: state.side || null,
      is_relative: state.relative,
      food_pref: state.food || null,
      food_allergies: state.allergies || null,
      alcohol_prefs: alcohol
    };
  }

  async function saveProfileToBackend(payload: any, successMsg: string) {
    try {
      const initData = tgInitData();
      const inviteToken = getInviteToken();
      if (!initData && !inviteToken) {
        throw new Error("NO_INITDATA");
      }
      await api.saveProfile(payload);
      setToastVariant("ok");
      setToast(successMsg);
    } catch (e: any) {
      const msg = String(e?.message || "");
      setToastVariant("error");
      setToast(msg.includes("NO_INITDATA") ? "Откройте через Telegram" : msg || "Не удалось сохранить");
    } finally {
      setTimeout(() => setToast(""), 2000);
    }
  }

  function applyRsvp(next: SegValue) {
    const tgUserId = getTelegramUserId();
    const existing = loadLocalProfile(tgUserId);
    const updated: TempProfile = {
      ...(existing || {}),
      rsvp: next,
      fullName: state.fullName,
      full_name: state.fullName,
      phone: state.phone
    };
    dispatch({ type: "rsvp", value: next });
    setConfirmOpen(false);
    setPendingRsvp(null);
    setShowFirstTime(false);
    if (next === "no") {
      setExpanded(false);
    }
    saveLocalProfile(tgUserId, updated);
    saveProfileToBackend(buildProfilePayload(next), "Статус сохранён");
  }

  function handlePhoneFocus() {
    if (!state.phone) dispatch({ type: "field", key: "phone", value: "+7" });
  }

  function handlePhoneChange(value: string) {
    const digits = value.replace(/[^\d]/g, "");
    const rest = digits.startsWith("7") ? digits.slice(1) : digits;
    const next = `+7${rest}`.slice(0, 12);
    dispatch({ type: "field", key: "phone", value: next });
  }

  function validateProfile(): string[] {
    const missing: string[] = [];
    if (!rsvpTouched) missing.push("Статус присутствия");
    if (!state.fullName.trim()) missing.push("ФИО");
    if (state.rsvp === "no" && !state.phone.trim()) missing.push("Телефон");
    return missing;
  }

  return (
    <div className={styles.page}>
      <FrostedHeader
        title={`До свадьбы — ${days} дней`}
        meta="25.07.2026"
        leftIcon="i"
        rightIcon="…"
        onLeft={props.onAbout}
        onRight={props.onMenu}
      />

      <main className={styles.content}>
        <GlassCard>
          <div className={styles.heroWrap}>
            <img className={styles.heroImage} src={coupleImage} alt="Wedding couple" />
          </div>
          <div className={styles.heroTitle}>Добро пожаловать на нашу свадьбу</div>
        </GlassCard>
        {showWelcome && welcomeEnabled ? (
          <GlassCard>
            <div className={styles.welcomeText}>
              Рады видеть вас здесь 💚 Заполните анкету — это займёт пару минут.
            </div>
            <button
              className={styles.welcomeBtn}
              onClick={() => {
                setShowWelcome(false);
                const seenKey = `wedding.welcomeSeen.${getTelegramUserId() || "guest"}`;
                localStorage.setItem(seenKey, "1");
                markWelcomeSeen().catch(() => {});
              }}
            >
              Понятно
            </button>
          </GlassCard>
        ) : null}

        <GlassCard title="Сможете присутствовать?">
          <SegmentedControl
            value={state.rsvp}
            onChange={(value) => confirmRsvpChange(value)}
          />
          <div className={styles.rsvpStatus}>{rsvpStatus}</div>
          <div className={styles.rsvpWarm}>{rsvpWarm}</div>
          {showFirstTime ? (
            <div className={styles.firstTimeBanner}>
              Вы не выбрали свой статус — отметьте, будете ли вы присутствовать на свадьбе.
            </div>
          ) : null}
          {state.rsvp === "no" ? (
            <div className={styles.rsvpHint}>Остальная информация не требуется.</div>
          ) : null}
        </GlassCard>

        <GlassCard title="Основная анкета">
          <div className={styles.formGrid}>
            <FormField label="ФИО">
              <input
                className={styles.input}
                value={state.fullName}
                onChange={(e) => {
                  dirtyRef.current = true;
                  dispatch({ type: "field", key: "fullName", value: e.target.value });
                }}
              />
            </FormField>
            {state.rsvp === "no" ? (
              <FormField label="Телефон">
                <input
                  className={styles.input}
                  inputMode="tel"
                  placeholder="+7 XXX XXX-XX-XX"
                  value={state.phone}
                  onFocus={handlePhoneFocus}
                  onChange={(e) => {
                    dirtyRef.current = true;
                    handlePhoneChange(e.target.value);
                  }}
                />
              </FormField>
            ) : (
              <>
                <FormField label="Дата рождения">
                  <input
                    className={styles.input}
                    type="date"
                    value={state.birthDate}
                    onChange={(e) => {
                      dirtyRef.current = true;
                      dispatch({ type: "field", key: "birthDate", value: e.target.value });
                    }}
                  />
                </FormField>
                <FormField label="Пол">
                  <select
                    className={styles.input}
                    value={state.gender}
                    onChange={(e) => {
                      dirtyRef.current = true;
                      dispatch({ type: "field", key: "gender", value: e.target.value });
                    }}
                  >
                    <option value="">Выбрать</option>
                <option value="Мужской">Мужской</option>
                <option value="Женский">Женский</option>
                <option value="Другое">Другое</option>
                  </select>
                </FormField>
              </>
            )}
          </div>

          {state.rsvp === "no" ? null : (
            <>
              <button
                className={styles.moreButton}
                onClick={() => setExpanded((v) => !v)}
              >
                {expanded ? "Свернуть" : "Продолжить заполнение"}
              </button>

              <div className={`${styles.expandArea} ${expanded ? styles.expandOpen : ""}`}>
                <div className={styles.expandInner}>
                  <FormField label="Телефон">
                    <input
                      className={styles.input}
                      inputMode="tel"
                      placeholder="+7 XXX XXX-XX-XX"
                      value={state.phone}
                      onFocus={handlePhoneFocus}
                      onChange={(e) => {
                        dirtyRef.current = true;
                        handlePhoneChange(e.target.value);
                      }}
                    />
                  </FormField>
                  <FormField label="С чьей стороны">
                    <select
                      className={styles.input}
                      value={state.side}
                      onChange={(e) => {
                        dirtyRef.current = true;
                        dispatch({ type: "field", key: "side", value: e.target.value });
                      }}
                    >
                      <option value="">Выбрать</option>
                      <option value="groom">Жених</option>
                      <option value="bride">Невеста</option>
                      <option value="both">Оба</option>
                    </select>
                  </FormField>
                  <div className={styles.inlineField}>
                    <input
                      className={styles.checkbox}
                      type="checkbox"
                      checked={state.relative}
                      onChange={() => {
                        dirtyRef.current = true;
                        dispatch({ type: "toggle", key: "relative" });
                      }}
                    />
                    <span>Родственник</span>
                  </div>
                  <FormField label="Еда">
                    <select
                      className={styles.input}
                      value={state.food}
                      onChange={(e) => {
                        dirtyRef.current = true;
                        dispatch({ type: "field", key: "food", value: e.target.value });
                      }}
                    >
                      <option value="">Выбрать</option>
                      <option value="Мясо">Мясо</option>
                      <option value="Рыба">Рыба</option>
                      <option value="Вегетарианское">Вегетарианское</option>
                      <option value="Веган">Веган</option>
                    </select>
                  </FormField>
                  <FormField label="Аллергии/ограничения">
                    <textarea
                      className={styles.textarea}
                      value={state.allergies}
                      onChange={(e) => {
                        dirtyRef.current = true;
                        dispatch({ type: "field", key: "allergies", value: e.target.value });
                      }}
                    />
                  </FormField>
                  <div className={styles.subSection}>
                    <div className={styles.subTitle}>Алкоголь (можно несколько)</div>
                    <ChipsMultiSelect
                      options={alcoholOptions}
                      value={state.alcohol}
                      exclusiveLabel="Не пью алкоголь"
                      onChange={(next) => {
                        dirtyRef.current = true;
                        dispatch({ type: "alcohol", value: next });
                      }}
                    />
                  </div>
                </div>
              </div>
            </>
          )}
        </GlassCard>
      </main>

      {kbOpen ? (
        <div className={styles.stickyActionInline}>
          <button
            className={styles.saveButton}
            disabled={saving}
            onClick={() => {
              const missing = validateProfile();
              if (missing.length) {
                setToastVariant("error");
                setToast(`Заполните: ${missing.join(", ")}`);
                setTimeout(() => setToast(""), 2200);
                return;
              }
              setShowFirstTime(false);
              setSaving(true);
              const tgUserId = getTelegramUserId();
              const payload: TempProfile = {
                rsvp: state.rsvp,
                fullName: state.fullName,
                full_name: state.fullName,
                birthDate: state.birthDate,
                gender: state.gender,
                phone: state.phone,
                side: state.side,
                relative: state.relative,
                food: state.food,
                allergies: state.allergies,
                alcohol: state.alcohol
              };
              try {
                saveLocalProfile(tgUserId, payload);
                saveProfileToBackend(buildProfilePayload(), "Анкета сохранена");
              } finally {
                setTimeout(() => setSaving(false), 300);
              }
            }}
          >
            {saving ? "Сохраняю..." : "Сохранить анкету"}
          </button>
          <BottomBar
            mode="inline"
            primaryLabel="Моя анкета"
            secondaryLabel="Информация о мероприятии"
            onPrimary={() => props.onNavigate("home")}
            onSecondary={() => props.onNavigate("event")}
          />
        </div>
      ) : (
        <>
          <div className={styles.stickyAction}>
            <button
              className={styles.saveButton}
              disabled={saving}
              onClick={() => {
                const missing = validateProfile();
                if (missing.length) {
                  setToastVariant("error");
                  setToast(`Заполните: ${missing.join(", ")}`);
                  setTimeout(() => setToast(""), 2200);
                  return;
                }
                setShowFirstTime(false);
                setSaving(true);
                const tgUserId = getTelegramUserId();
                const payload: TempProfile = {
                  rsvp: state.rsvp,
                  fullName: state.fullName,
                  full_name: state.fullName,
                  birthDate: state.birthDate,
                  gender: state.gender,
                  phone: state.phone,
                  side: state.side,
                  relative: state.relative,
                  food: state.food,
                  allergies: state.allergies,
                  alcohol: state.alcohol
                };
                try {
                  saveLocalProfile(tgUserId, payload);
                  saveProfileToBackend(buildProfilePayload(), "Анкета сохранена");
                } finally {
                  setTimeout(() => setSaving(false), 300);
                }
              }}
            >
              {saving ? "Сохраняю..." : "Сохранить анкету"}
            </button>
          </div>
          <BottomBar
            primaryLabel="Моя анкета"
            secondaryLabel="Информация о мероприятии"
            onPrimary={() => props.onNavigate("home")}
            onSecondary={() => props.onNavigate("event")}
          />
        </>
      )}
      <Toast message={toast} variant={toastVariant} />
      <ModalSheet
        open={confirmOpen}
        onClose={() => {
          setConfirmOpen(false);
          setPendingRsvp(null);
        }}
        title="Изменить ответ?"
      >
        <div className={styles.confirmText}>Мы обновим вашу анкету. Применить изменения?</div>
        <div className={styles.confirmActions}>
          <button
            className={styles.confirmPrimary}
            onClick={() => pendingRsvp && applyRsvp(pendingRsvp)}
          >
            {pendingRsvp === "yes"
              ? "Иду к вам!"
              : pendingRsvp === "no"
                ? "К сожалению, не пойду"
                : "Пока не знаю смогу или нет"}
          </button>
          <button
            className={styles.confirmSecondary}
            onClick={() => {
              setConfirmOpen(false);
              setPendingRsvp(null);
            }}
          >
            Отмена
          </button>
        </div>
      </ModalSheet>

    </div>
  );
}
