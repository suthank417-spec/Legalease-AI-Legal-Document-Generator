from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import sqlite3, os, io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER

app = Flask(__name__)
app.secret_key = "legalease-demo-secret"
DB = os.path.join("data", "legalease.db")

DOCUMENTS = {
    "rental": {
        "name": "Rental Agreement",
        "fields": ["landlord", "tenant", "property_address", "monthly_rent", "duration"]
    },
    "nda": {
        "name": "Non-Disclosure Agreement (NDA)",
        "fields": ["disclosing_party", "receiving_party", "purpose", "duration"]
    },
    "employment": {
        "name": "Employment Agreement",
        "fields": ["employer", "employee", "job_title", "salary", "start_date"]
    },
    "complaint": {
        "name": "Legal Complaint Letter",
        "fields": ["sender", "recipient", "subject", "incident", "requested_action"]
    }
}

LABELS = {
    "landlord":"Landlord Name","tenant":"Tenant Name","property_address":"Property Address",
    "monthly_rent":"Monthly Rent (₹)","duration":"Agreement Duration",
    "disclosing_party":"Disclosing Party","receiving_party":"Receiving Party","purpose":"Purpose",
    "employer":"Employer Name","employee":"Employee Name","job_title":"Job Title",
    "salary":"Salary","start_date":"Start Date","sender":"Your Name","recipient":"Recipient Name",
    "subject":"Subject","incident":"Incident Details","requested_action":"Requested Action"
}

def init_db():
    os.makedirs("data", exist_ok=True)
    with sqlite3.connect(DB) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS documents(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_type TEXT, title TEXT, content TEXT, created_at TEXT
        )""")

def generate_document(doc_type, data):
    if doc_type == "rental":
        return f"""RENTAL AGREEMENT

This Rental Agreement is made between {data['landlord']} (Landlord) and {data['tenant']} (Tenant).

PROPERTY
The property covered by this agreement is located at:
{data['property_address']}

RENT AND TERM
Monthly rent: ₹{data['monthly_rent']}
Agreement duration: {data['duration']}

GENERAL TERMS
The tenant agrees to use the property lawfully and maintain it with reasonable care.
The parties should review all applicable local laws and add any required clauses before signing.

SIGNATURES
Landlord: ____________________
Tenant: ______________________
Date: ________________________

DISCLAIMER
This is an AI-assisted draft for educational/general drafting purposes and is not legal advice."""
    if doc_type == "nda":
        return f"""NON-DISCLOSURE AGREEMENT (DRAFT)

Disclosing Party: {data['disclosing_party']}
Receiving Party: {data['receiving_party']}
Purpose: {data['purpose']}
Duration: {data['duration']}

CONFIDENTIALITY
The Receiving Party agrees to keep confidential information received for the stated purpose and not disclose it except as permitted by the final agreement or applicable law.

The parties should have this document reviewed and customized for their jurisdiction and circumstances.

Signatures:
Disclosing Party: ____________________
Receiving Party: _____________________
Date: _______________________________

DISCLAIMER
AI-generated draft; not a substitute for advice from a qualified legal professional."""
    if doc_type == "employment":
        return f"""EMPLOYMENT AGREEMENT (DRAFT)

Employer: {data['employer']}
Employee: {data['employee']}
Job Title: {data['job_title']}
Salary: {data['salary']}
Start Date: {data['start_date']}

The Employee will perform the duties associated with the stated role and comply with lawful workplace policies. Compensation, working hours, leave, termination, confidentiality and other terms should be finalized according to applicable law and the employer's policies.

Signatures:
Employer: __________________________
Employee: __________________________
Date: ______________________________

DISCLAIMER
AI-generated draft for general/educational use. Obtain appropriate legal review before relying on it."""
    return f"""LEGAL COMPLAINT LETTER (DRAFT)

From: {data['sender']}
To: {data['recipient']}
Subject: {data['subject']}

INCIDENT
{data['incident']}

REQUESTED ACTION
{data['requested_action']}

I request that the matter be reviewed and an appropriate response be provided.

Sincerely,
{data['sender']}

DISCLAIMER
This is a drafting aid and not legal advice. Verify facts and applicable procedures before sending."""

@app.route("/")
def home():
    return render_template("index.html", documents=DOCUMENTS)

@app.route("/create/<doc_type>", methods=["GET","POST"])
def create(doc_type):
    if doc_type not in DOCUMENTS:
        return "Document type not found", 404
    doc=DOCUMENTS[doc_type]
    if request.method=="POST":
        data={f:request.form.get(f,"").strip() for f in doc["fields"]}
        if any(not v for v in data.values()):
            flash("Please fill all fields.")
            return render_template("form.html", doc=doc, doc_type=doc_type, labels=LABELS)
        content=generate_document(doc_type,data)
        with sqlite3.connect(DB) as con:
            cur=con.execute("INSERT INTO documents(doc_type,title,content,created_at) VALUES(?,?,?,?)",
                            (doc_type,doc["name"],content,datetime.now().strftime("%Y-%m-%d %H:%M")))
            doc_id=cur.lastrowid
        return redirect(url_for("view_document", doc_id=doc_id))
    return render_template("form.html", doc=doc, doc_type=doc_type, labels=LABELS)

@app.route("/document/<int:doc_id>")
def view_document(doc_id):
    with sqlite3.connect(DB) as con:
        row=con.execute("SELECT id,title,content,created_at FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row: return "Document not found",404
    return render_template("document.html", row=row)

@app.route("/download/<int:doc_id>")
def download(doc_id):
    with sqlite3.connect(DB) as con:
        row=con.execute("SELECT title,content FROM documents WHERE id=?", (doc_id,)).fetchone()
    if not row: return "Document not found",404
    buf=io.BytesIO()
    styles=getSampleStyleSheet()
    story=[Paragraph(row[0], styles["Title"]), Spacer(1,16)]
    for p in row[1].split("\n"):
        if p.strip():
            story.append(Paragraph(p.replace("&","&amp;"), styles["BodyText"]))
            story.append(Spacer(1,8))
    SimpleDocTemplate(buf,pagesize=A4,rightMargin=50,leftMargin=50,topMargin=50,bottomMargin=50).build(story)
    buf.seek(0)
    return send_file(buf,as_attachment=True,download_name="legalease_document.pdf",mimetype="application/pdf")

@app.route("/history")
def history():
    with sqlite3.connect(DB) as con:
        rows=con.execute("SELECT id,title,created_at FROM documents ORDER BY id DESC").fetchall()
    return render_template("history.html", rows=rows)

init_db()
if __name__=="__main__":
    app.run(debug=True)
