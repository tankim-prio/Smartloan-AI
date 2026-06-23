import React, { useRef, useState } from "react";
import "./FixedLoanWorkflow.css";

type ExtractedFields = Record<string, string | number | boolean | null>;

const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

export default function FixedLoanWorkflow() {
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const normalPhotoInputRef = useRef<HTMLInputElement | null>(null);

  const [applicationId, setApplicationId] = useState("2");

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoConfirmed, setPhotoConfirmed] = useState(false);

  const [generatedPdfReady, setGeneratedPdfReady] = useState(false);
  const [generatedPdfUrl, setGeneratedPdfUrl] = useState<string | null>(null);
  const [generatedPdfName, setGeneratedPdfName] = useState("loan_application.pdf");

  const [loanPdfFile, setLoanPdfFile] = useState<File | null>(null);
  const [loanPdfConfirmed, setLoanPdfConfirmed] = useState(false);

  const [extractedText, setExtractedText] = useState("");
  const [textExtracted, setTextExtracted] = useState(false);

  const [extractedFields, setExtractedFields] = useState<ExtractedFields | null>(null);
  const [fieldsExtracted, setFieldsExtracted] = useState(false);

  const [predictionResult, setPredictionResult] = useState<any>(null);

  const [loading, setLoading] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  function showSuccess(message: string) {
    setSuccessMessage(message);
    setErrorMessage("");
  }

  function showError(message: string) {
    setErrorMessage(message);
    setSuccessMessage("");
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
      headers: {
        "Content-Type": "application/json",
      },
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

  function resetLoanExtraction() {
    setLoanPdfConfirmed(false);
    setTextExtracted(false);
    setExtractedText("");
    setFieldsExtracted(false);
    setExtractedFields(null);
    setPredictionResult(null);
  }

  async function handleConfirmPhoto() {
    if (!photoFile) {
      showError("Please choose or scan applicant photo first.");
      return;
    }

    setLoading("photo");

    try {
      const formData = new FormData();
      formData.append("file", photoFile);

      await postForm(`/applications/${applicationId}/photo`, formData);
      await postJson(`/applications/${applicationId}/confirm-step-3`);

      setPhotoConfirmed(true);
      showSuccess("Photo uploaded and Step 3 confirmed.");
    } catch (error: any) {
      showError(error.message || "Photo upload failed.");
    } finally {
      setLoading("");
    }
  }

  async function handleCreatePdf() {
    if (!photoConfirmed) {
      showError("Please confirm Step 3 before creating PDF.");
      return;
    }

    setLoading("create-pdf");

    try {
      const response = await fetch(`${API_BASE}/applications/${applicationId}/generate-pdf`, {
        method: "POST",
      });

      if (!response.ok) {
        const data = await readResponse(response);
        throw new Error(data.detail || data.message || `PDF creation failed: ${response.status}`);
      }

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

        const finalUrl = rawUrl.startsWith("http") ? rawUrl : `${API_BASE}${rawUrl}`;

        setGeneratedPdfUrl(finalUrl);
        setGeneratedPdfName(data.filename || `generated_application_${applicationId}.pdf`);
      }

      setGeneratedPdfReady(true);
      showSuccess("Generated PDF is ready. Click Download PDF, then upload it inside Apply for Loan.");
    } catch (error: any) {
      showError(error.message || "PDF creation failed.");
    } finally {
      setLoading("");
    }
  }

  async function handleConfirmLoanPdfUpload() {
    if (!loanPdfFile) {
      showError("Please upload the generated PDF first.");
      return;
    }

    setLoading("loan-upload");

    try {
      const formData = new FormData();
      formData.append("file", loanPdfFile);

      await postForm(`/applications/${applicationId}/upload-loan-pdf`, formData);

      setLoanPdfConfirmed(true);
      showSuccess("Loan PDF uploaded. Now click Extract Text.");
    } catch (error: any) {
      showError(error.message || "Loan PDF upload failed.");
    } finally {
      setLoading("");
    }
  }

  async function handleExtractText() {
    if (!loanPdfConfirmed) {
      showError("Please confirm loan application upload first.");
      return;
    }

    setLoading("extract-text");

    try {
      const response = await postJson(`/applications/${applicationId}/extract-text`);
      const data = await readResponse(response);

      const text =
        data.extracted_text ||
        data.readable_text ||
        data.text ||
        data.raw_text ||
        JSON.stringify(data, null, 2);

      setExtractedText(String(text));
      setTextExtracted(true);
      setFieldsExtracted(false);
      setExtractedFields(null);
      setPredictionResult(null);

      showSuccess("Readable text extracted. Now click Extract Fields.");
    } catch (error: any) {
      showError(error.message || "Text extraction failed.");
    } finally {
      setLoading("");
    }
  }

  async function handleExtractFields() {
    if (!textExtracted) {
      showError("Please extract readable text first.");
      return;
    }

    setLoading("extract-fields");

    try {
      const response = await postJson(`/applications/${applicationId}/extract-fields`);
      const data = await readResponse(response);

      const fields =
        data.fields ||
        data.extracted_fields ||
        data.application_fields ||
        data;

      setExtractedFields(fields);
      setFieldsExtracted(true);

      showSuccess("Fields extracted. Now Send Review or Predict.");
    } catch (error: any) {
      showError(error.message || "Field extraction failed.");
    } finally {
      setLoading("");
    }
  }

  async function handleSendReview() {
    if (!fieldsExtracted) {
      showError("Please extract fields before sending review.");
      return;
    }

    setLoading("send-review");

    try {
      await postJson(`/applications/${applicationId}/send-review`);
      showSuccess("Application sent for review.");
    } catch (error: any) {
      showError(error.message || "Send review failed.");
    } finally {
      setLoading("");
    }
  }

  async function handlePredict() {
    if (!fieldsExtracted) {
      showError("Please extract fields before prediction.");
      return;
    }

    setLoading("predict");

    try {
      const response = await postJson(`/applications/${applicationId}/predict`);
      const data = await readResponse(response);

      setPredictionResult(data);
      showSuccess("Prediction completed.");
    } catch (error: any) {
      showError(error.message || "Prediction failed.");
    } finally {
      setLoading("");
    }
  }

  return (
    <section className="fixed-loan-workflow">
      <div className="flw-header">
        <div>
          <span className="flw-badge">Fixed Apply + ML Workflow</span>
          <h2>Photo Scan → PDF Download → Text Extraction → Field Extraction → Review / Predict</h2>
          <p>
            This block is added without removing your existing dashboard, uploaded documents, recent applications, sidebar, navbar, or other pages.
          </p>
        </div>

        <label className="flw-app-id">
          Application ID
          <input
            value={applicationId}
            onChange={(event) => setApplicationId(event.target.value)}
          />
        </label>
      </div>

      {(successMessage || errorMessage) && (
        <div className="flw-message-area">
          {successMessage && <div className="flw-success">{successMessage}</div>}
          {errorMessage && <div className="flw-error">{errorMessage}</div>}
        </div>
      )}

      <div className="flw-grid">
        <div className="flw-card flw-wide">
          <div className="flw-card-head">
            <div>
              <span className="flw-step">Step 03</span>
              <h3>Scan Photo</h3>
              <p>Use normal upload or Scan Photo. On mobile browser, Scan Photo will prefer the front camera.</p>
            </div>

            <span className={photoConfirmed ? "flw-status done" : "flw-status"}>
              {photoConfirmed ? "Confirmed" : "Pending"}
            </span>
          </div>

          <div className="flw-upload-box">
            <strong>Applicant Photo</strong>

            <input
              ref={normalPhotoInputRef}
              type="file"
              accept="image/*"
              onChange={(event) => {
                const file = event.target.files?.[0];

                if (file) {
                  setPhotoFile(file);
                  setPhotoConfirmed(false);
                  showSuccess("Photo selected. Click Confirm Step 3.");
                }
              }}
            />

            <input
              ref={cameraInputRef}
              hidden
              type="file"
              accept="image/*"
              capture="user"
              onChange={(event) => {
                const file = event.target.files?.[0];

                if (file) {
                  setPhotoFile(file);
                  setPhotoConfirmed(false);
                  showSuccess("Camera photo captured. Click Confirm Step 3.");
                }
              }}
            />

            {photoFile && <p className="flw-file-ready">Photo ready: {photoFile.name}</p>}

            <div className="flw-actions">
              <button
                type="button"
                className="flw-btn muted"
                onClick={() => normalPhotoInputRef.current?.click()}
              >
                Choose Photo
              </button>

              <button
                type="button"
                className="flw-btn dark"
                onClick={() => cameraInputRef.current?.click()}
              >
                Scan Photo
              </button>

              <button
                type="button"
                className="flw-btn primary"
                disabled={!photoFile || loading === "photo"}
                onClick={handleConfirmPhoto}
              >
                {loading === "photo" ? "Confirming..." : "Confirm Step 3"}
              </button>
            </div>
          </div>
        </div>

        <div className="flw-card">
          <div className="flw-card-head">
            <div>
              <h3>Create PDF</h3>
              <p>Create the final system-generated PDF. This section gives download only.</p>
            </div>

            <span className={generatedPdfReady ? "flw-status done" : "flw-status"}>
              {generatedPdfReady ? "Ready" : "Pending"}
            </span>
          </div>

          <div className="flw-actions">
            <button
              type="button"
              className="flw-btn primary"
              disabled={!photoConfirmed || loading === "create-pdf"}
              onClick={handleCreatePdf}
            >
              {loading === "create-pdf" ? "Creating..." : "Create PDF"}
            </button>

            {generatedPdfReady && generatedPdfUrl && (
              <a
                className="flw-btn green"
                href={generatedPdfUrl}
                download={generatedPdfName}
              >
                Download PDF
              </a>
            )}
          </div>

          {generatedPdfReady ? (
            <p className="flw-good-text">PDF is ready. Download it, then upload it in Apply for Loan.</p>
          ) : (
            <p>There is no Extract Fields button here. Extraction starts after upload in Apply for Loan.</p>
          )}
        </div>

        <div className="flw-card">
          <div className="flw-card-head">
            <div>
              <h3>Apply for Loan</h3>
              <p>Upload the downloaded generated PDF here, then extract readable text.</p>
            </div>

            <span className={loanPdfConfirmed ? "flw-status done" : "flw-status"}>
              {loanPdfConfirmed ? "Uploaded" : "Pending"}
            </span>
          </div>

          <div className="flw-upload-box">
            <strong>Loan Application Document</strong>

            <input
              type="file"
              accept="application/pdf"
              onChange={(event) => {
                const file = event.target.files?.[0];

                if (file) {
                  setLoanPdfFile(file);
                  resetLoanExtraction();
                  showSuccess("Generated PDF selected. Click Confirm Loan Application Upload.");
                }
              }}
            />

            {loanPdfFile && <p className="flw-file-ready">PDF ready: {loanPdfFile.name}</p>}

            <div className="flw-actions">
              <button
                type="button"
                className="flw-btn muted"
                disabled={!loanPdfFile || loading === "loan-upload"}
                onClick={handleConfirmLoanPdfUpload}
              >
                {loading === "loan-upload" ? "Uploading..." : "Confirm Loan Application Upload"}
              </button>

              {loanPdfConfirmed && (
                <button
                  type="button"
                  className="flw-btn primary"
                  disabled={loading === "extract-text"}
                  onClick={handleExtractText}
                >
                  {loading === "extract-text" ? "Extracting..." : "Extract Text"}
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="flw-card flw-wide">
          <div className="flw-card-head">
            <div>
              <h3>Readable Extracted Text</h3>
              <p>
                This view should include applicant data, scanned photo reference, salary certificate reference,
                identity document reference, and all readable PDF text.
              </p>
            </div>

            <span className={textExtracted ? "flw-status done" : "flw-status"}>
              {textExtracted ? "Extracted" : "Waiting"}
            </span>
          </div>

          {textExtracted ? (
            <>
              <pre className="flw-text-view">{extractedText}</pre>

              <div className="flw-actions">
                <button
                  type="button"
                  className="flw-btn primary"
                  disabled={loading === "extract-fields"}
                  onClick={handleExtractFields}
                >
                  {loading === "extract-fields" ? "Extracting Fields..." : "Extract Fields"}
                </button>
              </div>
            </>
          ) : (
            <p>No readable text yet. Confirm loan PDF upload, then click Extract Text.</p>
          )}
        </div>

        <div className="flw-card">
          <div className="flw-card-head">
            <div>
              <h3>Extracted Fields</h3>
              <p>After fields are extracted, Send Review and Predict will appear here.</p>
            </div>

            <span className={fieldsExtracted ? "flw-status done" : "flw-status"}>
              {fieldsExtracted ? "Ready" : "Waiting"}
            </span>
          </div>

          {fieldsExtracted && extractedFields ? (
            <>
              <div className="flw-field-table">
                {Object.entries(extractedFields).map(([key, value]) => (
                  <div className="flw-field-row" key={key}>
                    <strong>{key.replaceAll("_", " ")}</strong>
                    <span>{value === null || value === undefined ? "-" : String(value)}</span>
                  </div>
                ))}
              </div>

              <div className="flw-actions">
                <button
                  type="button"
                  className="flw-btn green"
                  disabled={loading === "send-review"}
                  onClick={handleSendReview}
                >
                  {loading === "send-review" ? "Sending..." : "Send Review"}
                </button>

                <button
                  type="button"
                  className="flw-btn primary"
                  disabled={loading === "predict"}
                  onClick={handlePredict}
                >
                  {loading === "predict" ? "Predicting..." : "Predict"}
                </button>
              </div>
            </>
          ) : (
            <p>No fields yet. Extract readable text first, then click Extract Fields.</p>
          )}
        </div>

        <div className="flw-card">
          <h3>Prediction Result</h3>

          {predictionResult ? (
            <pre className="flw-prediction">{JSON.stringify(predictionResult, null, 2)}</pre>
          ) : (
            <p>No prediction yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}
