import React, { useReducer, useState } from "react";
import { HomeScreen } from "./HomeScreen";
import { EventScreen } from "./EventScreen";
import { FamilyScreen } from "./FamilyScreen";
import { ProfileScreen } from "./ProfileScreen";
import { BottomSheet } from "../components/BottomSheet";
import { ModalSheet } from "../components/ModalSheet";

export type RouteKey = "home" | "event" | "family" | "profile";

type NavState = {
  route: RouteKey;
};

type NavAction = { type: "go"; route: RouteKey };

function initialRoute(): RouteKey {
  try {
    const params = new URLSearchParams(window.location.search);
    const screen = (params.get("screen") || "").toLowerCase();
    if (screen === "family") return "family";
    if (screen === "event") return "event";
    if (screen === "profile") return "profile";
  } catch {}
  return "home";
}

const initialState: NavState = { route: initialRoute() };

function reducer(state: NavState, action: NavAction): NavState {
  if (action.type === "go") return { route: action.route };
  return state;
}

export function Router() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuAnchor, setMenuAnchor] = useState<DOMRect | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);

  const go = (route: RouteKey) => dispatch({ type: "go", route });

  const menu = (
    <BottomSheet
      open={menuOpen}
      onClose={() => setMenuOpen(false)}
      anchorRect={menuAnchor}
      items={[
        { label: "Информация о событии", onClick: () => go("event") },
        { label: "Семья", onClick: () => go("family") },
        { label: "О себе", onClick: () => go("profile") },
      ]}
    />
  );

  const about = (
    <ModalSheet open={aboutOpen} onClose={() => setAboutOpen(false)} title="О приложении">
      Здесь вы можете заполнить анкету, указать предпочтения и следить за обновлениями.
    </ModalSheet>
  );

  if (state.route === "home") {
    return (
      <>
        <HomeScreen
          onNavigate={(route) => go(route as RouteKey)}
          onMenu={(rect) => {
            setMenuAnchor(rect);
            setMenuOpen(true);
          }}
          onAbout={() => setAboutOpen(true)}
        />
        {menu}
        {about}
      </>
    );
  }

  if (state.route === "event") {
    return (
      <>
        <EventScreen
          onBack={() => go("home")}
          onMenu={(rect) => {
            setMenuAnchor(rect);
            setMenuOpen(true);
          }}
          onAbout={() => setAboutOpen(true)}
        />
        {menu}
        {about}
      </>
    );
  }

  if (state.route === "family") {
    return (
      <>
        <FamilyScreen
          onBack={() => go("home")}
          onEvent={() => go("event")}
          onMenu={(rect) => {
            setMenuAnchor(rect);
            setMenuOpen(true);
          }}
        />
        {menu}
        {about}
      </>
    );
  }

  return (
    <>
      <ProfileScreen
        onBack={() => go("home")}
        onEvent={() => go("event")}
        onMenu={(rect) => {
          setMenuAnchor(rect);
          setMenuOpen(true);
        }}
      />
      {menu}
      {about}
    </>
  );
}
