import { useEffect } from "react";

const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

function textOf(el: Element | null) {
  return (el?.textContent || "").trim();
}

function lowerTextOf(el: Element | null) {
  return textOf(el).toLowerCase();
}

function allButtons(root: ParentNode = document) {
  return Array.from(root.querySelectorAll("button, a")) as HTMLElement[];
}

function findButton(label: string, root: ParentNode = document) {
  const wanted = label.trim().toLowerCase();

  return allButtons(root).find((button) => {
    return textOf(button).toLowerCase() === wanted;
  }) || null;
}

function findButtons(label: string, root: ParentNode = document) {
  const wanted = label.trim().toLowerCase();

  return allButtons(root).filter((button) => {
    return textOf(button).toLowerCase() === wanted;
  });
}

function findCardAround(el: HTMLElement | null, title: string) {
  if (!el) return null;

  const titleLower = title.toLowerCase();
  let node: HTMLElement | null = el;

  while (node && node !== document.body) {
    const className = String(node.className || "").toLowerCase();
    const nodeText = lowerTextOf(node);

    if (
      nodeText.includes(titleLower) &&
      (className.includes("card") || node.tagName.toLowerCase() === "section")
    ) {
      return node;
    }

    node = node.parentElement;
  }

  return el.parentElement;
}

function findCardByTitle(title: string) {
  const titleLower = title.toLowerCase();

  const headings = Array.from(
    document.querySelectorAll("h1, h2, h3, h4, strong, span, div")
  ) as HTMLElement[];

  const heading = headings.find((el) => lowerTextOf(el) === titleLower);

  if (!heading) return null;

  return findCardAround(heading, title);
}

function isApplyPageVisible() {
  const bodyText = lowerTextOf(document.body);

  return (
    bodyText.includes("apply page") &&
    bodyText.includes("create pdf") &&
    bodyText.includes("apply for loan")
  );
}

function getApplicationId() {
  const body = textOf(document.body);

  const selectedMatch =
    body.match(/Selected Application\s*Application\s*#(\d+)/i) ||
    body.match(/Application\s*#(\d+)\s*—/i) ||
    body.match(/application_id\s+(\d+)/i) ||
    body.match(/Application\s*ID\s*(\d+)/i);

  return selectedMatch?.[1] || "1";
}

function injectStyle() {
  if (document.getElementById("smartloan-apply-workflow-patch-style")) return;

  const style = document.createElement("style");
  style.id = "smartloan-apply-workflow-patch-style";

  style.textContent = `
    .sl-patch-btn {
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      min-height: 38px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 900;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      margin: 6px 8px 6px 0;
      transition: 0.15s ease;
    }

    .sl-patch-btn:hover:not(:disabled) {
      transform: translateY(-1px);
      box-shadow: 0 10px 18px rgba(15, 23, 42, 0.12);
    }

    .sl-patch-btn:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }

    .sl-patch-primary {
      background: #2563eb;
      color: #ffffff;
    }

    .sl-patch-green {
      background: #16a34a;
      color: #ffffff;
    }

    .sl-patch-dark {
      background: #111827;
      color: #ffffff;
    }

    .sl-patch-soft {
      background: #e8eef6;
      color: #0f172a;
    }

    .sl-readable-text-panel {
      grid-column: 1 / -1;
      background: #ffffff;
      border: 1px solid #dfe7f0;
      border-radius: 18px;
      padding: 16px;
      box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
      margin-top: 0;
    }

    .sl-readable-text-panel h2 {
      margin: 0 0 6px;
      font-size: 20px;
      font-weight: 950;
      letter-spacing: -0.03em;
      color: #0f172a;
    }

    .sl-readable-text-panel p {
      margin: 0 0 12px;
      color: #64748b;
      font-size: 13px;
      line-height: 1.55;
    }

    .sl-readable-pre {
      margin: 12px 0;
      padding: 16px;
      min-height: 220px;
      max-height: 420px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 14px;
      font-size: 13px;
      line-height: 1.7;
    }

    .sl-patch-message {
      margin: 10px 0;
      padding: 10px 12px;
      border-radius: 12px;
      background: #dbeafe;
      color: #1d4ed8;
      font-size: 13px;
      font-weight: 850;
    }

    .sl-final-action-row {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
  `;

  document.head.appendChild(style);
}

async function readResponse(response: Response) {
  const text = await response.text();

  if (!text) return {};

  try {
    return JSON.parse(text);
  } catch {
    return { raw_text: text };
  }
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");

  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

async function downloadGeneratedPdf(button: HTMLElement) {
  const appId = getApplicationId();
  const oldText = button.textContent || "Download PDF";

  button.textContent = "Downloading...";
  button.setAttribute("disabled", "true");

  const candidates = [
    { method: "GET", url: `${API_BASE}/applications/${appId}/download-pdf` },
    { method: "GET", url: `${API_BASE}/applications/${appId}/pdf` },
    { method: "GET", url: `${API_BASE}/applications/${appId}/generated-pdf` },
    { method: "POST", url: `${API_BASE}/applications/${appId}/generate-pdf` },
  ];

  try {
    let lastError = "";

    for (const item of candidates) {
      try {
        const response = await fetch(item.url, { method: item.method });

        if (!response.ok) {
          lastError = `${item.method} ${item.url} failed: ${response.status}`;
          continue;
        }

        const contentType = response.headers.get("content-type") || "";

        if (
          contentType.includes("application/pdf") ||
          contentType.includes("application/octet-stream")
        ) {
          const blob = await response.blob();
          downloadBlob(blob, `generated_application_${appId}.pdf`);
          button.textContent = oldText;
          button.removeAttribute("disabled");
          return;
        }

        const data = await readResponse(response);

        const rawUrl =
          data.download_url ||
          data.pdf_url ||
          data.file_url ||
          data.url ||
          data.path;

        if (rawUrl) {
          const finalUrl = String(rawUrl).startsWith("http")
            ? String(rawUrl)
            : `${API_BASE}${rawUrl}`;

          const pdfResponse = await fetch(finalUrl);

          if (pdfResponse.ok) {
            const blob = await pdfResponse.blob();
            downloadBlob(blob, data.filename || `generated_application_${appId}.pdf`);
            button.textContent = oldText;
            button.removeAttribute("disabled");
            return;
          }

          window.open(finalUrl, "_blank");
          button.textContent = oldText;
          button.removeAttribute("disabled");
          return;
        }
      } catch (error: any) {
        lastError = error.message || "Download failed.";
      }
    }

    alert(
      "PDF download route was not found in backend. Last error: " +
        lastError +
        "\n\nFrontend button is now correct, but FastAPI needs a download endpoint."
    );
  } finally {
    button.textContent = oldText;
    button.removeAttribute("disabled");
  }
}

function buildFallbackReadableText() {
  const lines: string[] = [];

  lines.push("READABLE LOAN APPLICATION TEXT");
  lines.push("--------------------------------");

  const extractedCard = findCardByTitle("Extracted Fields");

  if (extractedCard) {
    lines.push("");
    lines.push("Applicant / Extracted Fields:");

    const rows = Array.from(extractedCard.querySelectorAll("tr, .field-row, div")) as HTMLElement[];

    const seen = new Set<string>();

    rows.forEach((row) => {
      const rowText = textOf(row).replace(/\s+/g, " ").trim();

      if (
        rowText &&
        rowText.length < 180 &&
        !seen.has(rowText) &&
        (
          rowText.includes("application_id") ||
          rowText.includes("applicant_name") ||
          rowText.includes("father_name") ||
          rowText.includes("mother_name") ||
          rowText.includes("monthly_income") ||
          rowText.includes("occupation") ||
          rowText.includes("phone") ||
          rowText.includes("email") ||
          rowText.includes("address") ||
          rowText.includes("age")
        )
      ) {
        seen.add(rowText);
        lines.push("- " + rowText);
      }
    });
  }

  const docsCard = findCardByTitle("Uploaded Documents");

  if (docsCard) {
    lines.push("");
    lines.push("Uploaded Documents:");

    const docText = textOf(docsCard)
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean);

    docText.forEach((line) => {
      if (
        line.toLowerCase().includes("photo") ||
        line.toLowerCase().includes("salary") ||
        line.toLowerCase().includes("nid") ||
        line.toLowerCase().includes("passport") ||
        line.toLowerCase().includes("generated pdf") ||
        line.toLowerCase().includes(".pdf") ||
        line.toLowerCase().includes(".jpg") ||
        line.toLowerCase().includes(".jpeg") ||
        line.toLowerCase().includes(".png")
      ) {
        lines.push("- " + line);
      }
    });
  }

  lines.push("");
  lines.push("Note: This fallback text was built from visible page data because backend /extract-text did not return readable text.");

  return lines.join("\n");
}

function ensureReadableTextPanel(applyCard: HTMLElement) {
  let panel = document.getElementById("sl-readable-text-panel") as HTMLElement | null;

  if (panel) return panel;

  panel = document.createElement("section");
  panel.id = "sl-readable-text-panel";
  panel.className = "sl-readable-text-panel";

  panel.innerHTML = `
    <h2>Readable Extracted Text</h2>
    <p>
      After clicking Extract Text, this section will show readable PDF text with applicant data,
      scanned photo reference, salary document reference, and identity document reference.
    </p>
    <div class="sl-patch-message">No readable text yet. Confirm loan PDF upload, then click Extract Text.</div>
  `;

  applyCard.insertAdjacentElement("afterend", panel);

  return panel;
}

function renderReadableText(panel: HTMLElement, text: string) {
  panel.innerHTML = "";

  const title = document.createElement("h2");
  title.textContent = "Readable Extracted Text";

  const desc = document.createElement("p");
  desc.textContent =
    "Readable text extracted from the uploaded generated PDF. Now click Extract Fields.";

  const pre = document.createElement("pre");
  pre.className = "sl-readable-pre";
  pre.textContent = text;

  const extractFieldsButton = document.createElement("button");
  extractFieldsButton.type = "button";
  extractFieldsButton.className = "sl-patch-btn sl-patch-primary";
  extractFieldsButton.textContent = "Extract Fields";
  extractFieldsButton.dataset.slPatchExtractFields = "true";

  extractFieldsButton.addEventListener("click", async () => {
    extractFieldsButton.textContent = "Extracting Fields...";
    extractFieldsButton.setAttribute("disabled", "true");

    const oldWrongButton = findButton("Extract PDF Fields");

    if (oldWrongButton) {
      oldWrongButton.click();
    } else {
      const appId = getApplicationId();

      try {
        await fetch(`${API_BASE}/applications/${appId}/extract-fields`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });
      } catch {
        // existing project may not have this endpoint yet
      }
    }

    setTimeout(() => {
      patchExtractedFieldsActions();
      extractFieldsButton.textContent = "Extract Fields";
      extractFieldsButton.removeAttribute("disabled");
    }, 900);
  });

  panel.appendChild(title);
  panel.appendChild(desc);
  panel.appendChild(pre);
  panel.appendChild(extractFieldsButton);
}

async function extractReadableText(button: HTMLElement, applyCard: HTMLElement) {
  const appId = getApplicationId();
  const panel = ensureReadableTextPanel(applyCard);

  const oldText = button.textContent || "Extract Text";
  button.textContent = "Extracting Text...";
  button.setAttribute("disabled", "true");

  try {
    let readableText = "";

    const candidates = [
      `${API_BASE}/applications/${appId}/extract-text`,
      `${API_BASE}/applications/${appId}/extract-pdf-text`,
      `${API_BASE}/applications/${appId}/readable-text`,
    ];

    for (const url of candidates) {
      try {
        const response = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        });

        if (!response.ok) continue;

        const data = await readResponse(response);

        readableText =
          data.extracted_text ||
          data.readable_text ||
          data.text ||
          data.raw_text ||
          "";

        if (readableText) break;
      } catch {
        // try next endpoint
      }
    }

    if (!readableText) {
      readableText = buildFallbackReadableText();
    }

    renderReadableText(panel, readableText);
  } finally {
    button.textContent = oldText;
    button.removeAttribute("disabled");
  }
}

function patchScanPhoto() {
  const scanCard =
    findCardByTitle("Scan Photo") ||
    findCardAround(findButton("Confirm Step 3"), "Scan Photo");

  if (!scanCard) return;

  const photoInput = Array.from(scanCard.querySelectorAll("input[type='file']")) as HTMLInputElement[];

  const originalInput = photoInput.find((input) => {
    return (input.accept || "").toLowerCase().includes("image");
  });

  if (!originalInput) return;

  if (scanCard.querySelector("[data-sl-scan-photo-button='true']")) return;

  const cameraInput = document.createElement("input");
  cameraInput.type = "file";
  cameraInput.accept = "image/*";
  cameraInput.setAttribute("capture", "user");
  cameraInput.style.display = "none";
  cameraInput.dataset.slCameraInput = "true";

  cameraInput.addEventListener("change", () => {
    const file = cameraInput.files?.[0];

    if (!file) return;

    try {
      const dataTransfer = new DataTransfer();
      dataTransfer.items.add(file);
      originalInput.files = dataTransfer.files;
      originalInput.dispatchEvent(new Event("change", { bubbles: true }));
    } catch {
      alert("Photo captured. If it does not appear in the upload field, choose the captured image manually.");
    }
  });

  const scanButton = document.createElement("button");
  scanButton.type = "button";
  scanButton.className = "sl-patch-btn sl-patch-dark";
  scanButton.textContent = "Scan Photo";
  scanButton.dataset.slScanPhotoButton = "true";

  scanButton.addEventListener("click", () => {
    cameraInput.click();
  });

  const confirmButton = findButton("Confirm Step 3", scanCard);

  if (confirmButton?.parentElement) {
    confirmButton.parentElement.insertBefore(scanButton, confirmButton);
    confirmButton.parentElement.insertBefore(cameraInput, confirmButton);
  } else {
    originalInput.insertAdjacentElement("afterend", cameraInput);
    originalInput.insertAdjacentElement("afterend", scanButton);
  }
}

function patchCreatePdf() {
  const createButton = findButton("Create PDF");
  const createCard =
    findCardByTitle("Create PDF") ||
    findCardAround(createButton, "Create PDF");

  if (!createCard) return;

  const wrongButtons = findButtons("Extract PDF Fields", createCard);

  wrongButtons.forEach((button) => {
    button.style.display = "none";
    button.dataset.slOldExtractPdfFields = "true";
  });

  const cardText = lowerTextOf(createCard);
  const pdfReady =
    cardText.includes("generated pdf is ready") ||
    cardText.includes("pdf is ready") ||
    cardText.includes("ready");

  if (!pdfReady) return;

  if (createCard.querySelector("[data-sl-download-pdf-button='true']")) return;

  const downloadButton = document.createElement("button");
  downloadButton.type = "button";
  downloadButton.className = "sl-patch-btn sl-patch-green";
  downloadButton.textContent = "Download PDF";
  downloadButton.dataset.slDownloadPdfButton = "true";

  downloadButton.addEventListener("click", () => {
    downloadGeneratedPdf(downloadButton);
  });

  const insertAfter = createButton || createCard.querySelector("button");

  if (insertAfter?.parentElement) {
    insertAfter.parentElement.appendChild(downloadButton);
  } else {
    createCard.appendChild(downloadButton);
  }
}

function patchApplyForLoan() {
  const confirmButton = findButton("Confirm Loan Application Upload");
  const applyCard =
    findCardByTitle("Apply for Loan") ||
    findCardAround(confirmButton, "Apply for Loan");

  if (!applyCard) return;

  const appId = getApplicationId();
  const confirmedKey = `smartloan_pdf_confirmed_${appId}`;

  const oldPredict = findButton("Predict", applyCard);
  const oldReview = findButton("Send Review", applyCard);

  if (oldPredict) {
    oldPredict.style.display = "none";
    oldPredict.dataset.slOldPredict = "true";
  }

  if (oldReview) {
    oldReview.style.display = "none";
    oldReview.dataset.slOldReview = "true";
  }

  const pdfInput = Array.from(applyCard.querySelectorAll("input[type='file']"))[0] as HTMLInputElement | undefined;

  if (pdfInput && !pdfInput.dataset.slPatchResetListener) {
    pdfInput.dataset.slPatchResetListener = "true";

    pdfInput.addEventListener("change", () => {
      localStorage.removeItem(confirmedKey);
      const btn = applyCard.querySelector("[data-sl-extract-text-button='true']") as HTMLElement | null;
      if (btn) btn.style.display = "none";
    });
  }

  if (confirmButton && !confirmButton.dataset.slPatchConfirmListener) {
    confirmButton.dataset.slPatchConfirmListener = "true";

    confirmButton.addEventListener("click", () => {
      setTimeout(() => {
        localStorage.setItem(confirmedKey, "true");
        patchApplyForLoan();
      }, 900);
    });
  }

  let extractTextButton = applyCard.querySelector("[data-sl-extract-text-button='true']") as HTMLElement | null;

  if (!extractTextButton) {
    extractTextButton = document.createElement("button");
    extractTextButton.type = "button";
    extractTextButton.className = "sl-patch-btn sl-patch-primary";
    extractTextButton.textContent = "Extract Text";
    extractTextButton.dataset.slExtractTextButton = "true";

    extractTextButton.addEventListener("click", () => {
      extractReadableText(extractTextButton as HTMLElement, applyCard);
    });

    if (confirmButton?.parentElement) {
      confirmButton.parentElement.appendChild(extractTextButton);
    } else {
      applyCard.appendChild(extractTextButton);
    }
  }

  const isConfirmed = localStorage.getItem(confirmedKey) === "true";
  extractTextButton.style.display = isConfirmed ? "inline-flex" : "none";

  ensureReadableTextPanel(applyCard);
}

function patchExtractedFieldsActions() {
  const fieldsCard = findCardByTitle("Extracted Fields");

  if (!fieldsCard) return;

  const hasFields =
    lowerTextOf(fieldsCard).includes("application_id") ||
    lowerTextOf(fieldsCard).includes("applicant_name") ||
    lowerTextOf(fieldsCard).includes("monthly_income");

  if (!hasFields) return;

  if (fieldsCard.querySelector("[data-sl-final-action-row='true']")) return;

  const row = document.createElement("div");
  row.className = "sl-final-action-row";
  row.dataset.slFinalActionRow = "true";

  const reviewButton = document.createElement("button");
  reviewButton.type = "button";
  reviewButton.className = "sl-patch-btn sl-patch-green";
  reviewButton.textContent = "Send Review";

  const predictButton = document.createElement("button");
  predictButton.type = "button";
  predictButton.className = "sl-patch-btn sl-patch-primary";
  predictButton.textContent = "Predict";

  reviewButton.addEventListener("click", async () => {
    const original = document.querySelector("[data-sl-old-review='true']") as HTMLElement | null;

    if (original) {
      original.click();
      return;
    }

    const appId = getApplicationId();

    await fetch(`${API_BASE}/applications/${appId}/send-review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  });

  predictButton.addEventListener("click", async () => {
    const original = document.querySelector("[data-sl-old-predict='true']") as HTMLElement | null;

    if (original) {
      original.click();
      return;
    }

    const appId = getApplicationId();

    await fetch(`${API_BASE}/applications/${appId}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
  });

  row.appendChild(reviewButton);
  row.appendChild(predictButton);
  fieldsCard.appendChild(row);
}

function runPatch() {
  if (!isApplyPageVisible()) return;

  injectStyle();
  patchScanPhoto();
  patchCreatePdf();
  patchApplyForLoan();
  patchExtractedFieldsActions();
}

export default function ApplyWorkflowPatcher() {
  useEffect(() => {
    injectStyle();

    const run = () => {
      try {
        runPatch();
      } catch {
        // keep page safe
      }
    };

    run();

    const interval = window.setInterval(run, 700);

    const observer = new MutationObserver(run);
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    return () => {
      window.clearInterval(interval);
      observer.disconnect();
    };
  }, []);

  return null;
}
