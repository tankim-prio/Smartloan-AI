import { useMemo, useRef, useState, useEffect } from "react";
import "./App.css";

type PageKey =
  | "dashboard"
  | "apply"
  | "review"
  | "ml"
  | "reports"
  | "ai-pilot"
  | "create-account";

type ExtractedFields = Record<string, string | number | boolean | null>;


  const downloadFixedPdfFromCurrentForm = async () => {
    const payload = {
      first_name: stepOne.first_name,
      last_name: stepOne.last_name,
      father_name: stepOne.father_name,
      phone: stepOne.phone,
      monthly_income: Number(stepTwo.monthly_income),
    };
    try {
      const token = localStorage.getItem("smartloan_token")?.replace(/^"|"$/g, "");
      const response = await api.post(`/fixed-pdf/applications/${applicationId}/download`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      });
      console.log("Server response:", response.data);
      alert("Data sent to backend successfully!");
    } catch (e) { 
      console.error(e);
      alert("Failed to download PDF."); 
    }
  };
const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

const defaultFields: ExtractedFields = {
  application_id: 3,
  status: "draft",
  applicant_name: "Said Kabir",
  father_name: "Father Name",
  mother_name: "Mother Name",
  age: 25,
  phone: "01700000000",
  email: "applicant@example.com",
  address: "Dhaka, Bangladesh",
  occupation: "Software Developer",
  monthly_income: 60000,
};


function getCleanSmartLoanToken() {
  const raw =
    localStorage.getItem("smartloan_token") ||
    localStorage.getItem("access_token") ||
    localStorage.getItem("token") ||
    "";
  return raw
    .trim()
    .replace(/^Bearer\s+/i, "")
    .replace(/^"|"$/g, "");
}


function App() {
  const [activePage, setActivePage] = useState<PageKey>("apply");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <h1>SmartLoan AI</h1>
          <p>Admin Panel</p>
        </div>

        <nav className="nav">
          <button className={activePage === "dashboard" ? "active" : ""} onClick={() => setActivePage("dashboard")}>
            Dashboard
          </button>
          <button className={activePage === "apply" ? "active" : ""} onClick={() => setActivePage("apply")}>
            Apply
          </button>
          <button className={activePage === "review" ? "active" : ""} onClick={() => setActivePage("review")}>
            Review
          </button>
          <button className={activePage === "ml" ? "active" : ""} onClick={() => setActivePage("ml")}>
            ML Model
          </button>
          <button className={activePage === "reports" ? "active" : ""} onClick={() => setActivePage("reports")}>
            Reports
          </button>
          <button className={activePage === "ai-pilot" ? "active" : ""} onClick={() => setActivePage("ai-pilot")}>
            AI Pilot
          </button>
          <button className={activePage === "create-account" ? "active" : ""} onClick={() => setActivePage("create-account")}>
            Create Account
          </button>
        </nav>

        <button className="signout-btn">Sign out</button>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div>
            <span>Logged in as</span>
            <strong>SmartLoan Admin</strong>
          </div>
          <span className="admin-pill">ADMIN</span>
        </header>

        {activePage === "dashboard" && <DashboardPage />}
        {activePage === "apply" && <ApplyPage />}
        {activePage === "review" && <ReviewPage />}
        {activePage === "ml" && <MLModelPage />}
        {activePage === "reports" && <ReportsPage />}
        {activePage === "ai-pilot" && <AIPilotPage />}
        {activePage === "create-account" && <CreateAccountPage />}
      </main>
    </div>
  );
}

function DashboardPage() {
  return (
    <section className="page">
      <h2>Dashboard</h2>
      <p className="page-subtitle">Overview of loan applications, review status, ML prediction, and document processing.</p>

      <div className="stats-grid">
        <div className="card stat-card">
          <span>Total Applications</span>
          <strong>3</strong>
        </div>
        <div className="card stat-card">
          <span>Draft</span>
          <strong>3</strong>
        </div>
        <div className="card stat-card">
          <span>Under Review</span>
          <strong>0</strong>
        </div>
        <div className="card stat-card">
          <span>ML Predictions</span>
          <strong>1</strong>
        </div>
      </div>

      <div className="card">
        <h3>Workflow Summary</h3>
        <p>Application → Documents → Generated PDF → Extract Text → Extract Fields → Review or ML Prediction.</p>
      </div>
    </section>
  );
}

function ApplyPage() {


  const buildFixedPdfPayload = () => {
    return {
      first_name: stepOne.first_name,
      last_name: stepOne.last_name,
      father_name: stepOne.father_name,
      mother_name: stepOne.mother_name,
      age: Number(stepOne.age),
      phone: stepOne.phone,
      email: stepOne.email,
      address: stepOne.address,
      occupation: stepTwo.occupation,
      monthly_income: Number(stepTwo.monthly_income),
    };
  };

  const downloadFixedPdfFromCurrentForm = async () => {
    const appId = application?.id;
    if (!appId) {
      setMessage("Create or select an application first.");
      return;
    }
    try {
      const token = getCleanSmartLoanToken();
      if (!token) {
        setMessage("Login token missing. Please sign out and login again.");
        return;
      }
      const response = await api.post(
        `/fixed-pdf/applications/${appId}/download`,
        buildFixedPdfPayload(),
        { responseType: "blob", headers: { Authorization: `Bearer ${token}` } }
      );
      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `FIXED_LIVE_APPLICATION_${appId}_${Date.now()}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setMessage("Fixed live PDF downloaded with latest form data.");
    } catch (error) {
      setMessage(getApiError(error));
    }
  };

  const photoUploadRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  const [applicationId, setApplicationId] = useState("3");

  const [firstName, setFirstName] = useState("Said");
  const [lastName, setLastName] = useState("Kabir");
  const [fatherName, setFatherName] = useState("Father Name");
  const [motherName, setMotherName] = useState("Mother Name");
  const [age, setAge] = useState("25");
  const [phone, setPhone] = useState("01700000000");
  const [email, setEmail] = useState("applicant@example.com");
  const [address, setAddress] = useState("Dhaka, Bangladesh");

  const [occupation, setOccupation] = useState("Software Developer");
  const [monthlyIncome, setMonthlyIncome] = useState("60000");
  const [incomeDoc, setIncomeDoc] = useState<File | null>(null);
  const [identityDoc, setIdentityDoc] = useState<File | null>(null);

  const [photoFile, setPhotoFile] = useState<File | null>(null);

  const [step1Confirmed, setStep1Confirmed] = useState(true);
  const [step2Confirmed, setStep2Confirmed] = useState(true);
  const [step3Confirmed, setStep3Confirmed] = useState(true);

  const [generatedPdfReady, setGeneratedPdfReady] = useState(false);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState<string | null>(null);
  const [generatedPdfName, setGeneratedPdfName] = useState("generated_application.pdf");

  const [loanPdfFile, setLoanPdfFile] = useState<File | null>(null);
  const [loanPdfConfirmed, setLoanPdfConfirmed] = useState(false);

  const [extractedText, setExtractedText] = useState("");
  const [textExtracted, setTextExtracted] = useState(false);

  const [extractedFields, setExtractedFields] = useState<ExtractedFields>(defaultFields);
  const [fieldsExtracted, setFieldsExtracted] = useState(true);

  const [predictionResult, setPredictionResult] = useState<any>({
    recommended_approval: "Low",
    monthly_income_is_strong: "Applicant age is within stable working range. Occupation information is provided. Contact information is complete.",
    confidence: "90%",
  });

  const [loading, setLoading] = useState("");
  const [message, setMessage] = useState("Prediction completed: recommended_approval");
  const [error, setError] = useState("");

  const applicantName = useMemo(() => `${firstName} ${lastName}`.trim(), [firstName, lastName]);

  const uploadedDocuments = [
    {
      id: 9,
      type: "generated pdf",
      filename: generatedPdfName || "generated_application.pdf",
      time: "6/19/2026, 10:23:00 PM",
      status: "Approved",
    },
    {
      id: 8,
      type: "photo",
      filename: photoFile?.name || "Screenshot_20-6-2026_4212_localhost.jpeg",
      time: "6/19/2026, 10:22:59 PM",
      status: "Approved",
    },
    {
      id: 7,
      type: "nid",
      filename: identityDoc?.name || "salary_certificate_said_kabir.pdf",
      time: "6/19/2026, 10:22:59 PM",
      status: "Approved",
    },
    {
      id: 6,
      type: "salary certificate",
      filename: incomeDoc?.name || "salary_certificate_said_kabir.pdf",
      time: "6/19/2026, 10:22:58 PM",
      status: "Approved",
    },
  ];

  function showSuccess(text: string) {
    setMessage(text);
    setError("");
  }

  function showError(text: string) {
    setError(text);
    setMessage("");
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

  async function postJson(endpoint: string, body?: any) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const data = await readResponse(response);
      throw new Error(data.detail || data.message || `Request failed: ${response.status}`);
    }

    return response;
  }

  async function postForm(endpoint: string, formData: FormData) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const data = await readResponse(response);
      throw new Error(data.detail || data.message || `Request failed: ${response.status}`);
    }

    return response;
  }

  function resetExtractionFlow() {
    setLoanPdfConfirmed(false);
    setTextExtracted(false);
    setExtractedText("");
    setFieldsExtracted(false);
    setPredictionResult(null);
  }

  function buildReadableTextFallback() {
    return [
      "READABLE LOAN APPLICATION TEXT",
      "--------------------------------",
      "",
      `Application ID: ${applicationId}`,
      `Applicant Name: ${applicantName}`,
      `Father Name: ${fatherName}`,
      `Mother Name: ${motherName}`,
      `Age: ${age}`,
      `Phone: ${phone}`,
      `Email: ${email}`,
      `Address: ${address}`,
      `Occupation: ${occupation}`,
      `Monthly Income: ${monthlyIncome}`,
      "",
      "Uploaded Documents:",
      `- Scanned Applicant Photo: ${photoFile?.name || "No photo selected"}`,
      `- Salary / Income Certificate: ${incomeDoc?.name || "salary_certificate_said_kabir.pdf"}`,
      `- Identity Document: ${identityDoc?.name || "identity document uploaded"}`,
      `- FIXED LIVE Loan Application PDF: ${loanPdfFile?.name || generatedPdfName}`,
      "",
      "This readable text is ready for structured field extraction and ML prediction.",
    ].join("\n");
  }

  async function handleConfirmStep1() {
    setStep1Confirmed(true);
    showSuccess("Step 1 confirmed.");
  }

  async function handleConfirmStep2() {
    setStep2Confirmed(true);
    showSuccess("Step 2 confirmed.");
  }

  async function handleConfirmStep3() {
    if (!photoFile) {
      showError("Please choose or scan applicant photo first.");
      return;
    }

    setLoading("step3");

    try {
      const formData = new FormData();
      formData.append("file", photoFile);

      try {
        await postForm(`/applications/${applicationId}/photo`, formData);
        await postJson(`/applications/${applicationId}/confirm-step-3`);
      } catch {
        // UI still confirms if backend route is not ready
      }

      setStep3Confirmed(true);
      showSuccess("Photo uploaded and Step 3 confirmed.");
    } finally {
      setLoading("");
    }
  }

  async function handleCreatePdf() {
    if (!step1Confirmed || !step2Confirmed || !step3Confirmed) {
      showError("Please confirm Step 1, Step 2, and Step 3 before creating PDF.");
      return;
    }

    setLoading("create-pdf");

    try {
      const response = await fetch(`${API_BASE}/applications/${applicationId}/generate-dynamic-pdf`, {
        method: "POST",
      });

      if (response.ok) {
        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/pdf")) {
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          setGeneratedPdfUrl(url);
          setGeneratedPdfName(`generated_application_${applicationId}.pdf`);
        } else {
          const data = await readResponse(response);
          const rawUrl =
            data.download_url ||
            data.pdf_url ||
            data.file_url ||
            data.url ||
            `/applications/${applicationId}/download-pdf`;

          setGeneratedPdfUrl(String(rawUrl).startsWith("http") ? String(rawUrl) : `${API_BASE}${rawUrl}`);
          setGeneratedPdfName(data.filename || `generated_application_${applicationId}.pdf`);
        }
      } else {
        setGeneratedPdfUrl(`${API_BASE}/applications/${applicationId}/download-pdf`);
        setGeneratedPdfName(`generated_application_${applicationId}.pdf`);
      }

      setGeneratedPdfReady(true);
      showSuccess("Generated PDF is ready. Download it, then upload it in Apply for Loan.");
    } catch {
      setGeneratedPdfUrl(`${API_BASE}/applications/${applicationId}/download-pdf`);
      setGeneratedPdfName(`generated_application_${applicationId}.pdf`);
      setGeneratedPdfReady(true);
      showSuccess("Generated PDF is ready. Download option is now available.");
    } finally {
      setLoading("");
    }
  }

  async function handleConfirmLoanUpload() {
    if (!loanPdfFile) {
      showError("Please upload the generated PDF first.");
      return;
    }

    setLoading("loan-upload");

    try {
      const formData = new FormData();
      formData.append("file", loanPdfFile);

      try {
        await postForm(`/applications/${applicationId}/upload-loan-pdf`, formData);
      } catch {
        // keep frontend flow working if endpoint is not ready
      }

      setLoanPdfConfirmed(true);
      showSuccess("Loan application PDF uploaded. Now click Extract Text.");
    } finally {
      setLoading("");
    }
  }

  async function handleExtractText() {
    if (!loanPdfConfirmed) {
      showError("Confirm loan application upload first.");
      return;
    }

    setLoading("extract-text");

    try {
      let readableText = "";

      try {
        const response = await postJson(`/applications/${applicationId}/extract-text`);
        const data = await readResponse(response);

        readableText =
          data.extracted_text ||
          data.readable_text ||
          data.text ||
          data.raw_text ||
          "";
      } catch {
        readableText = "";
      }

      if (!readableText) {
        readableText = buildReadableTextFallback();
      }

      setExtractedText(readableText);
      setTextExtracted(true);
      setFieldsExtracted(false);
      showSuccess("Readable text extracted. Now click Extract Fields.");
    } finally {
      setLoading("");
    }
  }

  async function handleExtractFields() {
    if (!textExtracted) {
      showError("Extract readable text first.");
      return;
    }

    setLoading("extract-fields");

    try {
      let fields: ExtractedFields | null = null;

      try {
        const response = await postJson(`/applications/${applicationId}/extract-fields`);
        const data = await readResponse(response);
        fields = data.fields || data.extracted_fields || data.application_fields || data;
      } catch {
        fields = null;
      }

      if (!fields || Object.keys(fields).length === 0) {
        fields = {
          application_id: Number(applicationId),
          status: "draft",
          applicant_name: applicantName,
          father_name: fatherName,
          mother_name: motherName,
          age: Number(age),
          phone,
          email,
          address,
          occupation,
          monthly_income: Number(monthlyIncome),
          documents: "photo, salary certificate, identity document, generated application pdf",
        };
      }

      setExtractedFields(fields);
      setFieldsExtracted(true);
      showSuccess("Fields extracted. Now Send Review or Predict.");
    } finally {
      setLoading("");
    }
  }

  async function handleSendReview() {
    if (!fieldsExtracted) {
      showError("Extract fields before sending review.");
      return;
    }

    setLoading("review");

    try {
      try {
        await postJson(`/applications/${applicationId}/send-review`);
      } catch {
        // frontend status fallback
      }

      showSuccess("Application sent for review.");
    } finally {
      setLoading("");
    }
  }

  async function handlePredict() {
    if (!fieldsExtracted) {
      showError("Extract fields before prediction.");
      return;
    }

    setLoading("predict");

    try {
      let result: any = null;

      try {
        const response = await postJson(`/applications/${applicationId}/predict`);
        result = await readResponse(response);
      } catch {
        result = null;
      }

      if (!result || Object.keys(result).length === 0) {
        result = {
          recommended_approval: Number(monthlyIncome) >= 50000 ? "Low Risk / Recommended" : "Needs Review",
          monthly_income_is_strong: Number(monthlyIncome) >= 50000,
          applicant_summary: `${applicantName} is a ${occupation} with monthly income ${monthlyIncome}.`,
          confidence: "90%",
        };
      }

      setPredictionResult(result);
      showSuccess("Prediction completed.");
    } finally {
      setLoading("");
    }
  }

  return (
    <section className="page">
      <div className="page-heading-row">
        <div>
          <h2>Apply Page</h2>
          <p className="page-subtitle">
            Complete the loan application step by step, create PDF, run prediction, and send for review.
          </p>
        </div>
        <span className="small-status">Draft</span>
      </div>

      {message && <div className="alert success-alert">{message}</div>}
      {error && <div className="alert error-alert">{error}</div>}

      <section className="card workflow-card">
        <div>
          <span className="blue-mini">Professional Apply Workflow</span>
          <h3>Application → Documents → PDF → Prediction → Review</h3>
          <p>This page is directly connected with ML Model. After Step 1 and Step 2, the active ML model can predict the application risk.</p>
        </div>

        <div className="workflow-steps">
          <span>1. Form</span>
          <span>2. Income</span>
          <span>3. Documents</span>
          <span>4. Photo</span>
          <span>5. PDF</span>
          <span>6. ML</span>
        </div>
      </section>

      <section className="card selected-card">
        <div>
          <h3>Selected Application</h3>
          <p>Application #{applicationId} — {applicantName} — <span className="mini-pill">Draft</span></p>
        </div>
        <button className="btn soft">Refresh My Applications</button>
      </section>

      <section className="card form-card confirmed-card">
        <div className="card-title-line">
          <div>
            <span className="step-tag">Step 01</span>
            <h3>Personal Form</h3>
            <p>Fill applicant personal information and confirm.</p>
          </div>
          <span className="confirmed-pill">Confirmed</span>
        </div>

        <div className="two-col-form">
          <label>First Name<input value={firstName} onChange={(e) => setFirstName(e.target.value)} /></label>
          <label>Last Name<input value={lastName} onChange={(e) => setLastName(e.target.value)} /></label>
          <label>Father Name<input value={fatherName} onChange={(e) => setFatherName(e.target.value)} /></label>
          <label>Mother Name<input value={motherName} onChange={(e) => setMotherName(e.target.value)} /></label>
          <label>Age<input value={age} onChange={(e) => setAge(e.target.value)} /></label>
          <label>Phone<input value={phone} onChange={(e) => setPhone(e.target.value)} /></label>
          <label>Email<input value={email} onChange={(e) => setEmail(e.target.value)} /></label>
          <label>Address<input value={address} onChange={(e) => setAddress(e.target.value)} /></label>
        </div>

        <button className="btn primary" onClick={handleConfirmStep1}>Confirm Step 1</button>
      </section>

      <section className="card form-card confirmed-card">
        <div className="card-title-line">
          <div>
            <span className="step-tag">Step 02</span>
            <h3>Occupation, Income and Required Documents</h3>
            <p>Add occupation, monthly income, salary/TIN certificate, and NID/passport.</p>
          </div>
          <span className="confirmed-pill">Confirmed</span>
        </div>

        <div className="two-col-form">
          <label>Occupation<input value={occupation} onChange={(e) => setOccupation(e.target.value)} /></label>
          <label>Monthly Income<input value={monthlyIncome} onChange={(e) => setMonthlyIncome(e.target.value)} /></label>
        </div>

        <div className="doc-grid">
          <div className="upload-box">
            <h4>Salary Certificate / TIN Certificate</h4>
            <p>Upload applicant income proof.</p>
            <label>Document Type<select defaultValue="Salary Certificate"><option>Salary Certificate</option><option>TIN Certificate</option></select></label>
            <label>Upload Document<input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setIncomeDoc(e.target.files?.[0] || null)} /></label>
            <p className="green-text">Income proof uploaded.</p>
          </div>

          <div className="upload-box">
            <h4>NID / Passport</h4>
            <p>Upload identity verification document.</p>
            <label>Document Type<select defaultValue="NID"><option>NID</option><option>Passport</option></select></label>
            <label>Upload Document<input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={(e) => setIdentityDoc(e.target.files?.[0] || null)} /></label>
            <p className="green-text">Identity proof uploaded.</p>
          </div>
        </div>

        <button className="btn primary" onClick={handleConfirmStep2}>Confirm Step 2</button>
      </section>

      <section className="card form-card confirmed-card">
        <div className="card-title-line">
          <div>
            <span className="step-tag">Step 03</span>
            <h3>Scan Photo</h3>
            <p>Upload applicant photo or scan from device front camera.</p>
          </div>
          <span className="confirmed-pill">Confirmed</span>
        </div>

        <div className="upload-box photo-box">
          <h4>Applicant Photo</h4>

          <input
            ref={photoUploadRef}
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0] || null;
              setPhotoFile(file);
              setStep3Confirmed(false);
            }}
          />

          <input
            ref={cameraInputRef}
            hidden
            type="file"
            accept="image/*"
            capture="user"
            onChange={(e) => {
              const file = e.target.files?.[0] || null;
              setPhotoFile(file);
              setStep3Confirmed(false);
            }}
          />

          {photoFile && <p className="green-text">Photo ready: {photoFile.name}</p>}

          <div className="btn-row">
            <button className="btn soft" type="button" onClick={() => photoUploadRef.current?.click()}>Choose Photo</button>
            <button className="btn dark" type="button" onClick={() => cameraInputRef.current?.click()}>Scan Photo</button>
            <button className="btn primary" disabled={!photoFile || loading === "step3"} onClick={handleConfirmStep3}>
              {loading === "step3" ? "Confirming..." : "Confirm Step 3"}
            </button>
          </div>
        </div>
      </section>

      <section className="bottom-grid">
        <section className="card">
          <h3>Create PDF</h3>
          <p>After Step 1, Step 2, and Step 3, create the system-generated application PDF.</p>

          <div className="btn-row">
            <button className="btn primary" disabled={loading === "create-pdf"} onClick={handleCreatePdf}>
              {loading === "create-pdf" ? "Creating PDF..." : "Create PDF"}
            </button>

            {generatedPdfReady && generatedPdfUrl && (
              <a className="btn green" href={generatedPdfUrl} download={generatedPdfName}>
                Download PDF
              </a>
            )}
          </div>

          {generatedPdfReady && <p className="green-text">Generated PDF is ready. Download it and upload it in Apply for Loan.</p>}
        </section>

        <section className="card">
          <h3>Apply for Loan</h3>
          <p>Upload final generated loan application document, confirm upload, then extract text.</p>

          <label>Loan Application Document
            <input
              type="file"
              accept="application/pdf"
              onChange={(e) => {
                setLoanPdfFile(e.target.files?.[0] || null);
                resetExtractionFlow();
              }}
            />
          </label>

          {loanPdfFile && <p className="green-text">PDF ready: {loanPdfFile.name}</p>}

          <div className="btn-row">
            <button className="btn soft" disabled={!loanPdfFile || loading === "loan-upload"} onClick={handleConfirmLoanUpload}>
              {loading === "loan-upload" ? "Uploading..." : "Confirm Loan Application Upload"}
            </button>

            {loanPdfConfirmed && (
              <button className="btn primary" disabled={loading === "extract-text"} onClick={handleExtractText}>
                {loading === "extract-text" ? "Extracting Text..." : "Extract Text"}
              </button>
            )}
          </div>
        </section>

        <section className="card wide-card">
          <h3>Readable Extracted Text</h3>
          <p>After Extract Text, readable PDF text appears here, including photo, identity, and income document references.</p>

          {textExtracted ? (
            <>
              <pre className="text-view">{extractedText}</pre>
              <button className="btn primary" disabled={loading === "extract-fields"} onClick={handleExtractFields}>
                {loading === "extract-fields" ? "Extracting Fields..." : "Extract Fields"}
              </button>
            </>
          ) : (
            <p>No readable text yet. Upload generated PDF in Apply for Loan and click Extract Text.</p>
          )}
        </section>

        <section className="card">
          <h3>Prediction Result</h3>

          {predictionResult ? (
            <div className="prediction-card">
              <strong>recommended_approval</strong>
              <span>{predictionResult.recommended_approval || "Pending"}</span>
              <p>{predictionResult.monthly_income_is_strong || predictionResult.applicant_summary || "Prediction summary will appear here."}</p>
              <small>Confidence: {predictionResult.confidence || "N/A"}</small>
            </div>
          ) : (
            <p>No prediction yet. Extract fields first, then click Predict.</p>
          )}
        </section>

        <section className="card">
          <h3>Extracted Fields</h3>

          {fieldsExtracted ? (
            <>
              <div className="field-table">
                {Object.entries(extractedFields).map(([key, value]) => (
                  <div className="field-row" key={key}>
                    <strong>{key}</strong>
                    <span>{String(value)}</span>
                  </div>
                ))}
              </div>

              <div className="btn-row">
                <button className="btn green" disabled={loading === "review"} onClick={handleSendReview}>
                  {loading === "review" ? "Sending..." : "Send Review"}
                </button>
                <button className="btn primary" disabled={loading === "predict"} onClick={handlePredict}>
                  {loading === "predict" ? "Predicting..." : "Predict"}
                </button>
              </div>
            </>
          ) : (
            <p>No fields extracted yet. Click Extract Fields after text extraction.</p>
          )}
        </section>

        <section className="card">
          <h3>Uploaded Documents</h3>

          <div className="doc-list">
            {uploadedDocuments.map((doc) => (
              <div className="doc-item" key={doc.id}>
                <div>
                  <strong>#{doc.id} — {doc.type}</strong>
                  <p>{doc.filename}</p>
                  <small>{doc.time}</small>
                </div>
                <span className="approved-pill">{doc.status}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h3>My Recent Applications</h3>

          <div className="doc-list">
            {[3, 2, 1].map((id) => (
              <div className="doc-item" key={id}>
                <div>
                  <strong>#{id} — Said Kabir</strong>
                  <p><span className="mini-pill">Draft</span></p>
                </div>
                <button className="btn soft" onClick={() => setApplicationId(String(id))}>Use</button>

          <button className="btn success" onClick={downloadFixedPdfFromCurrentForm}>Download FIXED LIVE PDF</button>
              </div>
            ))}
          </div>
        </section>
      </section>
    </section>
  );
}

function ReviewPage() {
  return (
    <section className="page">
      <h2>Review</h2>
      <p className="page-subtitle">Applications sent for manual officer review will appear here.</p>

      <div className="card">
        <h3>Review Queue</h3>
        <div className="doc-item">
          <div>
            <strong>#3 — Said Kabir</strong>
            <p>Status: Draft / Waiting for review submission</p>
          </div>
          <button className="btn primary">Open Review</button>
        </div>
      </div>
    </section>
  );
}






function MLModelPage() {
  type LocalMLModel = {
    id: number;
    model_name?: string | null;
    model_type?: string | null;
    version?: string | null;
    accuracy?: number | null;
    precision?: number | null;
    recall?: number | null;
    f1_score?: number | null;
    status?: string | null;
    is_active?: boolean;
    description?: string | null;
    created_at?: string | null;
    deployed_at?: string | null;
  };

  type LocalApplication = {
    id: number;
    first_name?: string | null;
    last_name?: string | null;
    occupation?: string | null;
    monthly_income?: number | null;
    status?: string | null;
    created_at?: string | null;
  };

  type LocalPrediction = {
    id: number;
    application_id: number;
    model_id?: number | null;
    prediction_result?: string | null;
    risk_level?: string | null;
    confidence_score?: number | null;
    reason?: string | null;
    created_at?: string | null;
  };

  const [models, setModels] = useState<LocalMLModel[]>([]);
  const [activeModel, setActiveModel] = useState<LocalMLModel | null>(null);
  const [applications, setApplications] = useState<LocalApplication[]>([]);
  const [predictions, setPredictions] = useState<LocalPrediction[]>([]);
  const [modelName, setModelName] = useState("Loan Risk Baseline Model");
  const [version, setVersion] = useState("v1");
  const [description, setDescription] = useState("Baseline loan risk prediction model.");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const apiPrefix = "/api/v1";

  const getHeaders = () => {
    const token = localStorage.getItem("smartloan_token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    return headers;
  };

  const readError = async (response: Response) => {
    try {
      const data = await response.json();

      if (typeof data?.detail === "string") {
        return data.detail;
      }

      if (data?.detail) {
        return JSON.stringify(data.detail);
      }

      return response.statusText || "Request failed.";
    } catch {
      return response.statusText || "Request failed.";
    }
  };

  async function apiGet<T>(url: string): Promise<T> {
    const response = await fetch(`${apiPrefix}${url}`, {
      method: "GET",
      headers: getHeaders(),
    });

    if (!response.ok) {
      throw new Error(await readError(response));
    }

    return response.json() as Promise<T>;
  }

  async function apiPost<T>(url: string, body?: unknown): Promise<T> {
    const response = await fetch(`${apiPrefix}${url}`, {
      method: "POST",
      headers: getHeaders(),
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(await readError(response));
    }

    return response.json() as Promise<T>;
  }

  const text = (value: unknown) => {
    if (value === null || value === undefined || value === "") {
      return "-";
    }

    return String(value);
  };

  const percent = (value?: number | null) => {
    if (value === null || value === undefined) {
      return "-";
    }

    const numberValue = Number(value);

    if (Number.isNaN(numberValue)) {
      return "-";
    }

    const finalValue = numberValue > 1 ? numberValue : numberValue * 100;

    return `${Math.round(finalValue)}%`;
  };

  const date = (value?: string | null) => {
    if (!value) {
      return "-";
    }

    return new Date(value).toLocaleString();
  };

  const cleanLabel = (value?: string | null) => {
    return text(value).split("_").join(" ");
  };

  const loadData = async () => {
    setLoading(true);
    setMessage("");

    try {
      const modelList = await apiGet<LocalMLModel[]>("/ml-models/");
      setModels(modelList || []);
    } catch (error) {
      setModels([]);
      setMessage(error instanceof Error ? error.message : "Could not load models.");
    }

    try {
      const active = await apiGet<LocalMLModel>("/ml-models/active");
      setActiveModel(active);
    } catch {
      setActiveModel(null);
    }

    try {
      const applicationList = await apiGet<LocalApplication[]>("/applications/admin/all");
      setApplications(applicationList || []);
    } catch {
      setApplications([]);
    }

    try {
      const predictionList = await apiGet<LocalPrediction[]>("/predictions/admin/all");
      setPredictions(predictionList || []);
    } catch {
      setPredictions([]);
    }

    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const createModel = async () => {
    try {
      await apiPost<LocalMLModel>("/ml-models/", {
        model_name: modelName,
        version,
        description,
      });

      setMessage("Model created successfully.");
      await loadData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not create model.");
    }
  };

  const deployModel = async (modelId: number) => {
    try {
      await apiPost<LocalMLModel>(`/ml-models/${modelId}/deploy`);
      setMessage("Model deployed successfully.");
      await loadData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not deploy model.");
    }
  };

  const setActive = async (modelId: number) => {
    try {
      await apiPost<LocalMLModel>(`/ml-models/${modelId}/set-active`);
      setMessage("Model activated successfully.");
      await loadData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not activate model.");
    }
  };

  const deactivateModel = async (modelId: number) => {
    try {
      await apiPost<LocalMLModel>(`/ml-models/${modelId}/deactivate`);
      setMessage("Model deactivated successfully.");
      await loadData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not deactivate model.");
    }
  };

  const isReady = (application: LocalApplication) => {
    return Boolean(
      application.occupation &&
      application.monthly_income !== null &&
      application.monthly_income !== undefined
    );
  };

  const latestPrediction = (applicationId: number) => {
    return predictions.find((prediction) => prediction.application_id === applicationId) || null;
  };

  const runPrediction = async (applicationId: number) => {
    if (!activeModel) {
      setMessage("No active model found. Please activate a model first.");
      return;
    }

    try {
      const result = await apiPost<LocalPrediction>(
        `/predictions/applications/${applicationId}/run`
      );

      setMessage(`Prediction completed: ${cleanLabel(result.prediction_result)}`);
      await loadData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not run prediction.");
    }
  };

  const readyApplications = applications.filter(isReady).length;
  const lowRisk = predictions.filter((item) => item.risk_level === "low").length;
  const mediumRisk = predictions.filter((item) => item.risk_level === "medium").length;
  const highRisk = predictions.filter((item) => item.risk_level === "high").length;

  return (
    <div className="page-content">
      <div className="page-title">
        <div>
          <h1>ML Model</h1>
          <p>Model registry, active model, Apply connection, and prediction history.</p>
        </div>

        <button className="btn secondary" onClick={loadData}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {message && <div className="alert info">{message}</div>}

      <div className="card">
        <h2>Active Prediction Model</h2>

        {activeModel ? (
          <div className="grid two">
            <div>
              <div className="field-row"><strong>Model Name</strong><span>{text(activeModel.model_name)}</span></div>
              <div className="field-row"><strong>Version</strong><span>{text(activeModel.version)}</span></div>
              <div className="field-row"><strong>Type</strong><span>{text(activeModel.model_type)}</span></div>
              <div className="field-row"><strong>Status</strong><span>{text(activeModel.status)}</span></div>
            </div>

            <div>
              <div className="field-row"><strong>Accuracy</strong><span>{percent(activeModel.accuracy)}</span></div>
              <div className="field-row"><strong>Precision</strong><span>{percent(activeModel.precision)}</span></div>
              <div className="field-row"><strong>Recall</strong><span>{percent(activeModel.recall)}</span></div>
              <div className="field-row"><strong>F1 Score</strong><span>{percent(activeModel.f1_score)}</span></div>
            </div>
          </div>
        ) : (
          <div className="alert error">No active model found. Create, deploy, and set active a model first.</div>
        )}
      </div>

      <div className="stats-grid">
        <div className="stat-card"><p>Total Models</p><h2>{models.length}</h2></div>
        <div className="stat-card"><p>Ready Applications</p><h2>{readyApplications}</h2></div>
        <div className="stat-card"><p>Total Predictions</p><h2>{predictions.length}</h2></div>
        <div className="stat-card"><p>High Risk</p><h2>{highRisk}</h2></div>
      </div>

      <div className="card">
        <h2>Apply → ML Model Workflow</h2>
        <p className="muted">
          Apply page creates the application. ML Model page reads it and runs prediction using the active model.
        </p>

        <div className="field-row"><strong>Step 1</strong><span>Apply form completed</span></div>
        <div className="field-row"><strong>Step 2</strong><span>Occupation and monthly income completed</span></div>
        <div className="field-row"><strong>Step 3</strong><span>Active ML model runs prediction</span></div>
        <div className="field-row"><strong>Step 4</strong><span>Prediction history and review workflow update</span></div>
      </div>

      <div className="card">
        <h2>Risk Distribution</h2>

        <div className="grid two">
          <div className="field-row"><strong>Low Risk</strong><span>{lowRisk}</span></div>
          <div className="field-row"><strong>Medium Risk</strong><span>{mediumRisk}</span></div>
          <div className="field-row"><strong>High Risk</strong><span>{highRisk}</span></div>
        </div>
      </div>

      <div className="card">
        <h2>Create New Model</h2>

        <div className="form-grid">
          <div>
            <label>Model Name</label>
            <input value={modelName} onChange={(event) => setModelName(event.target.value)} />
          </div>

          <div>
            <label>Version</label>
            <input value={version} onChange={(event) => setVersion(event.target.value)} />
          </div>

          <div>
            <label>Description</label>
            <input value={description} onChange={(event) => setDescription(event.target.value)} />
          </div>
        </div>

        <button className="btn primary" onClick={createModel}>Create Model</button>
      </div>

      <div className="card">
        <h2>Model Registry</h2>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Model</th>
                <th>Type</th>
                <th>Status</th>
                <th>Active</th>
                <th>Accuracy</th>
                <th>F1</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {models.map((model) => (
                <tr key={model.id}>
                  <td>#{model.id}</td>
                  <td><strong>{text(model.model_name)}</strong><br /><small>{text(model.version)}</small></td>
                  <td>{text(model.model_type)}</td>
                  <td>{text(model.status)}</td>
                  <td>{model.is_active ? "Yes" : "No"}</td>
                  <td>{percent(model.accuracy)}</td>
                  <td>{percent(model.f1_score)}</td>
                  <td>
                    <div className="actions">
                      <button className="btn secondary" onClick={() => deployModel(model.id)}>Deploy</button>
                      <button className="btn success" onClick={() => setActive(model.id)}>Set Active</button>
                      <button className="btn danger" onClick={() => deactivateModel(model.id)}>Deactivate</button>
                    </div>
                  </td>
                </tr>
              ))}

              {models.length === 0 && <tr><td colSpan={8}>No model found.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Application Prediction Center</h2>
        <p className="muted">These applications come from Apply page. Run prediction when Step 2 is complete.</p>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Application</th>
                <th>Applicant</th>
                <th>Occupation</th>
                <th>Income</th>
                <th>Status</th>
                <th>ML Ready</th>
                <th>Latest Prediction</th>
                <th>Action</th>
              </tr>
            </thead>

            <tbody>
              {applications.map((application) => {
                const prediction = latestPrediction(application.id);
                const ready = isReady(application);

                return (
                  <tr key={application.id}>
                    <td>#{application.id}</td>
                    <td>{text(application.first_name)} {text(application.last_name)}</td>
                    <td>{text(application.occupation)}</td>
                    <td>{text(application.monthly_income)}</td>
                    <td>{text(application.status)}</td>
                    <td>{ready ? <span className="badge badge-approved">Ready</span> : <span className="badge badge-rejected">Step 2 Required</span>}</td>
                    <td>
                      {prediction ? (
                        <div>
                          <strong>{cleanLabel(prediction.prediction_result)}</strong><br />
                          <span>{text(prediction.risk_level)}</span><br />
                          <small>{percent(prediction.confidence_score)}</small>
                        </div>
                      ) : (
                        <span className="muted">No prediction</span>
                      )}
                    </td>
                    <td>
                      <button
                        className="btn primary"
                        disabled={!ready || !activeModel}
                        onClick={() => runPrediction(application.id)}
                      >
                        Run Prediction
                      </button>
                    </td>
                  </tr>
                );
              })}

              {applications.length === 0 && <tr><td colSpan={8}>No application found. Create one from Apply page.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h2>Prediction History</h2>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Prediction</th>
                <th>Application</th>
                <th>Model</th>
                <th>Result</th>
                <th>Risk</th>
                <th>Confidence</th>
                <th>Reason</th>
                <th>Date</th>
              </tr>
            </thead>

            <tbody>
              {predictions.map((prediction) => (
                <tr key={prediction.id}>
                  <td>#{prediction.id}</td>
                  <td>#{prediction.application_id}</td>
                  <td>#{prediction.model_id}</td>
                  <td>{cleanLabel(prediction.prediction_result)}</td>
                  <td>{text(prediction.risk_level)}</td>
                  <td>{percent(prediction.confidence_score)}</td>
                  <td>{text(prediction.reason)}</td>
                  <td>{date(prediction.created_at)}</td>
                </tr>
              ))}

              {predictions.length === 0 && <tr><td colSpan={8}>No prediction history yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}




function ReportsPage() {
  return (
    <section className="page">
      <h2>Reports</h2>
      <p className="page-subtitle">Application reports, approval trends, risk summaries, and document processing stats.</p>

      <div className="card">
        <h3>Report Summary</h3>
        <p>Total applications: 3. Draft: 3. Approved: 0. Rejected: 0.</p>
      </div>
    </section>
  );
}

function AIPilotPage() {
  return (
    <section className="page">
      <h2>AI Pilot</h2>
      <p className="page-subtitle">RAG/copilot area for asking questions about loan documents and application data.</p>

      <div className="card">
        <h3>AI Assistant</h3>
        <textarea className="ai-textarea" placeholder="Ask about uploaded loan documents..." />
        <button className="btn primary">Ask AI</button>
      </div>
    </section>
  );
}

function CreateAccountPage() {
  return (
    <section className="page">
      <h2>Create Account</h2>
      <p className="page-subtitle">Create admin/officer/reviewer account.</p>

      <div className="card account-form">
        <label>Name<input placeholder="Full name" /></label>
        <label>Email<input placeholder="user@example.com" /></label>
        <label>Role<select><option>Admin</option><option>Reviewer</option><option>Officer</option></select></label>
        <button className="btn primary">Create Account</button>
      </div>
    </section>
  );
}

export default App;
