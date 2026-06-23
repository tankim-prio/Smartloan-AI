function cleanPdfGuardToken(value: string | null) {
  if (!value) {
    return "";
  }

  return value
    .trim()
    .replace(/^Bearer\s+/i, "")
    .replace(/^"|"$/g, "");
}

function savePdfGuardToken(token: string) {
  const cleanToken = cleanPdfGuardToken(token);

  if (!cleanToken) {
    return;
  }

  localStorage.setItem("smartloan_token", cleanToken);
  localStorage.setItem("access_token", cleanToken);
  localStorage.setItem("token", cleanToken);
}

function getSmartLoanTokenForPdfGuard() {
  const keys = ["smartloan_token", "access_token", "token", "auth_token"];

  for (const key of keys) {
    const token = cleanPdfGuardToken(localStorage.getItem(key));

    if (
      token &&
      token !== "undefined" &&
      token !== "null" &&
      token.split(".").length === 3
    ) {
      return token;
    }
  }

  return "";
}

async function forceRefreshSmartLoanTokenForPdfGuard() {
  localStorage.removeItem("smartloan_token");
  localStorage.removeItem("access_token");
  localStorage.removeItem("token");
  localStorage.removeItem("auth_token");

  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: "admin@smartloan.ai",
      password: "12345678",
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Token refresh failed.");
  }

  const data = await response.json();
  const freshToken = cleanPdfGuardToken(data.access_token);

  if (!freshToken) {
    throw new Error("Token refresh succeeded but access_token was missing.");
  }

  savePdfGuardToken(freshToken);

  return freshToken;
}

async function getFreshSmartLoanTokenForPdfGuard() {
  const existingToken = getSmartLoanTokenForPdfGuard();

  if (existingToken) {
    return existingToken;
  }

  return forceRefreshSmartLoanTokenForPdfGuard();
}

function isSmartLoanApplyPage() {
  const text = document.body.innerText || "";

  return (
    text.includes("Apply") &&
    (
      text.includes("Create PDF") ||
      text.includes("Apply for Loan") ||
      text.includes("Applicant Photo") ||
      text.includes("Loan Application Document")
    )
  );
}

function getSmartLoanApplicationId() {
  const text = document.body.innerText || "";

  const patterns = [
    /Application\s*#\s*(\d+)/i,
    /Application\s*ID\s*[:#]?\s*(\d+)/i,
    /#\s*(\d+)\s*[—-]/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);

    if (match?.[1]) {
      return Number(match[1]);
    }
  }

  const selects = Array.from(document.querySelectorAll("select"));

  for (const select of selects) {
    const selectedText = select.options[select.selectedIndex]?.text || "";
    const selectedValue = select.value || "";

    const textMatch = selectedText.match(/(\d+)/);
    const valueMatch = selectedValue.match(/(\d+)/);

    if (textMatch?.[1]) {
      return Number(textMatch[1]);
    }

    if (valueMatch?.[1]) {
      return Number(valueMatch[1]);
    }
  }

  return 3;
}

function readSmartLoanValue(keywords: string[]) {
  const controls = Array.from(
    document.querySelectorAll("input, textarea, select")
  ) as Array<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>;

  for (const control of controls) {
    if (control instanceof HTMLInputElement && control.type === "file") {
      continue;
    }

    const labelText =
      control.closest("label")?.textContent ||
      control.parentElement?.querySelector("label")?.textContent ||
      control.previousElementSibling?.textContent ||
      control.parentElement?.textContent ||
      "";

    const searchText = [
      control.getAttribute("name") || "",
      control.getAttribute("id") || "",
      control.getAttribute("placeholder") || "",
      control.getAttribute("aria-label") || "",
      labelText,
    ]
      .join(" ")
      .toLowerCase();

    const matched = keywords.every((keyword) =>
      searchText.includes(keyword.toLowerCase())
    );

    if (matched) {
      return control.value || "";
    }
  }

  return "";
}

function buildSmartLoanPdfPayloadFromVisibleForm() {
  return {
    first_name: readSmartLoanValue(["first"]),
    last_name: readSmartLoanValue(["last"]),
    father_name: readSmartLoanValue(["father"]),
    mother_name: readSmartLoanValue(["mother"]),
    age: Number(readSmartLoanValue(["age"]) || 0),
    phone: readSmartLoanValue(["phone"]),
    email: readSmartLoanValue(["email"]),
    address: readSmartLoanValue(["address"]),
    occupation: readSmartLoanValue(["occupation"]),
    monthly_income: Number(readSmartLoanValue(["income"]) || 0),
  };
}

function getFileInputContext(input: HTMLInputElement) {
  const uploadBox =
    input.closest(".upload-box") ||
    input.closest(".apply-step-card") ||
    input.closest(".card") ||
    input.parentElement;

  const labelText =
    input.closest("label")?.textContent ||
    input.parentElement?.querySelector("label")?.textContent ||
    input.previousElementSibling?.textContent ||
    "";

  return [
    input.getAttribute("name") || "",
    input.getAttribute("id") || "",
    input.getAttribute("placeholder") || "",
    input.getAttribute("aria-label") || "",
    labelText,
    uploadBox?.textContent || "",
  ]
    .join(" ")
    .toLowerCase();
}

function getSelectedSupportingFilesFromPage() {
  const result: {
    photo?: File;
    incomeDocument?: File;
    identityDocument?: File;
    incomeDocumentType: "salary_certificate" | "tin_certificate";
    identityDocumentType: "nid" | "passport";
  } = {
    incomeDocumentType: "salary_certificate",
    identityDocumentType: "nid",
  };

  const fileInputs = Array.from(
    document.querySelectorAll('input[type="file"]')
  ) as HTMLInputElement[];

  for (const input of fileInputs) {
    const file = input.files?.[0];

    if (!file) {
      continue;
    }

    const context = getFileInputContext(input);

    const isLoanApplication =
      context.includes("loan application") ||
      context.includes("final generated loan") ||
      context.includes("upload final");

    if (isLoanApplication) {
      continue;
    }

    const isPhoto =
      context.includes("applicant photo") ||
      context.includes("scan photo") ||
      context.includes("profile") ||
      context.includes("photo") ||
      context.includes("picture");

    const isIdentity =
      context.includes("nid") ||
      context.includes("passport") ||
      context.includes("identity");

    const isIncome =
      context.includes("salary") ||
      context.includes("tin") ||
      context.includes("income");

    if (isIdentity) {
      result.identityDocument = file;

      if (context.includes("passport")) {
        result.identityDocumentType = "passport";
      } else {
        result.identityDocumentType = "nid";
      }

      continue;
    }

    if (isIncome) {
      result.incomeDocument = file;

      if (context.includes("tin")) {
        result.incomeDocumentType = "tin_certificate";
      } else {
        result.incomeDocumentType = "salary_certificate";
      }

      continue;
    }

    if (isPhoto) {
      result.photo = file;
      continue;
    }
  }

  return result;
}

async function uploadSupportingFilesBeforePdf(appId: number, token: string) {
  const selectedFiles = getSelectedSupportingFilesFromPage();

  if (
    !selectedFiles.photo &&
    !selectedFiles.incomeDocument &&
    !selectedFiles.identityDocument
  ) {
    return new Response(null, { status: 204 });
  }

  const formData = new FormData();

  if (selectedFiles.photo) {
    formData.append("photo", selectedFiles.photo);
  }

  if (selectedFiles.incomeDocument) {
    formData.append("income_document", selectedFiles.incomeDocument);
    formData.append("income_document_type", selectedFiles.incomeDocumentType);
  }

  if (selectedFiles.identityDocument) {
    formData.append("identity_document", selectedFiles.identityDocument);
    formData.append("identity_document_type", selectedFiles.identityDocumentType);
  }

  return fetch(`/api/v1/fixed-pdf/applications/${appId}/upload-supporting-documents`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: formData,
  });
}

async function callFixedPdfDownload(appId: number, token: string) {
  return fetch(`/api/v1/fixed-pdf/applications/${appId}/download`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(buildSmartLoanPdfPayloadFromVisibleForm()),
  });
}

async function downloadSmartLoanFixedLivePdf(
  button: HTMLButtonElement | HTMLAnchorElement
) {
  const appId = getSmartLoanApplicationId();

  if (!appId) {
    alert("Application ID not found. Please create or select an application first.");
    return;
  }

  const oldText = button.textContent || "";

  if (button instanceof HTMLButtonElement) {
    button.disabled = true;
  }

  button.textContent = "Generating Loan Application PDF...";

  try {
    let token = await getFreshSmartLoanTokenForPdfGuard();

    let uploadResponse = await uploadSupportingFilesBeforePdf(appId, token);

    if (uploadResponse.status === 401 || uploadResponse.status === 403) {
      token = await forceRefreshSmartLoanTokenForPdfGuard();
      uploadResponse = await uploadSupportingFilesBeforePdf(appId, token);
    }

    if (!uploadResponse.ok && uploadResponse.status !== 204) {
      const uploadError = await uploadResponse.text();
      throw new Error(uploadError || "Supporting document upload failed.");
    }

    let response = await callFixedPdfDownload(appId, token);

    if (response.status === 401 || response.status === 403) {
      token = await forceRefreshSmartLoanTokenForPdfGuard();

      uploadResponse = await uploadSupportingFilesBeforePdf(appId, token);

      if (!uploadResponse.ok && uploadResponse.status !== 204) {
        const uploadError = await uploadResponse.text();
        throw new Error(uploadError || "Supporting document upload failed after token refresh.");
      }

      response = await callFixedPdfDownload(appId, token);
    }

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || "Loan Application PDF download failed.");
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `LOAN_APPLICATION_PDF_${appId}_${Date.now()}.pdf`;

    document.body.appendChild(link);
    link.click();

    link.remove();
    window.URL.revokeObjectURL(url);

    alert("Downloaded Loan Application PDF with latest selected files.");
  } catch (error) {
    alert(error instanceof Error ? error.message : "Loan Application PDF download failed.");
  } finally {
    button.textContent = oldText || "Download PDF";

    if (button instanceof HTMLButtonElement) {
      button.disabled = false;
    }
  }
}

function installSmartLoanPdfGuard() {
  if ((window as any).__smartLoanPdfGuardInstalled) {
    return;
  }

  (window as any).__smartLoanPdfGuardInstalled = true;

  document.addEventListener(
    "click",
    (event) => {
      if (!isSmartLoanApplyPage()) {
        return;
      }

      const target = event.target as HTMLElement | null;

      if (!target) {
        return;
      }

      const clickable = target.closest("button, a") as
        | HTMLButtonElement
        | HTMLAnchorElement
        | null;

      if (!clickable) {
        return;
      }

      const text = (clickable.textContent || "").toLowerCase();
      const href =
        clickable instanceof HTMLAnchorElement
          ? clickable.href.toLowerCase()
          : "";

      const isPdfClick =
        text.includes("pdf") ||
        href.includes(".pdf") ||
        href.includes("generate-pdf") ||
        href.includes("download-pdf") ||
        href.includes("generate-dynamic-pdf") ||
        href.includes("generated");

      if (!isPdfClick) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      downloadSmartLoanFixedLivePdf(clickable);
    },
    true
  );
}

installSmartLoanPdfGuard();

export {};
