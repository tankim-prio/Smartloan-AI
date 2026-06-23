import { useEffect } from "react";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";

const A4_WIDTH = 595.28;
const A4_HEIGHT = 841.89;

function clean(value: unknown) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function textOf(el: Element | null) {
  return clean(el?.textContent || "");
}

function lowerTextOf(el: Element | null) {
  return textOf(el).toLowerCase();
}

function getApplicationId() {
  const body = textOf(document.body);

  const match =
    body.match(/Selected Application\s*Application\s*#(\d+)/i) ||
    body.match(/Application\s*#(\d+)/i) ||
    body.match(/application_id\s+(\d+)/i);

  return match?.[1] || "3";
}

function getValueByLabel(labelName: string) {
  const wanted = labelName.toLowerCase();
  const labels = Array.from(document.querySelectorAll("label")) as HTMLLabelElement[];

  for (const label of labels) {
    const labelText = lowerTextOf(label);

    if (labelText.includes(wanted)) {
      const input = label.querySelector("input, select, textarea") as
        | HTMLInputElement
        | HTMLSelectElement
        | HTMLTextAreaElement
        | null;

      if (input) return clean(input.value);
    }
  }

  return "";
}

function findSmallestBlockContaining(text: string, mustHaveFileInput = false) {
  const wanted = text.toLowerCase();

  const blocks = Array.from(document.querySelectorAll("section, div, fieldset, label")) as HTMLElement[];

  return (
    blocks
      .filter((block) => {
        const hasText = lowerTextOf(block).includes(wanted);
        const hasFile = Boolean(block.querySelector("input[type='file']"));
        return mustHaveFileInput ? hasText && hasFile : hasText;
      })
      .sort((a, b) => textOf(a).length - textOf(b).length)[0] || null
  );
}

function getFileFromBlock(text: string) {
  const block = findSmallestBlockContaining(text, true);

  if (!block) return null;

  const inputs = Array.from(block.querySelectorAll("input[type='file']")) as HTMLInputElement[];

  for (const input of inputs) {
    const file = input.files?.[0];

    if (file) return file;
  }

  return null;
}

function getPhotoFile() {
  const block =
    findSmallestBlockContaining("Applicant Photo", true) ||
    findSmallestBlockContaining("Scan Photo", true);

  if (!block) return null;

  const inputs = Array.from(block.querySelectorAll("input[type='file']")) as HTMLInputElement[];

  for (const input of inputs) {
    const file = input.files?.[0];

    if (file && isImageFile(file)) return file;
  }

  return null;
}

function getCurrentFormData() {
  const firstName = getValueByLabel("First Name");
  const lastName = getValueByLabel("Last Name");

  const identityFile =
    getFileFromBlock("NID / Passport") ||
    getFileFromBlock("NID") ||
    getFileFromBlock("Passport");

  const incomeFile =
    getFileFromBlock("Salary Certificate / TIN Certificate") ||
    getFileFromBlock("Salary Certificate") ||
    getFileFromBlock("TIN Certificate");

  return {
    applicationId: getApplicationId(),
    status: "draft",
    firstName,
    lastName,
    applicantName: clean(`${firstName} ${lastName}`) || "Not provided",
    fatherName: getValueByLabel("Father Name"),
    motherName: getValueByLabel("Mother Name"),
    age: getValueByLabel("Age"),
    phone: getValueByLabel("Phone"),
    email: getValueByLabel("Email"),
    address: getValueByLabel("Address"),
    occupation: getValueByLabel("Occupation"),
    monthlyIncome: getValueByLabel("Monthly Income"),
    photoFile: getPhotoFile(),
    identityFile,
    incomeFile,
  };
}

function findCreatePdfButton() {
  return (
    Array.from(document.querySelectorAll("button")).find((button) => {
      const label = lowerTextOf(button);
      return label === "create pdf" || label === "creating pdf...";
    }) as HTMLButtonElement | null
  );
}

function findCreatePdfCard(button: HTMLElement) {
  let node: HTMLElement | null = button;

  while (node && node !== document.body) {
    const txt = lowerTextOf(node);
    const cls = String(node.className || "").toLowerCase();

    if (
      txt.includes("create pdf") &&
      (cls.includes("card") || node.tagName.toLowerCase() === "section" || node.tagName.toLowerCase() === "div")
    ) {
      return node;
    }

    node = node.parentElement;
  }

  return button.parentElement || document.body;
}

function hideWrongExtractButton(card: HTMLElement) {
  const buttons = Array.from(card.querySelectorAll("button, a")) as HTMLElement[];

  buttons.forEach((button) => {
    if (lowerTextOf(button) === "extract pdf fields") {
      button.style.display = "none";
    }
  });
}

function isImageFile(file: File) {
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();

  return (
    type.startsWith("image/") ||
    name.endsWith(".jpg") ||
    name.endsWith(".jpeg") ||
    name.endsWith(".png")
  );
}

function isPdfFile(file: File) {
  const name = file.name.toLowerCase();
  const type = file.type.toLowerCase();

  return type.includes("pdf") || name.endsWith(".pdf");
}

async function embedImage(pdfDoc: PDFDocument, file: File) {
  const bytes = await file.arrayBuffer();
  const lowerName = file.name.toLowerCase();

  if (file.type.toLowerCase().includes("png") || lowerName.endsWith(".png")) {
    return pdfDoc.embedPng(bytes);
  }

  return pdfDoc.embedJpg(bytes);
}

async function drawImageInsideBox(
  pdfDoc: PDFDocument,
  page: any,
  file: File,
  x: number,
  y: number,
  boxW: number,
  boxH: number
) {
  const image = await embedImage(pdfDoc, file);

  const scale = Math.min(boxW / image.width, boxH / image.height);
  const drawW = image.width * scale;
  const drawH = image.height * scale;

  page.drawRectangle({
    x,
    y,
    width: boxW,
    height: boxH,
    borderColor: rgb(0.8, 0.85, 0.9),
    borderWidth: 1,
  });

  page.drawImage(image, {
    x: x + (boxW - drawW) / 2,
    y: y + (boxH - drawH) / 2,
    width: drawW,
    height: drawH,
  });
}

function drawHeader(page: any, boldFont: any, title: string) {
  page.drawRectangle({
    x: 0,
    y: A4_HEIGHT - 48,
    width: A4_WIDTH,
    height: 48,
    color: rgb(0.15, 0.39, 0.92),
  });

  page.drawText(title, {
    x: 40,
    y: A4_HEIGHT - 31,
    size: 16,
    font: boldFont,
    color: rgb(1, 1, 1),
  });
}

function wrapText(text: string, maxLength = 58) {
  const words = clean(text).split(" ");
  const lines: string[] = [];
  let line = "";

  for (const word of words) {
    const next = line ? `${line} ${word}` : word;

    if (next.length > maxLength) {
      if (line) lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }

  if (line) lines.push(line);

  return lines.length ? lines : ["Not provided"];
}

function drawField(page: any, font: any, boldFont: any, label: string, value: unknown, x: number, y: number) {
  const lines = wrapText(clean(value), 48);

  page.drawText(label, {
    x,
    y,
    size: 10,
    font: boldFont,
    color: rgb(0.06, 0.09, 0.16),
  });

  lines.forEach((line, index) => {
    page.drawText(line, {
      x: x + 122,
      y: y - index * 12,
      size: 10,
      font,
      color: rgb(0.15, 0.2, 0.3),
    });
  });

  return y - Math.max(18, lines.length * 12);
}

async function addFilePage(
  pdfDoc: PDFDocument,
  file: File | null,
  title: string,
  emptyText: string,
  font: any,
  boldFont: any
) {
  if (!file) {
    const page = pdfDoc.addPage([A4_WIDTH, A4_HEIGHT]);
    drawHeader(page, boldFont, title);

    page.drawText(emptyText, {
      x: 40,
      y: A4_HEIGHT - 90,
      size: 12,
      font,
      color: rgb(0.45, 0.5, 0.58),
    });

    return;
  }

  if (isPdfFile(file)) {
    try {
      const bytes = await file.arrayBuffer();
      const sourcePdf = await PDFDocument.load(bytes, {
        ignoreEncryption: true,
      });

      const sourcePages = await pdfDoc.copyPages(sourcePdf, [0]);
      const copiedPage = sourcePages[0];

      pdfDoc.addPage(copiedPage);

      const size = copiedPage.getSize();

      copiedPage.drawRectangle({
        x: 0,
        y: size.height - 36,
        width: size.width,
        height: 36,
        color: rgb(1, 1, 1),
        opacity: 0.94,
      });

      copiedPage.drawText(`${title} — ${file.name}`, {
        x: 32,
        y: size.height - 24,
        size: 10,
        font: boldFont,
        color: rgb(0.06, 0.09, 0.16),
      });

      return;
    } catch (error) {
      const page = pdfDoc.addPage([A4_WIDTH, A4_HEIGHT]);
      drawHeader(page, boldFont, title);

      page.drawText("PDF file was selected, but preview could not be embedded.", {
        x: 40,
        y: A4_HEIGHT - 90,
        size: 11,
        font,
        color: rgb(0.75, 0.1, 0.1),
      });

      page.drawText(`File name: ${file.name}`, {
        x: 40,
        y: A4_HEIGHT - 112,
        size: 10,
        font,
        color: rgb(0.15, 0.2, 0.3),
      });

      return;
    }
  }

  if (isImageFile(file)) {
    const page = pdfDoc.addPage([A4_WIDTH, A4_HEIGHT]);
    drawHeader(page, boldFont, title);

    page.drawText(file.name, {
      x: 40,
      y: A4_HEIGHT - 72,
      size: 10,
      font,
      color: rgb(0.35, 0.42, 0.5),
    });

    try {
      await drawImageInsideBox(pdfDoc, page, file, 45, 70, A4_WIDTH - 90, A4_HEIGHT - 165);
    } catch (error) {
      page.drawText("Image file was selected, but preview could not be embedded.", {
        x: 40,
        y: A4_HEIGHT - 100,
        size: 11,
        font,
        color: rgb(0.75, 0.1, 0.1),
      });
    }

    return;
  }

  const page = pdfDoc.addPage([A4_WIDTH, A4_HEIGHT]);
  drawHeader(page, boldFont, title);

  page.drawText(`Unsupported file type: ${file.name}`, {
    x: 40,
    y: A4_HEIGHT - 90,
    size: 11,
    font,
    color: rgb(0.75, 0.1, 0.1),
  });
}

async function generatePdf() {
  const data = getCurrentFormData();

  const pdfDoc = await PDFDocument.create();
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const boldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

  const page = pdfDoc.addPage([A4_WIDTH, A4_HEIGHT]);

  drawHeader(page, boldFont, "SmartLoan AI — Loan Application");

  page.drawText("Generated from current Step 1, Step 2, and Step 3 information.", {
    x: 40,
    y: A4_HEIGHT - 72,
    size: 10,
    font,
    color: rgb(0.35, 0.42, 0.5),
  });

  page.drawText("Profile Photo", {
    x: 420,
    y: A4_HEIGHT - 104,
    size: 11,
    font: boldFont,
    color: rgb(0.06, 0.09, 0.16),
  });

  if (data.photoFile) {
    try {
      await drawImageInsideBox(pdfDoc, page, data.photoFile, 420, A4_HEIGHT - 252, 125, 136);
    } catch {
      page.drawText("Photo preview failed", {
        x: 420,
        y: A4_HEIGHT - 135,
        size: 9,
        font,
        color: rgb(0.75, 0.1, 0.1),
      });
    }
  } else {
    page.drawRectangle({
      x: 420,
      y: A4_HEIGHT - 252,
      width: 125,
      height: 136,
      borderColor: rgb(0.8, 0.85, 0.9),
      borderWidth: 1,
    });

    page.drawText("No photo", {
      x: 455,
      y: A4_HEIGHT - 185,
      size: 9,
      font,
      color: rgb(0.45, 0.5, 0.58),
    });
  }

  let y = A4_HEIGHT - 108;

  page.drawText("Applicant Information", {
    x: 40,
    y,
    size: 14,
    font: boldFont,
    color: rgb(0.06, 0.09, 0.16),
  });

  y -= 25;

  y = drawField(page, font, boldFont, "Application ID", data.applicationId, 40, y);
  y = drawField(page, font, boldFont, "Status", data.status, 40, y);
  y = drawField(page, font, boldFont, "Applicant Name", data.applicantName, 40, y);
  y = drawField(page, font, boldFont, "First Name", data.firstName, 40, y);
  y = drawField(page, font, boldFont, "Last Name", data.lastName, 40, y);
  y = drawField(page, font, boldFont, "Father Name", data.fatherName, 40, y);
  y = drawField(page, font, boldFont, "Mother Name", data.motherName, 40, y);
  y = drawField(page, font, boldFont, "Age", data.age, 40, y);
  y = drawField(page, font, boldFont, "Phone", data.phone, 40, y);
  y = drawField(page, font, boldFont, "Email", data.email, 40, y);
  y = drawField(page, font, boldFont, "Address", data.address, 40, y);
  y = drawField(page, font, boldFont, "Occupation", data.occupation, 40, y);
  y = drawField(page, font, boldFont, "Monthly Income", data.monthlyIncome, 40, y);

  y -= 5;

  page.drawText("Uploaded Files", {
    x: 40,
    y,
    size: 13,
    font: boldFont,
    color: rgb(0.06, 0.09, 0.16),
  });

  y -= 20;

  y = drawField(page, font, boldFont, "Photo File", data.photoFile?.name || "No photo selected", 40, y);
  y = drawField(page, font, boldFont, "NID / Passport", data.identityFile?.name || "No identity document selected", 40, y);
  y = drawField(page, font, boldFont, "Salary / TIN", data.incomeFile?.name || "No income document selected", 40, y);

  page.drawText(`Generated at: ${new Date().toLocaleString()}`, {
    x: 40,
    y: 34,
    size: 9,
    font,
    color: rgb(0.45, 0.5, 0.58),
  });

  await addFilePage(
    pdfDoc,
    data.identityFile,
    "Page 2 — NID / Passport Document",
    "No NID / Passport document selected.",
    font,
    boldFont
  );

  await addFilePage(
    pdfDoc,
    data.incomeFile,
    "Page 3 — Salary Certificate / TIN Document",
    "No Salary Certificate / TIN document selected.",
    font,
    boldFont
  );

  const pdfBytes = await pdfDoc.save();

  const blob = new Blob([pdfBytes.slice()], {
    type: "application/pdf",
  });

  const filename = `generated_application_${data.applicationId}_${Date.now()}.pdf`;

  return { blob, filename, data };
}

function addDownloadButton(card: HTMLElement, createButton: HTMLElement, blob: Blob, filename: string) {
  const old = card.querySelector("[data-smartloan-download-pdf='true']") as HTMLAnchorElement | null;

  if (old) {
    if (old.href.startsWith("blob:")) URL.revokeObjectURL(old.href);
    old.remove();
  }

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.dataset.smartloanDownloadPdf = "true";
  link.textContent = "Download PDF";
  link.className = "btn green";
  link.href = url;
  link.download = filename;
  link.style.marginLeft = "8px";
  link.style.textDecoration = "none";
  link.style.display = "inline-flex";
  link.style.alignItems = "center";
  link.style.justifyContent = "center";

  createButton.parentElement?.appendChild(link);

  let msg = card.querySelector("[data-smartloan-pdf-ready='true']") as HTMLParagraphElement | null;

  if (!msg) {
    msg = document.createElement("p");
    msg.dataset.smartloanPdfReady = "true";
    msg.style.color = "#15803d";
    msg.style.fontWeight = "900";
    msg.style.marginTop = "10px";
    card.appendChild(msg);
  }

  msg.textContent = "Generated PDF is ready with profile photo, NID/Passport page, and Salary/TIN page.";
}

async function createPdf(button: HTMLButtonElement) {
  const card = findCreatePdfCard(button);
  hideWrongExtractButton(card);

  const oldText = button.textContent || "Create PDF";

  button.textContent = "Creating PDF...";
  button.disabled = true;

  try {
    const result = await generatePdf();
    addDownloadButton(card, button, result.blob, result.filename);
    console.log("SmartLoan PDF generated:", result.data);
  } catch (error: any) {
    console.error("PDF generation failed:", error);
    alert("PDF generation failed. Check console for details.");
  } finally {
    button.textContent = oldText;
    button.disabled = false;
  }
}

function patchScanPhoto() {
  const scanBlock = findSmallestBlockContaining("Applicant Photo", true) || findSmallestBlockContaining("Scan Photo", true);

  if (!scanBlock) return;
  if (scanBlock.querySelector("[data-smartloan-scan-photo='true']")) return;

  const imageInput = Array.from(scanBlock.querySelectorAll("input[type='file']")).find((input) => {
    return String((input as HTMLInputElement).accept || "").includes("image");
  }) as HTMLInputElement | undefined;

  if (!imageInput) return;

  const cameraInput = document.createElement("input");
  cameraInput.type = "file";
  cameraInput.accept = "image/*";
  cameraInput.setAttribute("capture", "user");
  cameraInput.style.display = "none";

  const scanButton = document.createElement("button");
  scanButton.type = "button";
  scanButton.textContent = "Scan Photo";
  scanButton.className = "btn dark";
  scanButton.dataset.smartloanScanPhoto = "true";
  scanButton.style.marginLeft = "8px";

  cameraInput.addEventListener("change", () => {
    const file = cameraInput.files?.[0];

    if (!file) return;

    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      imageInput.files = dt.files;
      imageInput.dispatchEvent(new Event("change", { bubbles: true }));
    } catch {
      alert("Camera photo captured. If it does not appear, choose the captured photo manually.");
    }
  });

  scanButton.addEventListener("click", () => {
    cameraInput.click();
  });

  const confirmStep3Button = Array.from(scanBlock.querySelectorAll("button")).find((button) => {
    return lowerTextOf(button) === "confirm step 3";
  });

  if (confirmStep3Button?.parentElement) {
    confirmStep3Button.parentElement.insertBefore(cameraInput, confirmStep3Button);
    confirmStep3Button.parentElement.insertBefore(scanButton, confirmStep3Button);
  }
}

function runPatch() {
  const createButton = findCreatePdfButton();

  if (createButton) {
    const card = findCreatePdfCard(createButton);
    hideWrongExtractButton(card);
  }

  patchScanPhoto();
}

export default function DynamicPdfPatcher() {
  useEffect(() => {
    function handleClick(event: MouseEvent) {
      const target = event.target as HTMLElement | null;
      const button = target?.closest("button") as HTMLButtonElement | null;

      if (!button) return;

      if (lowerTextOf(button) === "create pdf") {
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();
        void createPdf(button);
      }
    }

    document.addEventListener("click", handleClick, true);

    runPatch();

    const interval = window.setInterval(runPatch, 700);
    const observer = new MutationObserver(runPatch);

    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });

    return () => {
      document.removeEventListener("click", handleClick, true);
      window.clearInterval(interval);
      observer.disconnect();
    };
  }, []);

  return null;
}
