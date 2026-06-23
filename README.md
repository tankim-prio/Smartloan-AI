# SmartLoan AI

## AI-Powered Loan Application, Review Workflow, PDF Intelligence and Risk Prediction Platform

SmartLoan AI is a complete full-stack portfolio project that demonstrates how a modern loan processing system can combine frontend engineering, backend API development, PDF automation, document intelligence, machine learning prediction, admin review workflow, reporting, AI-assisted document support and Docker deployment.

This project was designed to simulate a real-world digital loan application platform. An applicant can create an account, complete a loan application, generate a loan PDF, upload loan-related documents, extract text from PDFs, extract structured fields, run a machine learning prediction, send the application for review, and allow an admin or reviewer to approve or refuse the application.

Repository: https://github.com/tankim-prio/smartloan-ai

---

## Project Purpose

The purpose of SmartLoan AI is to demonstrate practical engineering skills through one connected, realistic and portfolio-ready system.

This project is suitable for:

- International job recruiter review
- University project evaluation
- AI Engineer portfolio
- Machine Learning Engineer portfolio
- Backend Developer portfolio
- Full-stack Developer portfolio
- Document intelligence project showcase
- Dockerized application demonstration
- Real-world workflow automation demonstration

SmartLoan AI is not only a simple CRUD system. It connects application data, PDF generation, document extraction, machine learning prediction, review management, reporting and AI document assistance into one professional workflow.

---

## Main Features

### 1. Authentication and User Workflow

- Login page
- Create account page
- Profile page
- Protected application pages
- Role-based workflow concept
- Applicant and admin/reviewer workflow separation

### 2. Loan Application System

- Professional Apply page
- Personal information section
- Employment and income section
- Loan information workflow
- Clean blank form fields
- Application data saving
- Professional form behavior without hardcoded sample values

### 3. PDF Generation

- Generate loan application PDF
- Include applicant information in PDF
- Include applicant summary
- Support profile photo and document pages
- Support salary certificate / NID / passport style documents
- Download generated loan PDF

### 4. PDF Upload and Text Extraction

- Upload generated or external loan PDF
- Extract readable text from PDF
- Extract structured applicant fields
- Extract salary certificate information
- PDF text-layer extraction
- OCR fallback for scanned or image-based PDF pages
- Designed for document intelligence workflow

Example extracted fields:

- Application ID
- Applicant name
- Father name
- Mother name
- Age
- Phone
- Email
- Address
- Occupation
- Monthly income
- Salary certificate number
- Employee name
- Designation
- Monthly salary
- NID-related text when OCR is possible

### 5. Review Management

- Send application to Review
- Create separate review records
- Pending review list
- Approved review list
- Refused review list
- All review history
- Admin can inspect extracted information
- Admin can approve or refuse a loan application
- Clean card-based review UI

### 6. Machine Learning Prediction

- Loan approval probability
- Risk score
- Risk band
- Prediction explanation
- Active model concept
- ML Model page
- MLOps-style model workflow concept
- Apply page prediction integration

### 7. Dashboard and Reports

- Dashboard overview
- Application statistics
- Review status overview
- Reports page
- Management-level insight
- Clean portfolio-ready UI

### 8. AI Pilot / RAG Assistant

- Document assistant concept
- Store document text
- Ask questions from stored documents
- Useful for loan policy explanation
- Demonstrates AI/RAG-style workflow

### 9. Docker Deployment

- Dockerized FastAPI backend
- Dockerized React frontend
- Docker Compose setup
- Nginx frontend serving
- Persistent local database mapping
- Persistent upload and storage folders
- Large PDF/image upload support

---

## Technology Stack

### Frontend

- React
- Vite
- TypeScript
- Tailwind CSS
- Shadcn-style UI structure
- Axios / API integration
- Responsive dashboard interface
- Component-based UI structure

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy
- SQLite
- Modular routers
- Service-layer architecture
- REST API design

### Machine Learning

- scikit-learn
- pandas
- NumPy
- joblib
- Custom loan risk prediction pipeline
- Model loading and prediction service

### PDF and Document Processing

- pypdf / PyPDF
- PyMuPDF
- pytesseract OCR
- Pillow
- ReportLab
- PDF generation
- PDF text extraction
- OCR fallback for scanned pages

### DevOps and Deployment

- Docker
- Docker Compose
- Nginx
- Backend container
- Frontend container
- Persistent volume mapping
- Local and Docker development workflow

### Database and Storage

- SQLite
- Local database files
- Persistent Docker volume mapping
- Upload storage
- Generated PDF storage
- Document storage

---

## System Architecture

SmartLoan AI follows a modular full-stack architecture.

User / Applicant / Admin
    -> React + Vite Frontend
    -> FastAPI Backend API
    -> SQLite Database
    -> File Storage
    -> PDF Processing
    -> ML Prediction Service
    -> AI/RAG Document Assistant
    -> Review and Reports Workflow

---

## Main Workflow

1. User logs into the system.
2. User opens the Dashboard.
3. User goes to Apply page.
4. User fills personal, employment and loan information.
5. System generates a loan application PDF.
6. User uploads the PDF in Apply for Loan section.
7. System extracts readable PDF text.
8. System extracts structured fields.
9. User runs ML prediction.
10. User sends application to Review.
11. Admin opens Review page.
12. Admin approves or refuses the application.
13. Reports and dashboard show the system status.

---

## Important Pages

- Login Page
- Create Account Page
- Dashboard Page
- Apply Page
- Review Page
- ML Model Page
- Reports Page
- AI Pilot Page
- Profile Page

---

## Project Structure

smartloan-ai/
  backend/
    app/
      core/
      ml/
      models/
      routers/
      schemas/
      services/
      main.py
    storage/
    uploads/
    data/
    Dockerfile
    requirements.txt

  frontend/
    src/
    public/
    Dockerfile
    nginx.conf

  docs/
    SCREENSHOT_LIST.md
    DEMO_VIDEO_SCRIPT.md
    GITHUB_PUSH_CHECKLIST.md

  docker-compose.yml
  README.md
  .gitignore

---

## Local Development Setup

Backend:

    cd backend
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 20000

Frontend:

    cd frontend
    npm install
    npm run dev -- --host localhost --port 5173

Frontend URL:

    http://localhost:5173

Backend URL:

    http://localhost:20000

---

## Docker Setup

Run from project root:

    docker compose up --build

Frontend:

    http://localhost:5173

Backend:

    http://localhost:20000

Stop Docker:

    docker compose down

Health check URLs:

    http://localhost:20000/api/v1/customer-portal/health
    http://localhost:20000/api/v1/ml/health
    http://localhost:20000/api/v1/ai-rag/health

---

## API Areas

The backend includes modular API areas for:

- Authentication
- Customer portal
- Loan application
- PDF generation
- PDF extraction
- Review workflow
- ML prediction
- AI/RAG assistant
- Reports and dashboard data

---

## Machine Learning Workflow

Applicant data is processed into model features. The active ML model then returns approval probability, risk score, risk band and explanation. This allows the reviewer to make a more informed decision.

ML workflow:

Applicant Data -> Feature Processing -> ML Model -> Approval Probability -> Risk Score -> Risk Band -> Explanation

---

## PDF Intelligence Workflow

The PDF intelligence workflow supports both normal text-based PDFs and image/scanned PDF pages.

PDF workflow:

Uploaded PDF -> Text Layer Extraction -> OCR Fallback -> Readable Text -> Structured Fields -> Review and Prediction Workflow

This is important because real loan documents often include scanned salary certificates, NID images, passport pages and uploaded PDF documents.

---

## Docker Persistence Design

The Docker version is designed to use persistent local folders so the system does not lose important data.

Persistent areas:

- SQLite database
- Uploaded PDFs
- Generated PDFs
- Document uploads
- Storage folders
- Application and review history

---

## Screenshots

Recommended screenshots for portfolio:

1. Login page
2. Dashboard page
3. Apply page
4. Generated PDF workflow
5. PDF upload and extraction result
6. ML prediction result
7. Review page
8. Reports page
9. ML Model page
10. AI Pilot page
11. Docker running containers

Screenshots folder:

    docs/screenshots/

---

## Demo Video Flow

Recommended demo video flow:

1. Introduce SmartLoan AI.
2. Show login page.
3. Open dashboard.
4. Open Apply page.
5. Fill or show applicant information.
6. Generate loan PDF.
7. Upload PDF.
8. Extract text and structured fields.
9. Run ML prediction.
10. Send application for review.
11. Open Review page.
12. Approve or refuse application.
13. Open Reports page.
14. Open ML Model page.
15. Open AI Pilot page.
16. Show Docker running.
17. Show GitHub repository.

---

## What This Project Demonstrates

SmartLoan AI demonstrates:

- Full-stack application development
- FastAPI backend engineering
- React frontend engineering
- REST API design
- Database-backed workflows
- PDF generation
- PDF text extraction
- OCR-based document processing
- ML model integration
- Review approval workflow
- Reports dashboard
- AI/RAG assistant concept
- Docker deployment
- Professional project documentation

---

## Recruiter and Professor Review Notes

This project demonstrates real-world system design thinking. It connects multiple practical components into one complete workflow:

- User input
- Document generation
- Document upload
- Text extraction
- Structured data extraction
- Machine learning prediction
- Human review
- Admin decision
- Reporting
- Docker deployment

Because of this, SmartLoan AI can be reviewed as an applied AI/ML engineering project, a backend engineering project and a full-stack software engineering project.

---

## Future Improvements

Possible future improvements:

- PostgreSQL production database
- JWT refresh token flow
- Advanced Bangla OCR support
- Cloud deployment
- CI/CD with GitHub Actions
- Audit log system
- Email notification system
- Model monitoring dashboard
- Vector database based RAG
- Role-specific dashboards
- Real banking or fintech API integration

---

## Author

Tankim Prio

GitHub:

    https://github.com/tankim-prio

Repository:

    https://github.com/tankim-prio/smartloan-ai

---

## Status

SmartLoan AI is a completed portfolio project with:

- Working frontend
- Working backend
- Working Docker setup
- Loan application workflow
- PDF generation
- PDF extraction
- Review workflow
- ML prediction
- Dashboard and reports
- AI Pilot / RAG assistant
- Professional GitHub documentation