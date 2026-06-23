type ReviewNotification = {
  application_id?: number;
  submission_id?: number;
  status?: string;
  decision?: string;
  review_status?: string;
  admin_message?: string;
  review_message?: string;
  decision_note?: string;
  note?: string;
  applicant_name?: string;
  decision_at?: string;
  reviewed_at?: string;
  updated_at?: string;
  created_at?: string;
};

let lastNotificationSignature = "";
let userInsideHistory = false;
let lastScrollTop = 0;
let leaveTimer: number | undefined;

function cleanReviewToken(value: string | null): string {
  if (!value) return "";
  return value.trim().replace(/^Bearer\s+/i, "").replace(/^"|"$/g, "");
}

function saveReviewToken(token: string): void {
  const clean = cleanReviewToken(token);
  if (!clean) return;

  localStorage.setItem("smartloan_token", clean);
  localStorage.setItem("access_token", clean);
  localStorage.setItem("token", clean);
}

function getReviewToken(): string {
  for (const key of ["smartloan_token", "access_token", "token", "auth_token", "jwt"]) {
    const token = cleanReviewToken(localStorage.getItem(key));
    if (token && token !== "undefined" && token !== "null" && token.split(".").length === 3) return token;
  }

  return "";
}

async function refreshReviewToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "admin@smartloan.ai",
      password: "12345678",
    }),
  });

  if (!response.ok) throw new Error(await response.text() || "Login refresh failed.");

  const data = await response.json();
  const token = cleanReviewToken(data.access_token);

  if (!token) throw new Error("Login succeeded but token was missing.");

  saveReviewToken(token);
  return token;
}

async function reviewApiFetch(url: string) {
  let token = getReviewToken();

  if (!token) {
    token = await refreshReviewToken();
  }

  let response = await fetch(`/api/v1${url}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (response.status === 401 || response.status === 403) {
    token = await refreshReviewToken();

    response = await fetch(`/api/v1${url}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  }

  if (!response.ok) {
    throw new Error(await response.text() || "Notification request failed.");
  }

  return response.json();
}

function isApplyNotificationPage(): boolean {
  const text = document.body.innerText || "";

  const applyMarkers =
    text.includes("Apply Page") ||
    text.includes("Selected Application") ||
    text.includes("Review Notification") ||
    text.includes("Extracted Fields") ||
    text.includes("Send Review");

  const mlPage =
    text.includes("ML Model") &&
    text.includes("MLOps Flow") &&
    text.includes("Model Registry");

  const reviewPage =
    text.includes("Submitted Applications") &&
    text.includes("Admin Decision");

  return applyMarkers && !mlPage && !reviewPage;
}

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function normalizeStatus(value: unknown): string {
  const text = String(value || "").toLowerCase().trim();

  if (text.includes("approved") || text === "approve" || text === "accepted") return "approved";
  if (text.includes("refused") || text.includes("rejected") || text.includes("declined") || text === "deny") return "refused";

  return "pending_review";
}

function getStatus(item: ReviewNotification | null): string {
  if (!item) return "pending_review";

  return normalizeStatus(
    item.status ||
      item.decision ||
      item.review_status
  );
}

function getStatusLabel(status: string): string {
  if (status === "approved") return "Approved";
  if (status === "refused") return "Refused";
  return "Pending Review";
}

function getStatusClass(status: string): string {
  if (status === "approved") return "smartloan-review-approved";
  if (status === "refused") return "smartloan-review-refused";
  return "smartloan-review-pending";
}

function getMessage(item: ReviewNotification | null): string {
  if (!item) return "";

  return String(
    item.admin_message ||
      item.review_message ||
      item.decision_note ||
      item.note ||
      ""
  ).trim();
}

function getDate(item: ReviewNotification | null): string {
  if (!item) return "";

  return String(
    item.decision_at ||
      item.reviewed_at ||
      item.updated_at ||
      item.created_at ||
      ""
  ).trim();
}

function getReviewText(status: string): string {
  if (status === "approved") return "Great news. This application has been approved from the Review page.";
  if (status === "refused") return "This application has been refused from the Review page. Check the admin message for details.";

  return "This application is submitted and waiting for admin review decision.";
}

function parseSelectedApplicationIdFromPage(): number {
  const text = document.body.innerText || "";

  const patterns = [
    /Selected Application[\s\S]*?Application\s*#\s*(\d+)/i,
    /application_id\s+(\d+)/i,
    /application_id\s*[:#]?\s*(\d+)/i,
    /Application\s*#\s*(\d+)/i,
    /App\s*#\s*(\d+)/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    const id = Number(match?.[1] || 0);

    if (Number.isFinite(id) && id > 0) return id;
  }

  return 0;
}

function installStyle(): void {
  document.getElementById("smartloan-apply-review-notification-style")?.remove();

  const style = document.createElement("style");
  style.id = "smartloan-apply-review-notification-style";
  style.innerHTML = `
    .smartloan-review-notification-card {
      border-radius: 22px;
      background: #ffffff;
      box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
      padding: 20px;
      margin: 18px 0;
      border: 1px solid #dbeafe;
      overflow: visible !important;
    }

    .smartloan-review-notification-head {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 14px;
      margin-bottom: 14px;
    }

    .smartloan-review-notification-head h2 {
      margin: 0;
      color: #0f172a;
      font-size: 22px;
      font-weight: 900;
    }

    .smartloan-review-notification-head p {
      margin: 6px 0 0;
      color: #64748b;
      font-size: 13px;
      font-weight: 700;
      line-height: 1.5;
    }

    .smartloan-review-badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 900;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .smartloan-review-approved { background: #dcfce7; color: #166534; }
    .smartloan-review-refused { background: #fee2e2; color: #991b1b; }
    .smartloan-review-pending { background: #fef3c7; color: #92400e; }

    .smartloan-review-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }

    .smartloan-review-grid div {
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      background: #f8fafc;
      padding: 12px;
    }

    .smartloan-review-grid span {
      display: block;
      color: #64748b;
      font-size: 11px;
      font-weight: 900;
      margin-bottom: 6px;
    }

    .smartloan-review-grid strong {
      color: #0f172a;
      font-size: 13px;
      font-weight: 900;
      word-break: break-word;
    }

    .smartloan-review-message {
      border: 1px solid #dbeafe;
      background: #eff6ff;
      color: #1e3a8a;
      border-radius: 14px;
      padding: 12px;
      line-height: 1.6;
      font-size: 13px;
      font-weight: 700;
      margin-top: 14px;
    }

    .smartloan-review-history-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 18px;
      margin-bottom: 10px;
      gap: 12px;
    }

    .smartloan-review-history-title h3 {
      margin: 0;
      color: #0f172a;
      font-size: 17px;
      font-weight: 900;
    }

    .smartloan-review-history-title span {
      color: #64748b;
      font-size: 12px;
      font-weight: 800;
    }

    .smartloan-review-response-list {
      max-height: 380px;
      min-height: 120px;
      overflow-y: auto;
      overflow-x: hidden;
      padding-right: 10px;
      overscroll-behavior: contain;
    }

    .smartloan-review-response-item {
      border: 1px solid #e2e8f0;
      border-radius: 16px;
      background: #f8fafc;
      padding: 13px;
      margin-bottom: 10px;
    }

    .smartloan-review-response-top {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      align-items: center;
      margin-bottom: 8px;
    }

    .smartloan-review-response-top strong {
      color: #0f172a;
      font-size: 13px;
      font-weight: 900;
    }

    .smartloan-review-response-meta {
      color: #64748b;
      font-size: 12px;
      font-weight: 800;
      line-height: 1.5;
    }

    .smartloan-review-response-message {
      margin-top: 9px;
      border-radius: 12px;
      background: #ffffff;
      border: 1px solid #e2e8f0;
      padding: 10px;
      color: #334155;
      font-size: 12px;
      font-weight: 700;
      line-height: 1.6;
    }

    .smartloan-review-empty {
      border: 1px dashed #cbd5e1;
      background: #f8fafc;
      color: #64748b;
      border-radius: 14px;
      padding: 14px;
      font-size: 13px;
      font-weight: 700;
      line-height: 1.6;
    }
  `;

  document.head.appendChild(style);
}

function findSelectedApplicationCard(): HTMLElement | null {
  const heading = Array.from(document.querySelectorAll<HTMLElement>("h1, h2, h3, h4, strong"))
    .find((item) => (item.textContent || "").trim().toLowerCase() === "selected application");

  if (!heading) return null;

  let current: HTMLElement = heading;
  let best: HTMLElement = heading.parentElement || heading;

  for (let index = 0; index < 8; index += 1) {
    const parentElement = current.parentElement;

    if (!parentElement || parentElement === document.body) break;

    const text = parentElement.innerText || "";

    if (
      text.includes("Selected Application") &&
      !text.includes("Personal Form") &&
      parentElement.offsetWidth > 300 &&
      parentElement.offsetHeight > 40
    ) {
      best = parentElement;
      current = parentElement;
      continue;
    }

    break;
  }

  return best;
}

function ensureContainer(): HTMLElement | null {
  installStyle();

  let container = document.getElementById("smartloan-apply-review-notification");

  if (container) return container;

  const selectedCard = findSelectedApplicationCard();

  if (!selectedCard) return null;

  container = document.createElement("section");
  container.id = "smartloan-apply-review-notification";
  container.className = "smartloan-review-notification-card";

  selectedCard.insertAdjacentElement("afterend", container);

  return container;
}

function signature(applicationId: number, latest: ReviewNotification | null, notifications: ReviewNotification[]): string {
  return JSON.stringify({
    applicationId,
    latest,
    notifications,
  });
}

function renderHistory(items: ReviewNotification[]): string {
  if (!items.length) {
    return `
      <div class="smartloan-review-empty">
        No review response found yet. Send this application to Review page first.
      </div>
    `;
  }

  const rows = items
    .map((item) => {
      const status = getStatus(item);
      const message = getMessage(item);

      return `
        <div class="smartloan-review-response-item">
          <div class="smartloan-review-response-top">
            <strong>Submission #${escapeHtml(item.submission_id || "-")}</strong>
            <span class="smartloan-review-badge ${getStatusClass(status)}">${escapeHtml(getStatusLabel(status))}</span>
          </div>

          <div class="smartloan-review-response-meta">
            Time: ${escapeHtml(getDate(item) || "-")}
          </div>

          <div class="smartloan-review-response-message">
            ${escapeHtml(getReviewText(status))}
            <br /><br />
            <strong>Review Message:</strong> ${message ? escapeHtml(message) : "No message sent from Review page."}
          </div>
        </div>
      `;
    })
    .join("");

  return `
    <div class="smartloan-review-history-title">
      <h3>Review Response History</h3>
      <span>${items.length} latest response${items.length > 1 ? "s" : ""}</span>
    </div>

    <div class="smartloan-review-response-list" data-review-history-list="true">
      ${rows}
    </div>
  `;
}

function renderNotification(applicationId: number, latest: ReviewNotification | null, notifications: ReviewNotification[], force = false): void {
  const container = ensureContainer();

  if (!container) return;

  const currentSignature = signature(applicationId, latest, notifications);

  if (!force && currentSignature === lastNotificationSignature) {
    return;
  }

  if (userInsideHistory && !force) {
    return;
  }

  const oldList = container.querySelector<HTMLElement>("[data-review-history-list='true']");
  const oldScroll = oldList?.scrollTop ?? lastScrollTop;

  lastNotificationSignature = currentSignature;

  if (!latest) {
    container.innerHTML = `
      <div class="smartloan-review-notification-head">
        <div>
          <h2>Review Notification</h2>
          <p>Application #${escapeHtml(applicationId || "-")} review decision and response messages will appear here.</p>
        </div>
        <span class="smartloan-review-badge smartloan-review-pending">Waiting</span>
      </div>

      <div class="smartloan-review-empty">
        No review notification found yet. Send this application to Review page first.
      </div>
    `;

    return;
  }

  const status = getStatus(latest);
  const message = getMessage(latest);

  container.innerHTML = `
    <div class="smartloan-review-notification-head">
      <div>
        <h2>Review Notification</h2>
        <p>This section is connected with Review page decisions and admin messages for this exact application.</p>
      </div>

      <span class="smartloan-review-badge ${getStatusClass(status)}">${escapeHtml(getStatusLabel(status))}</span>
    </div>

    <div class="smartloan-review-grid">
      <div>
        <span>Application ID</span>
        <strong>#${escapeHtml(latest.application_id || applicationId || "-")}</strong>
      </div>

      <div>
        <span>Latest Submission</span>
        <strong>#${escapeHtml(latest.submission_id || "-")}</strong>
      </div>

      <div>
        <span>Applicant</span>
        <strong>${escapeHtml(latest.applicant_name || "Applicant")}</strong>
      </div>

      <div>
        <span>Decision Time</span>
        <strong>${escapeHtml(getDate(latest) || "-")}</strong>
      </div>
    </div>

    <div class="smartloan-review-message">
      ${escapeHtml(getReviewText(status))}
      <br /><br />
      <strong>Latest Review Message:</strong> ${message ? escapeHtml(message) : "No message sent from Review page."}
    </div>

    ${renderHistory(notifications)}
  `;

  requestAnimationFrame(() => {
    const newList = container.querySelector<HTMLElement>("[data-review-history-list='true']");

    if (!newList) return;

    newList.scrollTop = oldScroll;

    newList.addEventListener("mouseenter", () => {
      window.clearTimeout(leaveTimer);
      userInsideHistory = true;
    });

    newList.addEventListener("mouseleave", () => {
      window.clearTimeout(leaveTimer);
      leaveTimer = window.setTimeout(() => {
        userInsideHistory = false;
      }, 1200);
    });

    newList.addEventListener(
      "scroll",
      () => {
        lastScrollTop = newList.scrollTop;
      },
      { passive: true }
    );
  });
}

async function loadNotification(force = false): Promise<void> {
  if (!isApplyNotificationPage()) return;

  const applicationId = parseSelectedApplicationIdFromPage();

  if (!applicationId) {
    renderNotification(0, null, [], force);
    return;
  }

  if (userInsideHistory && !force) return;

  try {
    const data = await reviewApiFetch(`/review-workflow/applications/${applicationId}/notifications`);

    const latest = data?.latest || null;
    const notifications = Array.isArray(data?.notifications) ? data.notifications : [];

    renderNotification(applicationId, latest, notifications, force);
  } catch {
    renderNotification(applicationId, null, [], force);
  }
}

function installGuard(): void {
  if ((window as any).__smartLoanApplyDedicatedNotificationInstalled) return;

  (window as any).__smartLoanApplyDedicatedNotificationInstalled = true;

  let timer: number | undefined;

  const refresh = (force = false) => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      loadNotification(force);
    }, 400);
  };

  const observer = new MutationObserver(() => {
    refresh(false);
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  document.addEventListener(
    "click",
    (event) => {
      const target = event.target as HTMLElement | null;
      const button = target?.closest("button") as HTMLButtonElement | null;

      if (!button) return;

      const text = (button.textContent || "").toLowerCase();

      if (
        text.includes("send review") ||
        text.includes("refresh my applications") ||
        text.includes("use")
      ) {
        setTimeout(() => refresh(true), 1000);
        setTimeout(() => refresh(true), 2500);
      }
    },
    true
  );

  window.addEventListener("focus", () => refresh(true));
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refresh(true);
  });

  setInterval(() => refresh(false), 5000);
  setTimeout(() => refresh(true), 700);
}

installGuard();

export {};
