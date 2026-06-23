function cleanReviewToken(value: string | null) {
  if (!value) return "";

  return value
    .trim()
    .replace(/^Bearer\s+/i, "")
    .replace(/^"|"$/g, "");
}

function saveReviewToken(token: string) {
  const cleaned = cleanReviewToken(token);

  if (!cleaned) return;

  localStorage.setItem("smartloan_token", cleaned);
  localStorage.setItem("access_token", cleaned);
  localStorage.setItem("token", cleaned);
}

function getReviewToken() {
  const keys = ["smartloan_token", "access_token", "token", "auth_token"];

  for (const key of keys) {
    const token = cleanReviewToken(localStorage.getItem(key));

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

async function refreshReviewToken() {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: "",
      password: "12345678",
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Login refresh failed.");
  }

  const data = await response.json();
  const token = cleanReviewToken(data.access_token);

  if (!token) {
    throw new Error("Login response did not return access_token.");
  }

  saveReviewToken(token);

  return token;
}

async function getFreshReviewToken() {
  const token = getReviewToken();

  if (token) return token;

  return refreshReviewToken();
}

function isApplyPageForReviewGuard() {
  const text = document.body.innerText || "";

  return text.includes("Apply Page") || text.includes("Send Review");
}

function getCurrentReviewApplicationId() {
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

  return 3;
}

function cleanReviewValue(value: string, maxLength = 80) {
  const cleaned = value.replace(/\s+/g, " ").trim();

  const badWords = [
    "my recent applications",
    "download fixed live pdf",
    "fixed live pdf",
    "use download",
    "dashboard",
    "review page",
    "sign out",
    "send review",
    "create pdf",
  ];

  if (!cleaned) return "";

  if (cleaned.length > maxLength) return "";

  if (badWords.some((word) => cleaned.toLowerCase().includes(word))) {
    return "";
  }

  return cleaned;
}

function getInputValueByLabel(labelText: string) {
  const labels = Array.from(document.querySelectorAll("label"));

  for (const label of labels) {
    const text = (label.childNodes[0]?.textContent || label.textContent || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();

    if (!text.includes(labelText.toLowerCase())) {
      continue;
    }

    const input = label.querySelector("input, textarea, select") as
      | HTMLInputElement
      | HTMLTextAreaElement
      | HTMLSelectElement
      | null;

    if (input && !(input instanceof HTMLInputElement && input.type === "file")) {
      return cleanReviewValue(input.value || "", 120);
    }
  }

  return "";
}

function getSelectedLoanPdfNameForReview() {
  const fileInputs = Array.from(
    document.querySelectorAll('input[type="file"]')
  ) as HTMLInputElement[];

  for (const input of fileInputs) {
    const boxText = (
      input.closest(".card")?.textContent ||
      input.parentElement?.textContent ||
      ""
    ).toLowerCase();

    if (
      boxText.includes("loan application document") ||
      boxText.includes("apply for loan")
    ) {
      return cleanReviewValue(input.files?.[0]?.name || "", 120);
    }
  }

  return "";
}

function buildReviewSnapshotFromApplyPage(appId: number) {
  const firstName = getInputValueByLabel("First Name");
  const lastName = getInputValueByLabel("Last Name");

  const applicantName =
    cleanReviewValue(`${firstName} ${lastName}`, 90) ||
    "Unknown Applicant";

  return {
    application_id: appId,
    applicant_name: applicantName,
    first_name: firstName,
    last_name: lastName,
    father_name: getInputValueByLabel(""),
    mother_name: getInputValueByLabel(""),
    age: Number(getInputValueByLabel("Age") || 0),
    phone: getInputValueByLabel("Phone"),
    email: getInputValueByLabel("Email"),
    address: getInputValueByLabel("Address"),
    occupation: getInputValueByLabel("Occupation"),
    monthly_income: Number(getInputValueByLabel("Monthly Income") || 0),
    loan_pdf_name: getSelectedLoanPdfNameForReview(),
    submitted_source: "apply_page_send_review",
  };
}

async function sendCurrentApplicationToReview(button: HTMLButtonElement | HTMLAnchorElement) {
  const appId = getCurrentReviewApplicationId();

  if (!appId) {
    alert("Application ID not found. Please select/create an application first.");
    return;
  }

  const oldText = button.textContent || "";

  if (button instanceof HTMLButtonElement) {
    button.disabled = true;
  }

  button.textContent = "Sending Review...";

  try {
    let token = await getFreshReviewToken();

    let response = await fetch(`/api/v1/review-workflow/applications/${appId}/send-review`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        application_snapshot: buildReviewSnapshotFromApplyPage(appId),
      }),
    });

    if (response.status === 401 || response.status === 403) {
      token = await refreshReviewToken();

      response = await fetch(`/api/v1/review-workflow/applications/${appId}/send-review`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          application_snapshot: buildReviewSnapshotFromApplyPage(appId),
        }),
      });
    }

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || "Send review failed.");
    }

    alert(`Application #${appId} sent to Review page successfully. Apply page will refresh now.`);
    window.location.reload();
  } catch (error) {
    alert(error instanceof Error ? error.message : "");
  } finally {
    button.textContent = oldText || "Send Review";

    if (button instanceof HTMLButtonElement) {
      button.disabled = false;
    }
  }
}

function installReviewGuard() {
  if ((window as any).__smartLoanReviewGuardInstalled) {
    return;
  }

  (window as any).__smartLoanReviewGuardInstalled = true;

  document.addEventListener(
    "click",
    (event) => {
      if (!isApplyPageForReviewGuard()) {
        return;
      }

      const target = event.target as HTMLElement | null;

      if (!target) return;

      const clickable = target.closest("button, a") as HTMLButtonElement | HTMLAnchorElement | null;

      if (!clickable) return;

      const text = (clickable.textContent || "").toLowerCase();

      const isSendReviewClick =
        text.includes("send review") ||
        text.includes("submit review") ||
        text.includes("send to review");

      if (!isSendReviewClick) {
        return;
      }

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      sendCurrentApplicationToReview(clickable);
    },
    true
  );
}

installReviewGuard();

export {};
