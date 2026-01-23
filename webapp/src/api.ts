export function tgInitData(): string {
  // @ts-ignore
  const w = window?.Telegram?.WebApp;
  return w?.initData || "";
}

export function getInviteToken(): string {
  try {
    const params = new URLSearchParams(window.location.search);
    return params.get("invite") || "";
  } catch {
    return "";
  }
}

const rawBase = (import.meta as any).env?.VITE_API_URL || "";
const API_BASE = rawBase.endsWith("/") ? rawBase.slice(0, -1) : rawBase;

async function parseError(res: Response): Promise<string> {
  try {
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      const data = await res.json();
      const detail = (data as any)?.detail;
      if (Array.isArray(detail)) {
        const lines = detail.map((d) => {
          const path = Array.isArray(d.loc) ? d.loc.slice(1).join(".") : "";
          return path ? `${path}: ${d.msg}` : d.msg;
        });
        return lines.join(", ");
      }
      if (typeof detail === "string") return detail;
      if (typeof (data as any)?.message === "string") return (data as any).message;
    }
    const text = await res.text();
    return text || "Request failed";
  } catch {
    return "Request failed";
  }
}

async function req(path: string, method: string, body?: any) {
  const initData = tgInitData();
  const inviteToken = initData ? "" : getInviteToken();
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "x-tg-initdata": initData,
      ...(inviteToken ? { "x-invite-token": inviteToken } : {})
    },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!res.ok) throw new Error(await parseError(res));
  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return res.json();
  }
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  auth: async (initData?: string) => {
    const resolvedInitData = initData || tgInitData();
    const inviteToken = resolvedInitData ? "" : getInviteToken();
    const res = await fetch(`${API_BASE}/api/auth/telegram`, {
      method: "POST",
      headers: {
        "Content-Type":"application/json",
        "x-tg-initdata": resolvedInitData,
        ...(inviteToken ? { "x-invite-token": inviteToken } : {})
      },
      body: JSON.stringify({ initData: resolvedInitData })
    });
    if (!res.ok) throw new Error(await parseError(res));
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return res.json();
    }
    const text = await res.text();
    return text ? JSON.parse(text) : null;
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

export async function saveFamily(data: FamilyPayload) {
  return req("/api/family/save", "POST", {
    with_partner: data.withPartner,
    partner_name: data.partnerName || null,
    children: data.children || []
  });
}

export async function loadFamily() {
  const res = await req("/api/family/me", "GET");
  return {
    withPartner: Boolean(res?.with_partner),
    partnerName: res?.partner_name || "",
    children: res?.children || []
  } as FamilyPayload;
}

export async function inviteFamily(fullName: string) {
  return req("/api/family/invite-by-name", "POST", { full_name: fullName });
}

export async function familyStatus() {
  return req("/api/family/status", "GET");
}

export async function sendQuestion(text: string) {
  return req("/api/questions", "POST", { text });
}
