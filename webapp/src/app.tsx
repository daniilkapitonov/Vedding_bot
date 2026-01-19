import React, { useEffect } from "react";
import { Router } from "./screens/Router";
import { initTelegram } from "./utils/telegram";

export default function App() {
  useEffect(() => {
    initTelegram();
  }, []);

  return <Router />; 
}
