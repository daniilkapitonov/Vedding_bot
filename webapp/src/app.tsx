import React, { useEffect } from "react";
import { Router } from "./screens/Router";
import { initTelegram } from "./utils/telegram";
import { api, tgInitData, getInviteToken } from "./api";

export default function App() {
  useEffect(() => {
    initTelegram();
    const initData = tgInitData();
    const inviteToken = getInviteToken();
    if (initData || inviteToken) {
      api.auth().catch(() => {});
    }
  }, []);

  return <Router />; 
}
