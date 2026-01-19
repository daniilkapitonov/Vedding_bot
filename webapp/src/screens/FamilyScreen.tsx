import React, { useEffect, useReducer, useState } from "react";
import styles from "./FamilyScreen.module.css";
import { FrostedHeader } from "../components/FrostedHeader";
import { GlassCard } from "../components/GlassCard";
import { BottomBar } from "../components/bottombar";
import { FamilyPayload, inviteFamily, loadFamily, saveFamily } from "../api";
import { Toast } from "../components/Toast";

type Child = { id: string; name: string; age: string; note: string };

type State = {
  withPartner: boolean;
  partnerName: string;
  children: Child[];
};

type Action =
  | { type: "toggle" }
  | { type: "partner"; key: "partnerName"; value: string }
  | { type: "addChild" }
  | { type: "removeChild"; id: string }
  | { type: "child"; id: string; key: keyof Child; value: string }
  | { type: "hydrate"; value: Partial<State> };

const initialState: State = {
  withPartner: false,
  partnerName: "",
  children: [],
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "toggle":
      return { ...state, withPartner: !state.withPartner };
    case "partner":
      return { ...state, [action.key]: action.value };
    case "addChild":
      return {
        ...state,
        children: [...state.children, { id: String(Date.now()), name: "", age: "", note: "" }],
      };
    case "removeChild":
      return { ...state, children: state.children.filter((c) => c.id !== action.id) };
    case "child":
      return {
        ...state,
        children: state.children.map((c) =>
          c.id === action.id ? { ...c, [action.key]: action.value } : c
        ),
      };
    case "hydrate":
      return { ...state, ...action.value };
    default:
      return state;
  }
}

export function FamilyScreen(props: { onBack: () => void; onMenu: (rect: DOMRect) => void; onEvent: () => void }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [invite, setInvite] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");
  const [toastVariant, setToastVariant] = useState<"ok" | "error">("ok");

  function getLocalId(): number {
    const key = "wedding.telegram_id";
    const raw = localStorage.getItem(key);
    if (raw) return Number(raw);
    const generated = 100000 + Math.floor(Math.random() * 900000);
    localStorage.setItem(key, String(generated));
    return generated;
  }

  function saveLocalFamily(data: FamilyPayload) {
    localStorage.setItem("wedding.family", JSON.stringify(data));
  }

  function loadLocalFamily(): FamilyPayload | null {
    const raw = localStorage.getItem("wedding.family");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function saveLocalInvite(data: any) {
    localStorage.setItem("wedding.familyInvite", JSON.stringify(data));
  }

  function loadLocalInvite(): any | null {
    const raw = localStorage.getItem("wedding.familyInvite");
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  useEffect(() => {
    const local = loadLocalFamily();
    if (local) {
      dispatch({ type: "hydrate", value: local });
    }
    const localInvite = loadLocalInvite();
    if (localInvite) setInvite(localInvite);
    const telegramId = getLocalId();
    loadFamily(telegramId).then((res: any) => {
      if (res?.data) dispatch({ type: "hydrate", value: res.data });
      if (res?.invite) setInvite(res.invite);
    }).catch(() => {});
  }, []);

  return (
    <div className={styles.page}>
      <FrostedHeader title="Семья" leftIcon="←" rightIcon="…" onLeft={props.onBack} onRight={props.onMenu} />
      <main className={styles.content}>
        <GlassCard title="Кого вы приведёте?">
          <label className={styles.toggle}>
            <input type="checkbox" checked={state.withPartner} onChange={() => dispatch({ type: "toggle" })} />
            <span>Буду с парой</span>
          </label>
          {state.withPartner ? (
            <div className={styles.grid}>
              <div className={styles.partnerHeader}>
                <div className={styles.partnerTitle}>Партнёр</div>
                {invite?.confirmed ? (
                  <span className={`${styles.badge} ${styles.badgeOk}`}>Подтверждено</span>
                ) : invite?.status === "sent" ? (
                  <span className={`${styles.badge} ${styles.badgePending}`}>Ожидаем подтверждение</span>
                ) : null}
              </div>
              <input
                className={styles.input}
                placeholder="ФИО партнёра"
                value={state.partnerName}
                onChange={(e) => dispatch({ type: "partner", key: "partnerName", value: e.target.value })}
              />
              <button
                className={styles.inviteBtn}
                disabled={!state.partnerName}
                onClick={() => {
                  const name = state.partnerName.trim();
                  if (!name) {
                    setToastVariant("error");
                    setToast("Введите ФИО партнёра");
                    setTimeout(() => setToast(""), 2200);
                    return;
                  }
                  const telegramId = getLocalId();
                  inviteFamily(telegramId, name)
                    .then((res: any) => {
                      if (!res?.ok) {
                        setToastVariant("error");
                        setToast("Такого гостя нет в списке");
                        setTimeout(() => setToast(""), 2200);
                        return;
                      }
                      setInvite(res.invite);
                      saveLocalInvite(res.invite);
                      setToastVariant("ok");
                      setToast("Приглашение отправлено");
                      setTimeout(() => setToast(""), 2000);
                    })
                    .catch(() => {
                      setToastVariant("error");
                      setToast("Не удалось отправить приглашение");
                      setTimeout(() => setToast(""), 2200);
                    });
                }}
              >
                Отправить приглашение
              </button>
            </div>
          ) : null}
        </GlassCard>

        <GlassCard title="Дети">
          <button className={styles.addBtn} onClick={() => dispatch({ type: "addChild" })}>Добавить ребёнка</button>
          <div className={styles.childrenList}>
            {state.children.map((child) => (
              <div key={child.id} className={styles.childRow}>
                <div className={styles.childHeader}>
                  <div className={styles.childTitle}>Ребёнок</div>
                  <button
                    className={styles.removeBtn}
                    onClick={() => dispatch({ type: "removeChild", id: child.id })}
                  >
                    Удалить
                  </button>
                </div>
                <input
                  className={styles.input}
                  placeholder="Имя"
                  value={child.name}
                  onChange={(e) => dispatch({ type: "child", id: child.id, key: "name", value: e.target.value })}
                />
                <input
                  className={styles.input}
                  placeholder="Возраст"
                  value={child.age}
                  onChange={(e) => dispatch({ type: "child", id: child.id, key: "age", value: e.target.value })}
                />
                <input
                  className={styles.input}
                  placeholder="Примечание"
                  value={child.note}
                  onChange={(e) => dispatch({ type: "child", id: child.id, key: "note", value: e.target.value })}
                />
              </div>
            ))}
          </div>
        </GlassCard>

        <button
          className={styles.saveBtn}
          disabled={saving}
          onClick={() => {
            setSaving(true);
            const telegramId = getLocalId();
            const payload: FamilyPayload = {
              withPartner: state.withPartner,
              partnerName: state.partnerName,
              partnerConfirmed: Boolean(invite?.confirmed),
              children: state.children,
            };
            saveLocalFamily(payload);
            saveFamily(telegramId, payload)
              .then(() => {
                setToastVariant("ok");
                setToast("Сохранено");
                setTimeout(() => setToast(""), 2000);
              })
              .catch(() => {
                setToastVariant("error");
                setToast("Не удалось сохранить");
                setTimeout(() => setToast(""), 2200);
              })
              .finally(() => setSaving(false));
          }}
        >
          {saving ? "Сохраняю..." : "Сохранить"}
        </button>
      </main>
      <Toast message={toast} variant={toastVariant} />
      <BottomBar
        primaryLabel="Моя анкета"
        secondaryLabel="Информация о мероприятии"
        onPrimary={props.onBack}
        onSecondary={props.onEvent}
      />
    </div>
  );
}
