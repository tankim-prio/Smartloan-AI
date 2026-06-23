type SmartLoanPrediction = {
  prediction_id?: number;
  application_id?: number;
  model?: {
    id?: number;
    model_name?: string;
    version?: string;
    model_type?: string;
  };
  result?: string;
  risk_level?: string;
  confidence?: number;
  reason?: string;
  mapped_features?: Record<string, unknown>;
};

let lastPrediction: SmartLoanPrediction | null = null;

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function cleanToken(value: string | null): string {
  if (!value) return "";
  return value.trim().replace(/^Bearer\s+/i, "").replace(/^"|"$/g, "");
}

function saveToken(token: string): void {
  const clean = cleanToken(token);
  if (!clean) return;

  localStorage.setItem("smartloan_token", clean);
  localStorage.setItem("access_token", clean);
  localStorage.setItem("token", clean);
}

function getToken(): string {
  const keys = ["smartloan_token", "access_token", "token", "auth_token", "jwt"];

  for (const key of keys) {
    const token = cleanToken(localStorage.getItem(key));

    if (token && token !== "undefined" && token !== "null" && token.split(".").length === 3) {
      return token;
    }
  }

  return "";
}

async function refreshToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email: "",
      password: "12345678",
    }),
  });

  if (!response.ok) {
    throw new Error(await response.text() || "Login refresh failed.");
  }

  const data = await response.json();
  const token = cleanToken(data.access_token);

  if (!token) {
    throw new Error("Login succeeded but token was missing.");
  }

  saveToken(token);
  return token;
}

async function apiFetch(url: string, options: RequestInit = {}) {
  const buildHeaders = (token: string) => {
    const headers: Record<string, string> = {
      ...((options.headers as Record<string, string>) || {}),
    };

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = headers["Content-Type"] || "application/json";
    }

    headers.Authorization = `Bearer ${token}`;
    return headers;
  };

  let token = getToken();

  if (!token) {
    token = await refreshToken();
  }

  let response = await fetch(`/api/v1${url}`, {
    ...options,
    headers: buildHeaders(token),
  });

  if (response.status === 401 || response.status === 403) {
    token = await refreshToken();

    response = await fetch(`/api/v1${url}`, {
      ...options,
      headers: buildHeaders(token),
    });
  }

  if (!response.ok) {
    const text = await response.text();

    try {
      const parsed = JSON.parse(text);
      throw new Error(parsed.detail || text || "Request failed.");
    } catch {
      throw new Error(text || "Request failed.");
    }
  }

  return response.json();
}

function isApplyPage(): boolean {
  const text = document.body.innerText || "";

  const applyMarkers =
    text.includes("Apply Page") ||
    text.includes("Personal Form") ||
    text.includes("Extracted Fields") ||
    text.includes("Send Review") ||
    text.includes("Create PDF") ||
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

function extractApplicationId(text: string): number | null {
  const patterns = [
    /application[_\s-]*id\s*[:#]?\s*(\d+)/i,
    /application\s*#\s*(\d+)/i,
    /app\s*#\s*(\d+)/i,
    /app[_\s-]*id\s*[:#]?\s*(\d+)/i,
  ];

  for (const pattern of patterns) {
    const match = text.match(pattern);
    const id = Number(match?.[1] || 0);

    if (Number.isFinite(id) && id > 0) {
      return id;
    }
  }

  return null;
}

function findApplicationId(button: HTMLElement): number | null {
  const containers = [
    button.closest("tr"),
    button.closest("table"),
    button.closest("section"),
    button.closest("div"),
    document.body,
  ].filter(Boolean) as HTMLElement[];

  for (const container of containers) {
    const id = extractApplicationId(container.innerText || "");
    if (id) return id;
  }

  return null;
}

async function getLatestReadyApplicationId(): Promise<number> {
  const data = await apiFetch("/mlops/applications/ready");
  const applications = Array.isArray(data)
    ? data
    : Array.isArray(data?.applications)
      ? data.applications
      : [];

  const sorted = applications
    .map((item: Record<string, unknown>) => ({
      id: Number(item.application_id || item.id || 0),
    }))
    .filter((item: { id: number }) => item.id > 0)
    .sort((a: { id: number }, b: { id: number }) => b.id - a.id);

  if (!sorted.length) {
    throw new Error("No ML-ready application found. Please create/extract an application first.");
  }

  return sorted[0].id;
}

function titleCase(value?: string): string {
  if (!value) return "-";

  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function confidence(value?: number): string {
  if (typeof value !== "number" || Number.isNaN(value)) return "-";
  return `${Math.round(value)}%`;
}

function riskClass(value?: string): string {
  const risk = String(value || "").toLowerCase();

  if (risk.includes("low")) return "smartloan-risk-low";
  if (risk.includes("medium")) return "smartloan-risk-medium";
  if (risk.includes("high")) return "smartloan-risk-high";

  return "smartloan-risk-medium";
}

function installStyles(): void {
  if (document.getElementById("smartloan-safe-predict-style")) return;

  const style = document.createElement("style");
  style.id = "smartloan-safe-predict-style";
  style.innerHTML = `
    #smartloan-apply-predict-result,
    #smartloan-inline-prediction-result {
      display: none !important;
    }

    .smartloan-active-predict-box {
      width: 100%;
    }

    .smartloan-active-predict-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }

    .smartloan-active-predict-head h3 {
      margin: 0;
      font-size: 20px;
      font-weight: 900;
      color: #0f172a;
    }

    .smartloan-active-predict-head p {
      margin: 6px 0 0;
      color: #64748b;
      font-size: 12px;
      font-weight: 700;
      line-height: 1.5;
    }

    .smartloan-risk-badge {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 7px 11px;
      font-size: 11px;
      font-weight: 900;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .smartloan-risk-low {
      background: #dcfce7;
      color: #166534;
    }

    .smartloan-risk-medium {
      background: #fef3c7;
      color: #92400e;
    }

    .smartloan-risk-high {
      background: #fee2e2;
      color: #991b1b;
    }

    .smartloan-predict-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin: 12px 0;
    }

    .smartloan-predict-grid div {
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      background: #f8fafc;
      padding: 11px;
    }

    .smartloan-predict-grid span {
      display: block;
      color: #64748b;
      font-size: 11px;
      font-weight: 900;
      margin-bottom: 5px;
    }

    .smartloan-predict-grid strong {
      color: #0f172a;
      font-size: 13px;
      font-weight: 900;
      word-break: break-word;
    }

    .smartloan-predict-reason {
      border: 1px solid #dbeafe;
      background: #eff6ff;
      color: #1e3a8a;
      border-radius: 14px;
      padding: 11px;
      line-height: 1.55;
      font-size: 12px;
      font-weight: 700;
      margin: 12px 0;
    }

    .smartloan-mapped-table-wrap {
      max-height: 230px;
      overflow: auto;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      margin-top: 12px;
    }

    .smartloan-mapped-table {
      width: 100%;
      min-width: 420px;
      border-collapse: collapse;
    }

    .smartloan-mapped-table th,
    .smartloan-mapped-table td {
      padding: 9px 10px;
      border-bottom: 1px solid #e2e8f0;
      text-align: left;
      font-size: 12px;
      color: #0f172a;
    }

    .smartloan-mapped-table th {
      background: #f8fafc;
      color: #334155;
      font-weight: 900;
    }

    .smartloan-predict-toast {
      position: fixed;
      right: 22px;
      bottom: 22px;
      z-index: 999999;
      background: #0f172a;
      color: #ffffff;
      border-radius: 16px;
      padding: 14px 16px;
      box-shadow: 0 18px 45px rgba(15, 23, 42, 0.25);
      font-weight: 800;
      max-width: 360px;
    }
  `;

  document.head.appendChild(style);
}

function toast(message: string): void {
  const oldToast = document.getElementById("smartloan-predict-toast");
  oldToast?.remove();

  const box = document.createElement("div");
  box.id = "smartloan-predict-toast";
  box.className = "smartloan-predict-toast";
  box.textContent = message;

  document.body.appendChild(box);

  setTimeout(() => box.remove(), 4500);
}

function findPredictionResultCard(): HTMLElement | null {
  const headings = Array.from(document.querySelectorAll<HTMLElement>("h1, h2, h3, h4, strong"));

  const heading = headings.find((item) => {
    return (item.textContent || "").trim().toLowerCase() === "prediction result";
  });

  if (!heading) return null;

  let current: HTMLElement = heading;
  let best: HTMLElement = heading.parentElement || heading;

  for (let index = 0; index < 8; index += 1) {
    const parent = current.parentElement;

    if (!parent || parent === document.body) break;

    const text = parent.innerText || "";

    if (
      text.includes("Prediction Result") &&
      !text.includes("Extracted Fields") &&
      !text.includes("Uploaded Documents") &&
      !text.includes("My Recent Applications") &&
      !text.includes("Readable Extracted Text")
    ) {
      best = parent;
      current = parent;
      continue;
    }

    break;
  }

  return best;
}

function mappedFeaturesTable(mapped?: Record<string, unknown>): string {
  const entries = Object.entries(mapped || {});

  if (!entries.length) return "";

  const rows = entries
    .map(([key, value]) => `
      <tr>
        <td>${escapeHtml(key)}</td>
        <td>${escapeHtml(value)}</td>
      </tr>
    `)
    .join("");

  return `
    <div class="smartloan-mapped-table-wrap">
      <table class="smartloan-mapped-table">
        <thead>
          <tr>
            <th>Mapped Feature</th>
            <th>Value Used By Active Model</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function renderPrediction(prediction: SmartLoanPrediction): void {
  installStyles();

  const card = findPredictionResultCard();

  if (!card) {
    throw new Error("Prediction Result card was not found.");
  }

  const risk = prediction.risk_level || "unknown";
  const modelName = prediction.model?.model_name || "Active ML Model";
  const modelVersion = prediction.model?.version || "-";

  card.innerHTML = `
    <div class="smartloan-active-predict-box">
      <div class="smartloan-active-predict-head">
        <div>
          <h3>Prediction Result</h3>
          <p>Generated from active deployed model: ${escapeHtml(modelName)} ${escapeHtml(modelVersion)}</p>
        </div>

        <span class="smartloan-risk-badge ${riskClass(risk)}">${escapeHtml(titleCase(risk))}</span>
      </div>

      <div class="smartloan-predict-grid">
        <div>
          <span>Application ID</span>
          <strong>#${escapeHtml(prediction.application_id || "-")}</strong>
        </div>

        <div>
          <span>Result</span>
          <strong>${escapeHtml(titleCase(prediction.result))}</strong>
        </div>

        <div>
          <span>Confidence</span>
          <strong>${escapeHtml(confidence(prediction.confidence))}</strong>
        </div>

        <div>
          <span>Prediction ID</span>
          <strong>#${escapeHtml(prediction.prediction_id || "-")}</strong>
        </div>
      </div>

      <div class="smartloan-predict-reason">
        ${escapeHtml(prediction.reason || "Prediction completed successfully.")}
      </div>

      ${mappedFeaturesTable(prediction.mapped_features)}
    </div>
  `;

  card.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });
}

async function runPrediction(button: HTMLButtonElement): Promise<void> {
  const oldText = button.textContent || "Predict";

  try {
    button.disabled = true;
    button.textContent = "Predicting...";

    const appId = findApplicationId(button) || await getLatestReadyApplicationId();

    const prediction = await apiFetch(`/mlops/applications/${appId}/predict`, {
      method: "POST",
      body: JSON.stringify({}),
    }) as SmartLoanPrediction;

    lastPrediction = prediction;
    renderPrediction(prediction);
    toast("Prediction completed using active ML model.");
  } catch (error) {
    const message = error instanceof Error ? error.message : "";
    toast(message);
    alert(message);
  } finally {
    button.disabled = false;
    button.textContent = oldText;
  }
}

function installGuard(): void {
  if ((window as any).__smartLoanSafePredictGuardInstalled) return;
  (window as any).__smartLoanSafePredictGuardInstalled = true;

  document.addEventListener(
    "click",
    (event) => {
      const target = event.target as HTMLElement | null;
      if (!target) return;

      const button = target.closest("button") as HTMLButtonElement | null;
      if (!button) return;

      const text = (button.textContent || "").trim().toLowerCase();

      if (text !== "predict") return;
      if (!isApplyPage()) return;

      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();

      runPrediction(button);
    },
    true
  );

  const observer = new MutationObserver(() => {
    if (!isApplyPage()) return;
    if (!lastPrediction) return;

    const duplicate = document.getElementById("smartloan-apply-predict-result");
    duplicate?.remove();
  });

  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
}

installGuard();

export {};
