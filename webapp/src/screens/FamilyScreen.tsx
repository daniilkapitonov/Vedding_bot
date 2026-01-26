import React, { useEffect, useReducer, useState } from "react";
import styles from "./FamilyScreen.module.css";
import { FrostedHeader } from "../components/FrostedHeader";
import { GlassCard } from "../components/GlassCard";
import { BottomBar } from "../components/bottombar";
import { FamilyPayload, inviteFamily, loadFamily, saveFamily, familyStatus, checkFamilyUsername } from "../api";
import { Toast } from "../components/Toast";
import { getTelegramUserId } from "../utils/telegram";

type Child = { id: string; name: string; age: string; note: string };

type State = {
  withPartner: boolean;
  partnerUsername: string;
  children: Child[];
};

type Action =
  | { type: "toggle" }
  | { type: "partner"; key: "partnerUsername"; value: string }
  | { type: "addChild" }
  | { type: "removeChild"; id: string }
  | { type: "child"; id: string; key: keyof Child; value: string }
  | { type: "hydrate"; value: Partial<State> };

const initialState: State = {
  withPartner: false,
  partnerUsername: "",
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
  const [members, setMembers] = useState<Array<{ name: string; rsvp: string }>>([]);
  const normalizeUsername = (value: string) => {
    let v = (value || "").trim();
    if (!v) return "";
    v = v.replace(/^https?:\/\/t\.me\//i, "");
    v = v.replace(/^t\.me\//i, "");
    v = v.replace(/^@/g, "");
    return v.toLowerCase();
  };

  function familyStorageKey(userId: number | null) {
    return userId ? `wedding.family.${userId}` : "wedding.family.guest";
  }

  function saveLocalFamily(userId: number | null, data: FamilyPayload) {
    localStorage.setItem(familyStorageKey(userId), JSON.stringify(data));
  }

  function loadLocalFamily(userId: number | null): FamilyPayload | null {
    const raw = localStorage.getItem(familyStorageKey(userId));
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
    const local = loadLocalFamily(getTelegramUserId());
    if (local) {
      dispatch({ type: "hydrate", value: {
        withPartner: Boolean(local.withPartner),
        partnerUsername: (local as any).partnerUsername || local.partnerName || "",
        children: local.children || []
      }});
    }
    const localInvite = loadLocalInvite();
    if (localInvite) setInvite(localInvite);
    loadFamily().then((res: any) => {
      if (res) {
        dispatch({ type: "hydrate", value: {
          withPartner: Boolean(res.withPartner),
          partnerUsername: res.partnerName || "",
          children: res.children || []
        }});
      }
    }).catch(() => {});

    familyStatus().then((res: any) => {
      if (res?.members?.length) setMembers(res.members);
    }).catch(() => {});
  }, []);

  const rsvpLabel = (value: string) => {
    if (value === "yes") return "Приду";
    if (value === "no") return "Не приду";
    if (value === "maybe") return "Не знаю";
    return "—";
  };

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
              {members.length > 1 ? (
                <>
                  <div className={styles.familyNote}>
                    Вы вместе: {members.map((m) => m.name).join(", ")}
                  </div>
                  <div className={styles.familyList}>
                    {members.map((m) => (
                      <div key={m.name} className={styles.familyRow}>
                        <span>{m.name}</span>
                        <span className={styles.familyRsvp}>{rsvpLabel(m.rsvp)}</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : null}
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
                placeholder="Ник Telegram (например, @username)"
                value={state.partnerUsername}
                onChange={(e) => dispatch({ type: "partner", key: "partnerUsername", value: e.target.value })}
              />
              <div className={styles.inviteRow}>
                <button
                  className={styles.checkBtn}
                  disabled={!state.partnerUsername}
                  onClick={() => {
                    const username = normalizeUsername(state.partnerUsername);
                    if (!username) {
                      setToastVariant("error");
                      setToast("Введите ник Telegram");
                      setTimeout(() => setToast(""), 2200);
                      return;
                    }
                    checkFamilyUsername(username)
                      .then((res: any) => {
                        if (!res?.found) {
                          setToastVariant("error");
                          setToast("Пользователь не найден");
                          setTimeout(() => setToast(""), 2200);
                          return;
                        }
                        const name = res?.name ? `Найден: ${res.name}` : "Пользователь найден";
                        setToastVariant("ok");
                        setToast(name);
                        setTimeout(() => setToast(""), 2000);
                      })
                      .catch((err: any) => {
                        const msg = String(err?.message || "");
                        if (msg.includes("Multiple")) {
                          setToastVariant("error");
                          setToast("Найдено несколько пользователей");
                        } else {
                          setToastVariant("error");
                          setToast("Не удалось проверить");
                        }
                        setTimeout(() => setToast(""), 2200);
                      });
                  }}
                >
                  Проверить
                </button>
                <button
                  className={styles.inviteBtn}
                  disabled={!state.partnerUsername}
                  onClick={() => {
                    const username = normalizeUsername(state.partnerUsername);
                    if (!username) {
                      setToastVariant("error");
                      setToast("Введите ник Telegram");
                      setTimeout(() => setToast(""), 2200);
                      return;
                    }
                    inviteFamily(username)
                      .then((res: any) => {
                        if (!res?.ok) {
                          setToastVariant("error");
                          setToast("Пользователь не найден");
                          setTimeout(() => setToast(""), 2200);
                          return;
                        }
                        setInvite({ status: "sent", confirmed: false });
                        setToastVariant("ok");
                        setToast("Приглашение отправлено");
                        setTimeout(() => setToast(""), 2000);
                      })
                      .catch((err: any) => {
                        const msg = String(err?.message || "");
                        if (msg.includes("User not found")) {
                          setToastVariant("error");
                          setToast("Пользователь не найден");
                        } else if (msg.includes("Multiple")) {
                          setToastVariant("error");
                          setToast("Найдено несколько пользователей");
                        } else {
                          setToastVariant("error");
                          setToast("Не удалось отправить приглашение");
                        }
                        setTimeout(() => setToast(""), 2200);
                      });
                  }}
                >
                  Отправить приглашение
                </button>
              </div>
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
            const payload: FamilyPayload = {
              withPartner: state.withPartner,
              partnerName: state.partnerUsername,
              partnerConfirmed: Boolean(invite?.confirmed),
              children: state.children,
            };
            saveLocalFamily(getTelegramUserId(), payload);
            saveFamily(payload)
              .then(() => {
                setToastVariant("ok");
                setToast("Сохранено");
                setTimeout(() => setToast(""), 2000);
              })
              .catch((err: any) => {
                const msg = String(err?.message || "");
                setToastVariant("error");
                setToast(msg || "Не удалось сохранить");
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
