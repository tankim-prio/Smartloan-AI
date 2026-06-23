import { useEffect } from "react";

export default function HideWrongExtractPdfButton() {
  useEffect(() => {
    function hideWrongButton() {
      const buttons = Array.from(document.querySelectorAll("button"));

      buttons.forEach((button) => {
        const text = button.textContent?.trim().toLowerCase();

        if (text === "extract pdf fields") {
          const nearestCard =
            button.closest("[class*='card']") ||
            button.closest("section") ||
            button.parentElement;

          const cardText = nearestCard?.textContent?.toLowerCase() || "";

          if (cardText.includes("create pdf")) {
            button.style.display = "none";
          }
        }
      });
    }

    hideWrongButton();

    const observer = new MutationObserver(hideWrongButton);
    observer.observe(document.body, { childList: true, subtree: true });

    return () => observer.disconnect();
  }, []);

  return null;
}
