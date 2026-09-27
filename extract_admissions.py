import csv
import os
from datetime import datetime

from pypdf import PdfReader

pdf_path = r'PDF Reader, All PDF Viewer_ADMISSION DATA.pdf'
reader = PdfReader(pdf_path)

fieldnames = [
    "Timestamp",
    "Student Name",
    "Course Name",
    "Course Fees",
    "Aadhar Number",
    "College Name",
    "Mobile Number",
    "Address",
    "Placement Details",
    "Payment Method",
    "Transaction ID",
]

records = [
    {"student_name": "PARVEEZ KHAN", "course_name": "Certificate Course in CAD", "college_name": "BE (MECH)", "mobile_number": "7448297470", "address": "Batch: EDS/CAD/01", "course_fees": ""},
    {"student_name": "BALKRISHNA", "course_name": "ACAD, NX", "college_name": "ITI", "mobile_number": "9595535479", "address": "Batch: EDS/CAD/02", "course_fees": ""},
    {"student_name": "CHANDRASHEKAR MURKHE", "course_name": "ACAD, SOLIDWORKS", "college_name": "DIPLOMA (MECH)", "mobile_number": "8788183113", "address": "Batch: EDS/CAD/03", "course_fees": ""},
    {"student_name": "KHUSI RAMTEKE", "course_name": "ECAD", "college_name": "BE (ELECT)", "mobile_number": "7721803530", "address": "Batch: EDS/CAD/04", "course_fees": ""},
    {"student_name": "PRANTOSH", "course_name": "CAD", "college_name": "BE (MECH)", "mobile_number": "", "address": "Batch: EDS/CAD/05", "course_fees": ""},
    {"student_name": "RITISHA", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "7020314499", "address": "Batch: EDS/PDD/202601", "course_fees": "20000"},
    {"student_name": "RADHIKA BAJPAYE", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "7499913678", "address": "Batch: EDS/PDD/202602", "course_fees": "20000"},
    {"student_name": "PRAPTI BHANGE", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "8180935428", "address": "Batch: EDS/PDD/202602", "course_fees": "20000"},
    {"student_name": "RIDHI GADPAYLE", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "9021119276", "address": "Batch: EDS/PDD/202602", "course_fees": "17500"},
    {"student_name": "SIDHI GADPAYLE", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "7559119276", "address": "Batch: EDS/PDD/202602", "course_fees": "17500"},
    {"student_name": "YAMINI", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "9270819638", "address": "Batch: EDS/PDD/202603", "course_fees": "22500"},
    {"student_name": "YOGINI", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "7828968046", "address": "Batch: EDS/PDD/202603", "course_fees": "22500"},
    {"student_name": "ISHWARI", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "7721882552", "address": "Batch: EDS/PDD/202603", "course_fees": "22500"},
    {"student_name": "TANUSHRI", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "9307303075", "address": "Batch: EDS/PDD/202603", "course_fees": "22500"},
    {"student_name": "Aditi Falke", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "9209725572", "address": "Batch: EDS/PDD/202604", "course_fees": "20000"},
    {"student_name": "Anushka Hiwase", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "8459854553", "address": "Batch: EDS/PDD/202604", "course_fees": "20000"},
    {"student_name": "Aditi Yerpude", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "7414965059", "address": "Batch: EDS/PDD/202604", "course_fees": "20000"},
    {"student_name": "NATASHA", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BTECH (AERONAUTICAL)", "mobile_number": "9860935310", "address": "Batch: EDS/PDD/202605", "course_fees": "25000"},
    {"student_name": "CHARULATA", "course_name": "Master Certificate Course in Product Design & Development", "college_name": "BE (MECH Pursuing)", "mobile_number": "7447615146", "address": "Batch: EDS/PDD/202605", "course_fees": "25000"},
    {"student_name": "ISHA NIMKAR", "course_name": "CAE", "college_name": "BE (MECH Pursuing)", "mobile_number": "", "address": "Batch: EDS/CAE/202606", "course_fees": "8000"},
    {"student_name": "PRAPTIKA DAF", "course_name": "CAE", "college_name": "BE (MECH Pursuing)", "mobile_number": "", "address": "Batch: EDS/CAE/202606", "course_fees": "8000"},
    {"student_name": "VEDANTI BADWAIK", "course_name": "CAE", "college_name": "BE (MECH Pursuing)", "mobile_number": "", "address": "Batch: EDS/CAE/202606", "course_fees": "8000"},
]

output_path = "admissions_local.csv"
copy_path = "admission_local.csv"

rows_to_write = []
if os.path.exists(output_path):
    with open(output_path, newline="", encoding="utf-8") as f:
        rows_to_write = list(csv.DictReader(f))

# Keep existing rows and append imported PDF rows.
for item in records:
    row = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Student Name": item["student_name"],
        "Course Name": item["course_name"],
        "Course Fees": item.get("course_fees", ""),
        "Aadhar Number": "",
        "College Name": item.get("college_name", ""),
        "Mobile Number": item.get("mobile_number", ""),
        "Address": item.get("address", ""),
        "Placement Details": "",
        "Payment Method": "Cash",
        "Transaction ID": "",
    }
    rows_to_write.append(row)

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows_to_write)

with open(copy_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows_to_write)

print(f"Wrote {len(rows_to_write)} rows to {output_path} and {copy_path}")
