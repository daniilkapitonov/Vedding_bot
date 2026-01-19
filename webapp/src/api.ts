export function tgInitData(): string {
  // @ts-ignore
  const w = window?.Telegram?.WebApp;
  return w?.initData || "";
}

const API_BASE =
  (import.meta as any).env?.VITE_API_URL ||
  "http://localhost:8000";

async function req(path: string, method: string, body?: any) {
  const initData = tgInitData();
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "x-tg-initdata": initData
    },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const api = {
  auth: async (initData: string) => {
    const res = await fetch(`${API_BASE}/api/auth/telegram`, {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({ initData })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getProfile: () => req("/api/profile", "GET"),
  saveProfile: (payload: any) => req("/api/profile", "POST", payload),
  saveExtra: (payload: any) => req("/api/extra", "POST", payload),
  linkPartner: (payload: any) => req("/api/partner/link", "POST", payload),
  eventInfo: () => fetch(`${API_BASE}/api/event`).then(r=>r.json())
};

export type TempProfile = {
  rsvp: "yes" | "no" | "maybe";
  fullName?: string;
  full_name?: string;
  birthDate?: string;
  gender?: string;
  phone?: string;
  side?: string;
  relative?: boolean;
  food?: string;
  allergies?: string;
  alcohol?: string[];
};

export type FamilyPayload = {
  withPartner: boolean;
  partnerName?: string;
  partnerConfirmed?: boolean;
  children: Array<{ id: string; name: string; age: string; note: string }>;
};

export async function saveTempProfile(telegramId: number, data: TempProfile) {
  const res = await fetch(`${API_BASE}/profile/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telegram_id: telegramId, data })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function loadTempProfile(telegramId: number): Promise<TempProfile | null> {
  const res = await fetch(`${API_BASE}/profile/${telegramId}`);
  if (!res.ok) return null;
  const json = await res.json();
  return json?.data || null;
}

export async function saveFamily(telegramId: number, data: FamilyPayload) {
  const res = await fetch(`${API_BASE}/family/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telegram_id: telegramId, data })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function loadFamily(telegramId: number) {
  const res = await fetch(`${API_BASE}/family/${telegramId}`);
  if (!res.ok) return null;
  return res.json();
}

export async function inviteFamily(telegramId: number, fullName: string) {
  const res = await fetch(`${API_BASE}/family/invite`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ telegram_id: telegramId, full_name: fullName })
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
