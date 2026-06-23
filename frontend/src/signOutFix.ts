function clearSmartLoanSession() {
  const exactKeys = [
    "smartloan_token",
    "access_token",
    "token",
    "auth_token",
    "jwt",
    "user",
    "smartloan_user",
    "current_user",
  ];

  exactKeys.forEach((key) => {
    localStorage.removeItem(key);
    sessionStorage.removeItem(key);
  });

  Object.keys(localStorage).forEach((key) => {
    const lower = key.toLowerCase();

    if (
      lower.includes("token") ||
      lower.includes("auth") ||
      lower.includes("jwt") ||
      lower.includes("user")
    ) {
      localStorage.removeItem(key);
    }
  });

  Object.keys(sessionStorage).forEach((key) => {
    const lower = key.toLowerCase();

    if (
      lower.includes("token") ||
      lower.includes("auth") ||
      lower.includes("jwt") ||
      lower.includes("user")
    ) {
      sessionStorage.removeItem(key);
    }
  });
}

function installSmartLoanSignOutFix() {
  if ((window as any).__smartLoanSignOutFixInstalled) {
    return;
  }

  (window as any).__smartLoanSignOutFixInstalled = true;

  document.addEventListener(
    "click",
    (event) => {
      const target = event.target as HTMLElement | null;

      if (!target) {
        return;
      }

      const button = target.closest("button, a") as HTMLButtonElement | HTMLAnchorElement | null;

      if (!button) {
        return;
      }

      const text = (button.textContent || "").toLowerCase().trim();

      if (!text.includes("sign out") && !text.includes("logout") && !text.includes("log out")) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      clearSmartLoanSession();

      window.location.href = window.location.origin;
    },
    true
  );
}

installSmartLoanSignOutFix();

export {};
