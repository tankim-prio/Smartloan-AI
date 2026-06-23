import React, { useMemo, useRef, useState } from "react";
import "./LoanWorkflowPanel.css";

type ExtractedFields = Record<string, string | number | boolean | null>;

type Props = {
  applicationId?: string | number;
};

const API_BASE =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

export default function LoanWorkflowPanel({ applicationId = 2 }: Props) {
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const photoInputRef = useRef<HTMLInputElement | null>(null);

  const [currentApplicationId, setCurrentApplicationId] = useState(String(applicationId));

  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [step3Confirmed, setStep3Confirmed] = useState(false);

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

  const [statusMessage, setStatusMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [loading, setLoading] = useState<string | null>(null);

  const canCreatePdf = step3Confirmed;
  const canConfirmLoanUpload = Boolean(loanPdfFile);
  const canExtractText = loanPdfConfirmed;
  const canExtractFields = textExtracted && extractedText.trim().length > 0;
  const canFinalAction = useMemo(
    () => fieldsExtracted && Boolean(extractedFields),
    [fieldsExtracted, extractedFields]
  );

  function showSuccess(message: string) {
    setStatusMessage(message);
    setErrorMessage("");
  }

  function showError(message: string) {
    setErrorMessage(message);
    setStatusMessage("");
  }

  function resetAfterLoanPdfChange() {
    setLoanPdfConfirmed(false);
    setTextExtracted(false);
    setFieldsExtracted(false);
    setExtractedText("");
    setExtractedFields(null);
    setPredictionResult(null);
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

  async function handleConfirmStep3() {
    if (!photoFile) {
      showError("Please upload or scan applicant photo first.");
      return;
    }

    setLoading("confirm-step-3");

    try {
      const formData = new FormData();
      formData.append("file", photoFile);

      await postForm(`/applications/${currentApplicationId}/photo`, formData);
      await postJson(`/applications/${currentApplicationId}/confirm-step-3`);

      setStep3Confirmed(true);
      showSuccess("Step 3 confirmed. Applicant photo saved successfully.");
    } catch (error: any) {
      showError(error.message || "Failed to confirm Step 3.");
    } finally {
      setLoading(null);
    }
  }

  async function handleCreatePdf() {
    if (!canCreatePdf) {
      showError("Confirm Step 3 before creating PDF.");
      return;
    }

    setLoading("create-pdf");

    try {
      const response = await fetch(`${API_BASE}/applications/${currentApplicationId}/generate-pdf`, {
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
      } else {
        const data = await readResponse(response);
        const rawUrl =
          data.download_url ||
          data.pdf_url ||
          data.file_url ||
          `/applications/${currentApplicationId}/download-pdf`;

        setGeneratedPdfUrl(rawUrl.startsWith("http") ? rawUrl : `${API_BASE}${rawUrl}`);
        setGeneratedPdfName(data.filename || `generated_application_${currentApplicationId}.pdf`);
      }

      setGeneratedPdfReady(true);
      showSuccess("Generated PDF is ready. Download it, then upload it in Apply for Loan.");
    } catch (error: any) {
      showError(error.message || "Failed to create PDF.");
    } finally {
      setLoading(null);
    }
  }

  async function handleConfirmLoanPdfUpload() {
    if (!loanPdfFile) {
      showError("Please choose generated loan application PDF first.");
      return;
    }

    setLoading("confirm-loan-upload");

    try {
      const formData = new FormData();
      formData.append("file", loanPdfFile);

      await postForm(`/applications/${currentApplicationId}/upload-loan-pdf`, formData);

      setLoanPdfConfirmed(true);
      showSuccess("Loan application PDF uploaded successfully. Now extract readable text.");
    } catch (error: any) {
      showError(error.message || "Failed to upload loan application PDF.");
    } finally {
      setLoading(null);
    }
  }

  async function handleExtractText() {
    if (!canExtractText) {
      showError("Confirm loan PDF upload first.");
      return;
    }

    setLoading("extract-text");

    try {
      const response = await postJson(`/applications/${currentApplicationId}/extract-text`);
      const data = await readResponse(response);

      const readableText =
        data.extracted_text ||
        data.readable_text ||
        data.text ||
        data.raw_text ||
        JSON.stringify(data, null, 2);

      setExtractedText(String(readableText));
      setTextExtracted(true);
      setFieldsExtracted(false);
      setExtractedFields(null);
      setPredictionResult(null);

      showSuccess("Readable text extracted successfully.");
    } catch (error: any) {
      showError(error.message || "Failed to extract text.");
    } finally {
      setLoading(null);
    }
  }

  async function handleExtractFields() {
    if (!canExtractFields) {
      showError("Extract readable text first.");
      return;
    }

    setLoading("extract-fields");

    try {
      const response = await postJson(`/applications/${currentApplicationId}/extract-fields`);
      const data = await readResponse(response);

      const fields = data.fields || data.extracted_fields || data.application_fields || data;

      setExtractedFields(fields);
      setFieldsExtracted(true);
      showSuccess("Fields extracted successfully. Now Send Review or Predict.");
    } catch (error: any) {
      showError(error.message || "Failed to extract fields.");
    } finally {
      setLoading(null);
    }
  }

  async function handleSendReview() {
    if (!canFinalAction) {
      showError("Extract fields before sending review.");
      return;
    }

    setLoading("send-review");

    try {
      await postJson(`/applications/${currentApplicationId}/send-review`);
      showSuccess("Application sent for review successfully.");
    } catch (error: any) {
      showError(error.message || "Failed to send review.");
    } finally {
      setLoading(null);
    }
  }

  async function handlePredict() {
    if (!canFinalAction) {
      showError("Extract fields before prediction.");
      return;
    }

    setLoading("predict");

    try {
      const response = await postJson(`/applications/${currentApplicationId}/predict`);
      const data = await readResponse(response);

      setPredictionResult(data);
      showSuccess("Prediction completed successfully.");
    } catch (error: any) {
      showError(error.message || "Prediction failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <section className="sl-workflow">
      <div className="sl-workflow-head">
        <div>
          <span className="sl-kicker">Loan Workflow</span>
          <h2>Apply → PDF → Extraction → ML Prediction</h2>
          <p>
            This keeps your existing page and adds the correct connection between Apply section and ML model section.
          </p>
        </div>

        <label className="sl-app-id">
          Application ID
          <input
            value={currentApplicationId}
            onChange={(event) => setCurrentApplicationId(event.target.value)}
          />
        </label>
      </div>

      {(statusMessage || errorMessage) && (
        <div className="sl-message-wrap">
          {statusMessage && <div className="sl-success">{statusMessage}</div>}
          {errorMessage && <div className="sl-error">{errorMessage}</div>}
        </div>
      )}

      <div className="sl-grid">
        <div className="sl-card sl-wide">
          <div className="sl-card-title-row">
            <div>
              <span className="sl-step">Step 03</span>
              <h3>Scan Photo</h3>
              <p>Upload applicant photo or scan with device camera. Mobile browser will prefer front camera.</p>
            </div>
            <span className={step3Confirmed ? "sl-pill good" : "sl-pill"}>{step3Confirmed ? "Confirmed" : "Pending"}</span>
          </div>

          <div className="sl-upload-box">
            <strong>Applicant Photo</strong>

            <input
              ref={photoInputRef}
              type="file"
              accept="image/*"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  setPhotoFile(file);
                  setStep3Confirmed(false);
                  showSuccess("Photo selected. Confirm Step 3 to save.");
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
                  setStep3Confirmed(false);
                  showSuccess("Photo captured. Confirm Step 3 to save.");
                }
              }}
            />

            {photoFile && <p className="sl-file">Photo ready: {photoFile.name}</p>}

            <div className="sl-actions">
              <button className="sl-btn muted" onClick={() => photoInputRef.current?.click()}>
                Choose Photo
              </button>

              <button className="sl-btn dark" onClick={() => cameraInputRef.current?.click()}>
                Scan Photo
              </button>

              <button
                className="sl-btn primary"
                disabled={!photoFile || loading === "confirm-step-3"}
                onClick={handleConfirmStep3}
              >
                {loading === "confirm-step-3" ? "Confirming..." : "Confirm Step 3"}
              </button>
            </div>
          </div>
        </div>

        <div className="sl-card">
          <div className="sl-card-title-row">
            <div>
              <h3>Create PDF</h3>
              <p>Create final generated application PDF only. Extraction does not belong here.</p>
            </div>
            <span className={generatedPdfReady ? "sl-pill good" : "sl-pill"}>{generatedPdfReady ? "Ready" : "Pending"}</span>
          </div>

          <div className="sl-actions">
            <button
              className="sl-btn primary"
              disabled={!canCreatePdf || loading === "create-pdf"}
              onClick={handleCreatePdf}
            >
              {loading === "create-pdf" ? "Creating..." : "Create PDF"}
            </button>

            {generatedPdfReady && generatedPdfUrl && (
              <a className="sl-btn green" href={generatedPdfUrl} download={generatedPdfName}>
                Download PDF
              </a>
            )}
          </div>

          {generatedPdfReady && (
            <p className="sl-good-text">Generated PDF is ready. Download it and upload it in Apply for Loan.</p>
          )}
        </div>

        <div className="sl-card">
          <div className="sl-card-title-row">
            <div>
              <h3>Apply for Loan</h3>
              <p>Upload the generated PDF here. Then extract text and fields.</p>
            </div>
            <span className={loanPdfConfirmed ? "sl-pill good" : "sl-pill"}>{loanPdfConfirmed ? "Uploaded" : "Pending"}</span>
          </div>

          <div className="sl-upload-box">
            <strong>Loan Application Document</strong>

            <input
              type="file"
              accept="application/pdf"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) {
                  setLoanPdfFile(file);
                  resetAfterLoanPdfChange();
                  showSuccess("Loan PDF selected. Confirm upload to continue.");
                }
              }}
            />

            {loanPdfFile && <p className="sl-file">PDF ready: {loanPdfFile.name}</p>}

            <div className="sl-actions">
              <button
                className="sl-btn muted"
                disabled={!canConfirmLoanUpload || loading === "confirm-loan-upload"}
                onClick={handleConfirmLoanPdfUpload}
              >
                {loading === "confirm-loan-upload" ? "Uploading..." : "Confirm Upload"}
              </button>

              {loanPdfConfirmed && (
                <button
                  className="sl-btn primary"
                  disabled={!canExtractText || loading === "extract-text"}
                  onClick={handleExtractText}
                >
                  {loading === "extract-text" ? "Extracting..." : "Extract Text"}
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="sl-card sl-wide">
          <div className="sl-card-title-row">
            <div>
              <h3>Readable Extracted Text</h3>
              <p>Text view from PDF appears here. After this, extract structured fields.</p>
            </div>
            <span className={textExtracted ? "sl-pill good" : "sl-pill"}>{textExtracted ? "Extracted" : "Waiting"}</span>
          </div>

          {textExtracted ? (
            <>
              <pre className="sl-text-view">{extractedText}</pre>

              <div className="sl-actions">
                <button
                  className="sl-btn primary"
                  disabled={!canExtractFields || loading === "extract-fields"}
                  onClick={handleExtractFields}
                >
                  {loading === "extract-fields" ? "Extracting Fields..." : "Extract Fields"}
                </button>
              </div>
            </>
          ) : (
            <p className="sl-muted-text">No text yet. Upload PDF in Apply for Loan and click Extract Text.</p>
          )}
        </div>

        <div className="sl-card">
          <div className="sl-card-title-row">
            <div>
              <h3>Extracted Fields</h3>
              <p>Structured data for review and ML model.</p>
            </div>
            <span className={fieldsExtracted ? "sl-pill good" : "sl-pill"}>{fieldsExtracted ? "Ready" : "Waiting"}</span>
          </div>

          {fieldsExtracted && extractedFields ? (
            <>
              <div className="sl-fields">
                {Object.entries(extractedFields).map(([key, value]) => (
                  <div className="sl-field-row" key={key}>
                    <strong>{key.replaceAll("_", " ")}</strong>
                    <span>{value === null || value === undefined ? "-" : String(value)}</span>
                  </div>
                ))}
              </div>

              <div className="sl-actions">
                <button
                  className="sl-btn green"
                  disabled={!canFinalAction || loading === "send-review"}
                  onClick={handleSendReview}
                >
                  {loading === "send-review" ? "Sending..." : "Send Review"}
                </button>

                <button
                  className="sl-btn primary"
                  disabled={!canFinalAction || loading === "predict"}
                  onClick={handlePredict}
                >
                  {loading === "predict" ? "Predicting..." : "Predict"}
                </button>
              </div>
            </>
          ) : (
            <p className="sl-muted-text">No fields yet. Extract text first, then extract fields.</p>
          )}
        </div>

        <div className="sl-card">
          <h3>Prediction Result</h3>

          {predictionResult ? (
            <pre className="sl-prediction">{JSON.stringify(predictionResult, null, 2)}</pre>
          ) : (
            <p className="sl-muted-text">No prediction yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}
