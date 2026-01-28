import React, { useEffect, useState } from "react";
import { Router } from "./screens/Router";
import { initTelegram } from "./utils/telegram";
import { api, tgInitData, getInviteToken, getUiSettings } from "./api";

export default function App() {
  const [animEnabled, setAnimEnabled] = useState(true);
  useEffect(() => {
    initTelegram();
    try {
      const cached = localStorage.getItem("wedding.uiSettings");
      if (cached) {
        const data = JSON.parse(cached);
        const enabled = data?.ui_animations_enabled !== false;
        setAnimEnabled(enabled);
        document.documentElement.style.setProperty("--anim-ms", enabled ? "180ms" : "0ms");
      }
    } catch {}
    getUiSettings()
      .then((data: any) => {
        const enabled = data?.ui_animations_enabled !== false;
        setAnimEnabled(enabled);
        localStorage.setItem("wedding.uiSettings", JSON.stringify(data || {}));
        document.documentElement.style.setProperty("--anim-ms", enabled ? "180ms" : "0ms");
      })
      .catch(() => {});
    const initData = tgInitData();
    const inviteToken = getInviteToken();
    if (initData || inviteToken) {
      api.auth().catch(() => {});
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    let kbOpen = false;
    const w = window as any;
    const webapp = w?.Telegram?.WebApp;
    const vv = window.visualViewport;
    const update = () => {
      let open = false;
      if (vv) {
        const diff = window.innerHeight - vv.height;
        if (diff > 140) open = true;
      }
      if (webapp?.viewportHeight) {
        const diff = window.innerHeight - webapp.viewportHeight;
        if (diff > 140) open = true;
      }
      const el = document.activeElement as HTMLElement | null;
      if (el && ["INPUT", "TEXTAREA", "SELECT"].includes(el.tagName)) {
        open = true;
      }
      if (open !== kbOpen) {
        kbOpen = open;
        root.classList.toggle("kb-open", open);
      }
    };
    const onFocusIn = (e: Event) => {
      const target = e.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) {
        const behavior = animEnabled ? "smooth" : "auto";
        setTimeout(() => {
          try {
            target.scrollIntoView({ block: "center", behavior });
          } catch {}
        }, 50);
      }
      update();
    };
    const onFocusOut = () => {
      setTimeout(update, 60);
    };
    window.addEventListener("focusin", onFocusIn);
    window.addEventListener("focusout", onFocusOut);
    vv?.addEventListener("resize", update);
    vv?.addEventListener("scroll", update);
    if (webapp?.onEvent) {
      webapp.onEvent("viewportChanged", update);
    }
    update();
    return () => {
      window.removeEventListener("focusin", onFocusIn);
      window.removeEventListener("focusout", onFocusOut);
      vv?.removeEventListener("resize", update);
      vv?.removeEventListener("scroll", update);
      if (webapp?.offEvent) {
        webapp.offEvent("viewportChanged", update);
      }
    };
  }, [animEnabled]);

  return <Router />; 
}
