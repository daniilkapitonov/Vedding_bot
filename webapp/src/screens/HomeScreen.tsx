import React, { useEffect, useMemo, useReducer, useState } from "react";
import styles from "./HomeScreen.module.css";
import { GlassCard } from "../components/GlassCard";
import { FrostedHeader } from "../components/FrostedHeader";
import { SegmentedControl, SegValue } from "../components/SegmentedControl";
import { FormField } from "../components/FormField";
import { ChipsMultiSelect } from "../components/ChipsMultiSelect";
import { BottomBar } from "../components/bottombar";
import { daysUntil } from "../utils/date";
import { ModalSheet } from "../components/ModalSheet";
import { api, tgInitData, TempProfile, getInviteToken } from "../api";
import coupleImage from "../assets/married-people.png";
import { Toast } from "../components/Toast";
import { getTelegramUser } from "../utils/telegram";

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
  "Вода",
  "Коньяк",
  "Не пью",
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

function getLocalId(): number {
  const key = "wedding.telegram_id";
  const raw = localStorage.getItem(key);
  if (raw) return Number(raw);
  const generated = 100000 + Math.floor(Math.random() * 900000);
  localStorage.setItem(key, String(generated));
  return generated;
}

function saveLocalProfile(data: TempProfile) {
  localStorage.setItem("wedding.profile", JSON.stringify(data));
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

  const days = useMemo(() => daysUntil(WEDDING_ISO), []);
  const rsvpStatus =
    state.rsvp === "yes"
      ? "Вы указали, что придёте"
      : state.rsvp === "no"
        ? "Вы указали, что не сможете присутствовать"
        : "Вы указали, что пока не уверены";

  useEffect(() => {
    const tgUser = getTelegramUser();
    if (tgUser?.id) {
      localStorage.setItem("wedding.telegram_id", String(tgUser.id));
    }
    const local = loadLocalProfile();
    if (local) {
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
        alcohol: local.alcohol || []
      }});
    }
    const initData = tgInitData();
    const inviteToken = getInviteToken();
    if (initData || inviteToken) {
      api.auth().then(() => api.getProfile()).then((remote: any) => {
        if (!remote) return;
        dispatch({ type: "hydrate", value: {
          rsvp: remote.rsvp_status || "yes",
          fullName: remote.full_name || "",
          birthDate: remote.birth_date || "",
          gender: remote.gender || "",
          phone: remote.phone || "",
          side: remote.side || "",
          relative: Boolean(remote.is_relative),
          food: remote.food_pref || "",
          allergies: remote.food_allergies || "",
          alcohol: remote.alcohol_prefs || []
        }});
      }).catch(() => {});
    }

    if (tgUser && !local?.fullName && !local?.full_name) {
      const name = [tgUser.first_name, tgUser.last_name].filter(Boolean).join(" ").trim();
      if (name) {
        dispatch({ type: "hydrate", value: { fullName: name } });
      }
    }
  }, []);

  function confirmRsvpChange(next: SegValue) {
    if (next === state.rsvp) return;
    setPendingRsvp(next);
    setConfirmOpen(true);
  }

  function buildProfilePayload(nextRsvp?: SegValue) {
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
      alcohol_prefs: state.alcohol || []
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
      setToast(msg.includes("NO_INITDATA") ? "Откройте через Telegram" : "Не удалось сохранить");
    } finally {
      setTimeout(() => setToast(""), 2000);
    }
  }

  function applyRsvp(next: SegValue) {
    const existing = loadLocalProfile();
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
    if (next === "no") {
      setExpanded(false);
    }
    saveLocalProfile(updated);
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

        <GlassCard title="Сможете присутствовать?">
          <SegmentedControl
            value={state.rsvp}
            onChange={(value) => confirmRsvpChange(value)}
          />
          <div className={styles.rsvpStatus}>{rsvpStatus}</div>
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
                onChange={(e) => dispatch({ type: "field", key: "fullName", value: e.target.value })}
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
                  onChange={(e) => handlePhoneChange(e.target.value)}
                />
              </FormField>
            ) : (
              <>
                <FormField label="Дата рождения">
                  <input
                    className={styles.input}
                    type="date"
                    value={state.birthDate}
                    onChange={(e) => dispatch({ type: "field", key: "birthDate", value: e.target.value })}
                  />
                </FormField>
                <FormField label="Пол">
                  <select
                    className={styles.input}
                    value={state.gender}
                    onChange={(e) => dispatch({ type: "field", key: "gender", value: e.target.value })}
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
                      onChange={(e) => handlePhoneChange(e.target.value)}
                    />
                  </FormField>
                  <FormField label="С чьей стороны">
                    <select
                      className={styles.input}
                      value={state.side}
                      onChange={(e) => dispatch({ type: "field", key: "side", value: e.target.value })}
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
                      onChange={() => dispatch({ type: "toggle", key: "relative" })}
                    />
                    <span>Родственник</span>
                  </div>
                  <FormField label="Еда">
                    <select
                      className={styles.input}
                      value={state.food}
                      onChange={(e) => dispatch({ type: "field", key: "food", value: e.target.value })}
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
                      onChange={(e) => dispatch({ type: "field", key: "allergies", value: e.target.value })}
                    />
                  </FormField>
                  <div className={styles.subSection}>
                    <div className={styles.subTitle}>Алкоголь (можно несколько)</div>
                    <ChipsMultiSelect
                      options={alcoholOptions}
                      value={state.alcohol}
                      exclusiveLabel="Не пью"
                      onChange={(next) => dispatch({ type: "alcohol", value: next })}
                    />
                  </div>
                </div>
              </div>
            </>
          )}
        </GlassCard>
      </main>

      <div className={styles.stickyAction}>
        <button
          className={styles.saveButton}
          disabled={saving}
          onClick={() => {
            setSaving(true);
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
              saveLocalProfile(payload);
              saveProfileToBackend(buildProfilePayload(), "Анкета сохранена");
            } finally {
              setTimeout(() => setSaving(false), 300);
            }
          }}
        >
          {saving ? "Сохраняю..." : "Сохранить анкету"}
        </button>
      </div>
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

      <BottomBar
        primaryLabel="Моя анкета"
        secondaryLabel="Информация о мероприятии"
        onPrimary={() => props.onNavigate("home")}
        onSecondary={() => props.onNavigate("event")}
      />
    </div>
  );
}
