import React, { useEffect } from "react";
import { Router } from "./screens/Router";
import { initTelegram } from "./utils/telegram";
import { api, tgInitData, getInviteToken, getUiSettings } from "./api";

export default function App() {
  useEffect(() => {
    initTelegram();
    try {
      const cached = localStorage.getItem("wedding.uiSettings");
      if (cached) {
        const data = JSON.parse(cached);
        const enabled = data?.ui_animations_enabled !== false;
        document.documentElement.style.setProperty("--anim-ms", enabled ? "180ms" : "0ms");
      }
    } catch {}
    getUiSettings()
      .then((data: any) => {
        const enabled = data?.ui_animations_enabled !== false;
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

  return <Router />; 
}
