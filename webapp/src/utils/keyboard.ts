export function isKeyboardOpen(): boolean {
  return Boolean((window as any).__kbOpen);
}

export function subscribeKeyboardOpen(cb: (open: boolean) => void) {
  const handler = (e: Event) => {
    const detail = (e as CustomEvent).detail;
    cb(Boolean(detail));
  };
  window.addEventListener("kb-change", handler);
  return () => window.removeEventListener("kb-change", handler);
}
