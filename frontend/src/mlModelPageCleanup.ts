function isMlModelPage() {
  const pageText = document.body.innerText || "";

  return (
    pageText.includes("ML Model") &&
    pageText.includes("MLOps Flow") &&
    pageText.includes("Model Registry")
  );
}

function installMlModelCleanupStyles() {
  if (document.getElementById("smartloan-ml-model-cleanup-style")) {
    return;
  }

  const style = document.createElement("style");
  style.id = "smartloan-ml-model-cleanup-style";
  style.innerHTML = `
    .smartloan-dataset-only-artifacts * {
      grid-template-columns: 1fr !important;
    }

    .smartloan-dataset-only-artifacts .mlops-preview-panel,
    .smartloan-dataset-only-artifacts .mlops-table-wrap,
    .smartloan-dataset-only-artifacts table {
      width: 100% !important;
      max-width: 100% !important;
    }
  `;

  document.head.appendChild(style);
}

function renameArtifactSection() {
  const allElements = Array.from(document.querySelectorAll<HTMLElement>("h1, h2, h3, p, span"));

  allElements.forEach((element) => {
    const text = (element.textContent || "").trim();

    if (text === "Dataset + Model Artifact Preview" || text === "Dataset Preview + Model Inspection") {
      element.textContent = "Dataset Artifact Preview";
    }

    if (text === "Click View Artifacts in Model Registry to inspect uploaded files.") {
      element.textContent = "Click View Artifacts in Model Registry to preview the uploaded dataset.";
    }

    if (text === "Preview first 10 dataset rows and inspect uploaded model object.") {
      element.textContent = "Preview first 10 rows from the uploaded dataset.";
    }
  });
}

function removeModelFilePreviewCard() {
  const allElements = Array.from(document.querySelectorAll<HTMLElement>("*"));

  const modelHeading = allElements.find((element) => {
    const text = (element.textContent || "").trim();

    return text === "Model File Preview";
  });

  if (!modelHeading) {
    return;
  }

  let current: HTMLElement | null = modelHeading;
  let removable: HTMLElement | null = modelHeading;

  while (current && current.parentElement && current.parentElement !== document.body) {
    const parentText = current.parentElement.textContent || "";

    if (parentText.includes("Dataset Preview")) {
      break;
    }

    removable = current.parentElement;
    current = current.parentElement;
  }

  removable?.remove();
}

function markDatasetArtifactSection() {
  const sections = Array.from(document.querySelectorAll<HTMLElement>("section, .mlops-card, div"));

  const artifactsSection = sections.find((section) => {
    const text = section.textContent || "";

    return text.includes("Dataset Preview") && text.includes("Artifact");
  });

  if (artifactsSection) {
    artifactsSection.classList.add("smartloan-dataset-only-artifacts");
  }
}

function cleanupMlModelPage() {
  if (!isMlModelPage()) {
    return;
  }

  installMlModelCleanupStyles();
  renameArtifactSection();
  removeModelFilePreviewCard();
  markDatasetArtifactSection();
}

function installMlModelPageCleanup() {
  cleanupMlModelPage();

  const observer = new MutationObserver(() => {
    cleanupMlModelPage();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

installMlModelPageCleanup();

export {};
