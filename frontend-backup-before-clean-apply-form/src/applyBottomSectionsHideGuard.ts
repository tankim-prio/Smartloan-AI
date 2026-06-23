function isApplyPageForBottomHide() {
  const text = document.body.innerText || "";

  const applyMarkers =
    text.includes("Apply Page") ||
    text.includes("Selected Application") ||
    text.includes("Personal Form") ||
    text.includes("Extracted Fields") ||
    text.includes("Review Notification");

  const mlPage =
    text.includes("ML Model") &&
    text.includes("MLOps Flow") &&
    text.includes("Model Registry");

  const reviewPage =
    text.includes("Submitted Applications") &&
    text.includes("Admin Decision");

  return applyMarkers && !mlPage && !reviewPage;
}

function installApplyBottomHideStyle() {
  if (document.getElementById("smartloan-hide-apply-bottom-sections-style")) {
    return;
  }

  const style = document.createElement("style");
  style.id = "smartloan-hide-apply-bottom-sections-style";
  style.innerHTML = `
    [data-smartloan-hide-apply-bottom-section="true"] {
      display: none !important;
    }
  `;

  document.head.appendChild(style);
}

function findCardByExactHeading(headingText: string, oppositeHeading: string) {
  const headings = Array.from(
    document.querySelectorAll<HTMLElement>("h1, h2, h3, h4, strong")
  );

  const heading = headings.find((item) => {
    return (item.textContent || "").trim().toLowerCase() === headingText.toLowerCase();
  });

  if (!heading) {
    return null;
  }

  let current: HTMLElement = heading;
  let best: HTMLElement = heading.parentElement || heading;

  for (let index = 0; index < 10; index += 1) {
    const parentElement = current.parentElement;

    if (!parentElement || parentElement === document.body) {
      break;
    }

    const text = parentElement.innerText || "";

    const validCard =
      text.includes(headingText) &&
      !text.includes(oppositeHeading) &&
      !text.includes("Prediction Result") &&
      !text.includes("Extracted Fields") &&
      !text.includes("Review Notification") &&
      parentElement.offsetWidth > 250 &&
      parentElement.offsetHeight > 80;

    if (validCard) {
      best = parentElement;
      current = parentElement;
      continue;
    }

    break;
  }

  return best;
}

function hideApplyBottomSections() {
  if (!isApplyPageForBottomHide()) {
    return;
  }

  installApplyBottomHideStyle();

  const uploadedDocumentsCard = findCardByExactHeading(
    "Uploaded Documents",
    "My Recent Applications"
  );

  const recentApplicationsCard = findCardByExactHeading(
    "My Recent Applications",
    "Uploaded Documents"
  );

  uploadedDocumentsCard?.setAttribute("data-smartloan-hide-apply-bottom-section", "true");
  recentApplicationsCard?.setAttribute("data-smartloan-hide-apply-bottom-section", "true");
}

function installApplyBottomSectionsHideGuard() {
  if ((window as any).__smartLoanApplyBottomSectionsHideInstalled) {
    return;
  }

  (window as any).__smartLoanApplyBottomSectionsHideInstalled = true;

  hideApplyBottomSections();

  const observer = new MutationObserver(() => {
    hideApplyBottomSections();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

installApplyBottomSectionsHideGuard();

export {};
