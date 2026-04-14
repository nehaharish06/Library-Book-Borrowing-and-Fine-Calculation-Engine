# =============================
# COMPLETE STRUCTURED FLASK APP (AS YOU SPECIFIED)
# =============================

from flask import Flask, render_template, request, redirect, send_file
import pandas as pd
from datetime import datetime
import os

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from flask import jsonify
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

UPLOAD = 'uploads'
REPORT = 'reports'
os.makedirs(UPLOAD, exist_ok=True)
os.makedirs(REPORT, exist_ok=True)

ALLOWED_DAYS = 5

# ------------------ PROCESS ------------------

def process_data(book_file, borrow_file):
    books = pd.read_csv(book_file)
    records = pd.read_csv(borrow_file)
    books.columns = books.columns.str.strip()
    records.columns = records.columns.str.strip()
    valid_books = set(books['book_id'])
    output = []

    for _, r in records.iterrows():
        if r['book_id'] not in valid_books:
            continue

        try:
            b = datetime.strptime(r['borrow_date'], '%Y-%m-%d')
            ret = datetime.strptime(r['return_date'], '%Y-%m-%d')
        except:
            continue

        days = (ret - b).days
        fine = 0
        late = False

        if days > ALLOWED_DAYS:
            fine = (days - ALLOWED_DAYS) * 20
            late = True

        output.append({
            'user_id': r['user_id'],
            'book_id': r['book_id'],
            'days': days,
            'fine': fine,
            'late': late,
            'borrow_date': r['borrow_date'],
            'return_date': r['return_date'],
            'email': r['email']
        })

    df = pd.DataFrame(output)
    df.to_csv(f'{REPORT}/fine_report.csv', index=False)

    usage = df.groupby('book_id').size().reset_index(name='count')
    usage.to_csv(f'{REPORT}/usage.csv', index=False)

    return df, usage

# ------------------ PDF ------------------

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
def make_pdf(row):
    path = f"{REPORT}/receipt_{row['user_id']}.pdf"

    c = canvas.Canvas(path, pagesize=letter)
    width, height = letter

    # ---------------- BACKGROUND ----------------
    c.setFillColorRGB(0.96, 0.90, 0.80)
    c.rect(0, 0, width, height, fill=1)

    # RESET TEXT COLOR (VERY IMPORTANT)
    c.setFillColor(colors.black)

    # ---------------- BORDER ----------------
    c.setStrokeColor(colors.brown)
    c.setLineWidth(2)
    c.rect(10, 10, width-20, height-20)

    # Start position
    y = height - 40

    # ---------------- HEADER ----------------
    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "City Central Library")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawString(40, y-20, "123 Knowledge Street, Library District")
    c.drawString(40, y-35, "Phone: 011-2345-6789")

    c.drawRightString(width-40, y, f"Date: {row['return_date']}")
    c.drawRightString(width-40, y-20, f"Slip No: {row['user_id']}")

    c.setStrokeColor(colors.brown)
    c.line(30, y-50, width-30, y-50)

    # ---------------- TITLE ----------------
    c.setFillColor(colors.darkred)
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(width/2, y-80, "Library Fine Receipt")

    c.setFillColor(colors.black)
    c.line(30, y-95, width-30, y-95)

    # ---------------- USER INFO ----------------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, y-120, f"Patron: {row['user_id']}")
    c.drawRightString(width-40, y-120, f"ID No: {row['user_id']}")

    c.drawString(40, y-140, f"Late Title(s): {row['book_name'] if 'book_name' in row else row['book_id']}")
    c.drawRightString(width-40, y-140, f"Days Late: {row['days']},")

    c.line(40, y-155, width-40, y-155)

    # ---------------- DATES ----------------
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y-175, "Check Out Date:")
    c.drawString(220, y-175, "Date Due:")
    c.drawString(400, y-175, "Date Returned:")

    c.setFont("Helvetica", 11)
    c.drawString(40, y-195, row['borrow_date'])
    c.drawString(220, y-195, row['borrow_date'])  # replace if due_date available
    c.drawString(400, y-195, row['return_date'])

    c.line(40, y-210, width-40, y-210)

    # ---------------- STATUS ----------------
    late_days = max(0, row['days'] - ALLOWED_DAYS)

    c.setFont("Helvetica", 11)
    c.drawString(40, y-230, "Book Was: [ ] Damaged   Cost: Rs. 0")

    if row['late']:
        c.setFillColor(colors.red)
        c.drawString(
            40, y-250,
            f"Book Was: [X] Late by {late_days} days. Cost per day: Rs. 10    Cost: Rs. {row['fine']}"
        )
        c.setFillColor(colors.black)
    else:
        c.drawString(40, y-250, "Book Was: [ ] Late   Cost: Rs. 0")

    c.drawString(40, y-270, "Book Was: [ ] Lost/Abandoned/Stolen   Cost: Rs. 0")

    # ---------------- AMOUNT BOX ----------------
    c.setStrokeColor(colors.brown)
    c.setLineWidth(1.5)
    c.rect(40, y-380, width-80, 100)

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkred)
    c.drawString(60, y-300, "Full Amount:")
    c.drawRightString(width-60, y-300, f"Rs. {row['fine']:.2f}")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    c.drawString(60, y-325, "Amount Paid:")
    c.drawRightString(width-60, y-325, "Rs. 0.00")

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.darkred)
    c.drawString(60, y-350, "Balance Due:")
    c.drawRightString(width-60, y-350, f"Rs. {row['fine']:.2f}")

    # ---------------- PAYMENT ----------------
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    c.drawString(40, y-400, "Payment Method: [ ] Cash   [ ] Check   [ ] Card")

    # ---------------- FOOTER ----------------
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(
        width/2, 60,
        "This is a system-generated fine slip from City Central Library. Please pay at the front desk."
    )
    c.drawCentredString(width/2, 45, f"Date: {row['return_date']}")

    c.save()

    return path
# ------------------ EMAIL ------------------

def send_mail(to, pdf, user_id):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")

    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = to
    msg['Subject'] = "Library Fine"

    # ✅ Add proper email body (THIS WAS MISSING)
    body = f"""Dear User {user_id},

Please find attached your library fine receipt.

Kindly clear any outstanding dues at the earliest to avoid further penalties.

If you have already made the payment, please disregard this message.

Regards,  
Library Management System
"""

    msg.attach(MIMEText(body, 'plain'))

    # ✅ Keep your original attachment code
    part = MIMEBase('application', 'octet-stream')
    with open(pdf, 'rb') as f:
        part.set_payload(f.read())

    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(pdf)}')
    msg.attach(part)

    # ✅ Send mail (unchanged)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(sender, password)
        s.send_message(msg)

# ------------------ ROUTES ------------------

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method == 'POST':
        b = request.files['books']
        r = request.files['records']

        bp = os.path.join(UPLOAD, b.filename)
        rp = os.path.join(UPLOAD, r.filename)

        b.save(bp)
        r.save(rp)

        process_data(bp, rp)

        return redirect('/results')

    return render_template('upload.html')

@app.route('/results')
def results():
    df = pd.read_csv(f'{REPORT}/fine_report.csv')
    usage = pd.read_csv(f'{REPORT}/usage.csv')

    # 🔥 Badge ONLY if fine > 250
    def add_badge(row):
        if row['fine'] > 250:
            return f"{row['user_id']} <span class='badge'>HIGH FINE</span>"
        return row['user_id']

    df['user_id'] = df.apply(add_badge, axis=1)

    # 🔴 Background for ANY fine > 0
    def highlight_row(row):
        if row['fine'] > 0:
            return ['background-color: #2a1a1a'] * len(row)
        return [''] * len(row)

    # 🔥 Red highlight for user_id + fine (ANY fine > 0)
    def highlight_cells(row):
        styles = []
        for col in row.index:
            if row['fine'] > 0 and col in ['user_id', 'fine']:
                styles.append('color: #ff4d4d; font-weight: bold')
            else:
                styles.append('')
        return styles

    styled_df = df.style.apply(highlight_row, axis=1)\
                         .apply(highlight_cells, axis=1)

    return render_template(
        'results.html',
        fine=styled_df.to_html(escape=False),
        usage=usage.to_html(classes='table table-dark')
    )

@app.route('/email')
def email_page():
    df = pd.read_csv(f'{REPORT}/fine_report.csv')
    pending = df[df['fine'] > 0]

    return render_template('email.html', data=pending.to_dict(orient='records'))

@app.route('/send_mail/<user>', methods=['POST'])
def send(user):
    email = request.form['email']
    df = pd.read_csv(f'{REPORT}/fine_report.csv')
    row = df[df['user_id']==user].iloc[0]

    try:
        pdf = make_pdf(row)
        send_mail(email, pdf, user)

        return jsonify({"status": "success", "message": f"Email sent to {user}"})

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/send_bulk', methods=['POST'])
def send_bulk():
    df = pd.read_csv(f'{REPORT}/fine_report.csv')
    pending = df[df['fine'] > 0]

    success = 0
    failed = 0
    errors = []   # ✅ FIX

    for _, row in pending.iterrows():
        try:
            user = row['user_id']
            email = row['email']

            pdf = make_pdf(row)
            send_mail(email, pdf, user)

            success += 1

        except Exception as e:
            failed += 1
            errors.append(str(e))

    return jsonify({
        "status": "done",
        "sent": success,
        "failed": failed,
        "errors": errors[:3]
    })
    
    
@app.route('/download/<file>')
def download(file):
    return send_file(f'{REPORT}/{file}', as_attachment=True)

# ------------------ RUN ------------------

if __name__ == '__main__':
    app.run(debug=True)

