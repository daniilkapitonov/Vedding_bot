export type TelegramThemeParams = {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  button_color?: string;
  button_text_color?: string;
};

export type TelegramWebApp = {
  themeParams?: TelegramThemeParams;
  expand?: () => void;
  ready?: () => void;
  HapticFeedback?: { impactOccurred: (style: "light" | "medium" | "heavy") => void };
  initDataUnsafe?: { user?: TelegramUser };
  initData?: string;
  openLink?: (url: string) => void;
  openTelegramLink?: (url: string) => void;
};

export type TelegramUser = {
  id?: number;
  first_name?: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
};

export function getTelegramWebApp(): TelegramWebApp | null {
  const tg = (window as any)?.Telegram?.WebApp;
  return tg || null;
}

export function getTelegramUser(): TelegramUser | null {
  const tg = getTelegramWebApp();
  return tg?.initDataUnsafe?.user || null;
}

export function initTelegram() {
  const tg = getTelegramWebApp();
  try {
    tg?.ready?.();
    tg?.expand?.();
  } catch {
    // ignore
  }

  const theme = tg?.themeParams;
  if (theme) {
    const root = document.documentElement;
    if (theme.text_color) root.style.setProperty("--tg-text", theme.text_color);
    if (theme.hint_color) root.style.setProperty("--tg-hint", theme.hint_color);
    if (theme.bg_color) root.style.setProperty("--tg-bg", theme.bg_color);
  }
}

export function openLink(url: string) {
  const tg = getTelegramWebApp();
  try {
    tg?.openLink?.(url);
  } catch {
    window.open(url, "_blank");
  }
}

export function openTelegramLink(url: string) {
  const tg = getTelegramWebApp();
  try {
    tg?.openTelegramLink?.(url);
  } catch {
    openLink(url);
  }
}
