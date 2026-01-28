import React, { useEffect, useState } from "react";
import { Router } from "./screens/Router";
import { initTelegram } from "./utils/telegram";
import { api, tgInitData, getInviteToken, getUiSettings } from "./api";
import { LoadingScreen } from "./components/LoadingScreen";

export default function App() {
  const [showLoading, setShowLoading] = useState(false);
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
      (async () => {
        try {
          await api.auth();
        } catch {}
        try {
          const existsRes: any = await api.profileExists();
          const alreadyShown = sessionStorage.getItem("welcomeShown") === "1";
          if (!existsRes?.exists && !alreadyShown) {
            setShowLoading(true);
            sessionStorage.setItem("welcomeShown", "1");
            setTimeout(() => setShowLoading(false), 5000);
          }
        } catch {}
      })();
    }
  }, []);

  if (showLoading) {
    return <LoadingScreen animate={animEnabled} />;
  }
  return <Router />; 
}
