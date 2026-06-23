from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.models.application import Application


def generate_application_pdf(application: Application, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    y = height - 60

    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, y, "SmartLoan AI - Application Form")

    y -= 40

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Application ID: {application.id}")
    y -= 22
    pdf.drawString(50, y, f"Status: {application.status}")
    y -= 22
    pdf.drawString(50, y, f"Applicant Name: {application.first_name} {application.last_name}")
    y -= 22
    pdf.drawString(50, y, f"Father Name: {application.father_name}")
    y -= 22
    pdf.drawString(50, y, f"Mother Name: {application.mother_name}")
    y -= 22
    pdf.drawString(50, y, f"Age: {application.age}")
    y -= 22
    pdf.drawString(50, y, f"Phone: {application.phone}")
    y -= 22
    pdf.drawString(50, y, f"Email: {application.email}")
    y -= 22
    pdf.drawString(50, y, f"Address: {application.address}")

    y -= 35

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "Occupation and Income")
    y -= 25

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Occupation: {application.occupation or 'Not provided'}")
    y -= 22
    pdf.drawString(50, y, f"Monthly Income: {application.monthly_income or 'Not provided'}")

    y -= 35

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, "System Note")
    y -= 25

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, "This PDF was generated automatically by SmartLoan AI.")

    pdf.save()

    return output_path
