from fastapi import FastAPI, Form, HTTPException, Request, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import jinja2
import emails
import os
from datetime import datetime
import tempfile
import shutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Pay Slip Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize templates for web pages
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.post("/submit-payslip")
async def submit_payslip(
    request: Request,
    name: str = Form(None),
    email: str = Form(None),
    student_id: str = Form(None),
    department: str = Form(None),
    year: str = Form(None),
    amount: str = Form(None),
    payment_date: str = Form(None),
    purpose: str = Form(None),
    pdf_file: UploadFile = File(None)
):
    # Validate all required fields are present
    required_fields = {
        'name': name,
        'email': email,
        'student_id': student_id,
        'department': department,
        'year': year,
        'amount': amount,
        'payment_date': payment_date,
        'purpose': purpose
    }
    print("required",required_fields.items())  
    missing_fields = [field for field, value in required_fields.items() if not value]
    if missing_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required fields: {', '.join(missing_fields)}"
        )

    try:
        # Validate amount is a number
        try:
            amount_float = float(amount)
        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Amount must be a valid number (e.g., 5000 or 5000.50)"
            )

        # Create pay slip data
        pay_slip_data = {
            "name": name,
            "email": email,
            "student_id": student_id,
            "department": department,
            "year": year,
            "amount": amount_float,
            "payment_date": payment_date,
            "purpose": purpose,
            "generated_date": datetime.now().strftime("%Y-%m-%d")
        }

        # Save uploaded PDF if provided
        pdf_path = None
        if pdf_file:
            # Validate file type
            if not pdf_file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded file must be a PDF"
                )
            
            # Save the uploaded PDF temporarily
            pdf_path = tempfile.mktemp(suffix='.pdf')
            with open(pdf_path, 'wb') as buffer:
                shutil.copyfileobj(pdf_file.file, buffer)

        # Send email with PDF
        send_email(pay_slip_data, pdf_path if pdf_path else None)

        # Clean up temporary file
        if pdf_path:
            os.remove(pdf_path)

        return JSONResponse(
            content={"message": "Pay slip submitted successfully and sent to email"},
            status_code=200
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def send_email(data: dict, pdf_path: str = None):
    # Configure email
    print("sending email", data)
    print("SMTP Settings:", {
        "host": os.getenv("SMTP_HOST"),
        "port": os.getenv("SMTP_PORT"),
        "user": os.getenv("SMTP_USER"),
        "tls": True
    })
    
    message = emails.Message(
        subject=f'Pay Slip Confirmation - {data["name"]}',
        html=f"""
        <h2>Pay Slip Details</h2>
        <p>Dear {data['name']},</p>
        <p>Your payment details have been received:</p>
        <ul>
            <li>Student ID: {data['student_id']}</li>
            <li>Department: {data['department']}</li>
            <li>Year: {data['year']}</li>
            <li>Amount: ₹{data['amount']}</li>
            <li>Purpose: {data['purpose']}</li>
            <li>Payment Date: {data['payment_date']}</li>
        </ul>
        <p>Please find the attached pay slip for your records.</p>
        <p>Best regards,<br>Finance Department</p>
        """,
        mail_from=(os.getenv("SMTP_USER", "Pay Slip System"))
    )

    # Add PDF attachment if provided
    if pdf_path:
        message.attach(
            filename="payslip.pdf",
            content_disposition="attachment",
            data=open(pdf_path, "rb")
        )

    # Send email
    try:
        response = message.send(
            to=data["email"],
            smtp={
                "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
                "port": int(os.getenv("SMTP_PORT", "587")),
                "user": os.getenv("SMTP_USER"),
                "password": os.getenv("SMTP_PASSWORD"),
                "tls": True
            }
        )
        print("Email response:", response)
        if not response.success:
            raise Exception(f"Failed to send email: {response.error}")
    except Exception as e:
        print("Email error:", str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to send email: {str(e)}"
        )
    print("sent", data)
