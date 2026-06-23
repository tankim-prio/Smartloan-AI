function isApplyPageForWorkflowHide() {
  const text = document.body.innerText || "";

  const applyMarkers =
    text.includes("Apply Page") ||
    text.includes("Selected Application") ||
    text.includes("Personal Form") ||
    text.includes("Extracted Fields") ||
    text.includes("My Recent Applications");

  const mlPage =
    text.includes("ML Model") &&
    text.includes("MLOps Flow") &&
    text.includes("Model Registry");

  const reviewPage =
    text.includes("Submitted Applications") &&
    text.includes("Admin Decision");

  return applyMarkers && !mlPage && !reviewPage;
}

function installApplyWorkflowHideStyle() {
  if (document.getElementById("smartloan-hide-apply-workflow-style")) {
    return;
  }

  const style = document.createElement("style");
  style.id = "smartloan-hide-apply-workflow-style";
  style.innerHTML = `
    [data-smartloan-hide-apply-workflow="true"] {
      display: none !important;
    }
  `;

  document.head.appendChild(style);
}

function hideApplyWorkflowSection() {
  if (!isApplyPageForWorkflowHide()) {
    return;
  }

  installApplyWorkflowHideStyle();

  const candidates = Array.from(document.querySelectorAll<HTMLElement>("section, article, div"));

  const workflowBlocks = candidates
    .filter((element) => {
      const text = element.innerText || "";

      const isTarget =
        text.includes("Professional Apply Workflow") &&
        text.includes("Application") &&
        text.includes("Documents") &&
        text.includes("PDF") &&
        text.includes("Prediction") &&
        text.includes("Review") &&
        text.includes("1. Form") &&
        text.includes("6. ML");

      const isTooLarge =
        text.includes("Selected Application") ||
        text.includes("Personal Form") ||
        text.includes("Occupation, Income") ||
        text.includes("Prediction Result") ||
        text.includes("Uploaded Documents") ||
        text.includes("My Recent Applications");

      return isTarget && !isTooLarge;
    })
    .sort((a, b) => {
      const areaA = a.offsetWidth * a.offsetHeight;
      const areaB = b.offsetWidth * b.offsetHeight;

      return areaA - areaB;
    });

  const target = workflowBlocks[0];

  if (target) {
    target.setAttribute("data-smartloan-hide-apply-workflow", "true");
  }
}

function installApplyWorkflowHideGuard() {
  if ((window as any).__smartLoanApplyWorkflowHideInstalled) {
    return;
  }

  (window as any).__smartLoanApplyWorkflowHideInstalled = true;

  hideApplyWorkflowSection();

  const observer = new MutationObserver(() => {
    hideApplyWorkflowSection();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

installApplyWorkflowHideGuard();

export {};
