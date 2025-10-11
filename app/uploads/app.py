#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HireSense Pro v3 — Enterprise Edition
-------------------------------------
✅ ATS + JD Match + Role Insights
✅ Downloadable PDF Reports
✅ Analysis History Dashboard
✅ Local Data Persistence (no cloud)
"""
import os, json, re, uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash, send_file
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas

# --- Internal Imports ---
from utils.parser import extract_text_from_file
from utils.text_clean import normalize_text, simple_skill_extract

# --- Role Keywords ---
MODELS_DIR = Path(__file__).resolve().parent / "models"
ROLES_JSON = MODELS_DIR / "roles_keywords.json"
with open(ROLES_JSON, "r", encoding="utf-8") as f:
    ROLE_KEYWORDS = json.load(f)

# --- NLP Optional ---
try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
except Exception:
    NLP = None

# --- JD Similarity via TF-IDF ---
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False

# --- Global Paths ---
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
BASE_DIR = Path(__file__).resolve().parent
UPLOADS = BASE_DIR / "uploads"
DATA = BASE_DIR / "data"
HISTORY_FILE = DATA / "history.json"
for p in [UPLOADS, DATA]:
    p.mkdir(exist_ok=True)


# -----------------------------
# Utility Functions
# -----------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_skills(text):
    skills = set()
    if NLP:
        doc = NLP(text)
        for tok in doc:
            if tok.ent_type_ in {"ORG", "PRODUCT"} or tok.pos_ == "PROPN":
                val = tok.text.strip().lower()
                if 2 <= len(val) <= 30 and re.search(r"[A-Za-z#\+\-\.]", val):
                    skills.add(val)
    skills |= set(simple_skill_extract(text))
    return sorted(skills)


def jd_similarity(resume_text, jd_text):
    if not jd_text.strip():
        return 0.0
    if SKLEARN_OK:
        vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        X = vec.fit_transform([resume_text, jd_text])
        return round(float(cosine_similarity(X[0:1], X[1:2])[0][0]) * 100, 2)
    r, j = set(resume_text.lower().split()), set(jd_text.lower().split())
    return round(100 * len(r & j) / len(j), 2) if j else 0.0


def score_roles(skills_lower, roles_dict, target_role=None):
    scores, missing = [], set()
    for role, data in roles_dict.items():
        req = set(k.lower() for k in data.get("required", []))
        opt = set(k.lower() for k in data.get("optional", []))
        hits_req, hits_opt = req & skills_lower, opt & skills_lower
        req_score = len(hits_req) / len(req) if req else 0
        opt_score = len(hits_opt) / len(opt) if opt else 0
        final = 0.7 * req_score + 0.3 * opt_score
        scores.append((role, round(final * 100, 2)))
        missing |= (req - skills_lower)
    scores.sort(key=lambda x: x[1], reverse=True)
    rec_roles = [r for r, s in scores if s >= 40][:3] or [r for r, _ in scores[:3]]
    if target_role and target_role not in rec_roles:
        rec_roles.insert(0, target_role)
    return {
        "ats_score": scores[0][1] if scores else 0,
        "recommended_roles": rec_roles,
        "role_scores": scores[:6],
        "missing_skills": sorted(list(missing))[:12],
    }


def save_history(entry):
    """Append analysis results to history.json"""
    HISTORY_FILE.touch(exist_ok=True)
    data = []
    try:
        if HISTORY_FILE.stat().st_size > 0:
            data = json.loads(HISTORY_FILE.read_text())
    except Exception:
        pass
    data.insert(0, entry)  # newest first
    HISTORY_FILE.write_text(json.dumps(data[:50], indent=2))


def load_history():
    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except Exception:
        return []


def generate_pdf(report_id, analysis, meta):
    """Generate PDF summary report in /uploads"""
    pdf_path = UPLOADS / f"{report_id}.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 22)
    c.drawString(60, h - 80, "HireSense Pro — Resume Analysis Report")
    c.setFont("Helvetica", 12)
    c.drawString(60, h - 110, f"File: {meta.get('filename', 'N/A')}")
    c.drawString(60, h - 130, f"Date: {meta.get('uploaded_at', '')}")
    if meta.get("target_role"):
        c.drawString(60, h - 150, f"Target Role: {meta['target_role']}")

    # ATS + JD Scores
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.darkblue)
    c.drawString(60, h - 190, f"ATS Score: {analysis['ats_score']}%")
    c.setFillColor(colors.darkgreen)
    c.drawString(200, h - 190, f"JD Match: {analysis['jd_match']}%")
    c.setFillColor(colors.black)

    # Recommended Roles
    c.setFont("Helvetica-Bold", 13)
    c.drawString(60, h - 220, "Recommended Roles:")
    c.setFont("Helvetica", 12)
    y = h - 240
    for r in analysis["recommended_roles"]:
        c.drawString(80, y, f"• {r}")
        y -= 18

    # Missing Skills
    y -= 10
    c.setFont("Helvetica-Bold", 13)
    c.drawString(60, y, "Top Missing Skills:")
    c.setFont("Helvetica", 12)
    y -= 20
    for s in analysis["missing_skills"]:
        c.drawString(80, y, f"• {s}")
        y -= 16

    # Footer
    c.setFont("Helvetica-Oblique", 10)
    c.setFillColor(colors.grey)
    c.drawString(60, 40, "Generated by HireSense Pro v3 — AI Resume Analyzer (Local Mode)")
    c.save()
    return pdf_path


# -----------------------------
# Flask Application
# -----------------------------
def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "hire-sense-v3"
    app.config["UPLOAD_FOLDER"] = str(UPLOADS)

    @app.route("/")
    def index():
        return render_template("index.html", roles=list(ROLE_KEYWORDS.keys()))

    @app.route("/upload")
    def upload_page():
        return render_template("upload.html", roles=list(ROLE_KEYWORDS.keys()))

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/history")
    def history_page():
        history = load_history()
        return render_template("history.html", history=history)

    @app.route("/analyze", methods=["POST"])
    def analyze():
        jd_text = request.form.get("job_description", "").strip()
        target_role = request.form.get("target_role") or None

        if "resume" not in request.files:
            flash("No file part")
            return redirect(url_for("upload_page"))
        file = request.files["resume"]
        if not file.filename:
            flash("No selected file")
            return redirect(url_for("upload_page"))
        if not allowed_file(file.filename):
            flash("Unsupported file type.")
            return redirect(url_for("upload_page"))

        filename = secure_filename(file.filename)
        save_path = UPLOADS / filename
        file.save(str(save_path))

        raw_text = extract_text_from_file(str(save_path))
        clean_text = normalize_text(raw_text)
        skills = extract_skills(clean_text)
        scores = score_roles(set(skills), ROLE_KEYWORDS, target_role)
        jd_score = jd_similarity(clean_text, jd_text)

        analysis = {**scores, "extracted_skills": skills[:60], "jd_match": jd_score, "target_role": target_role or ""}
        meta = {
            "id": str(uuid.uuid4())[:8],
            "filename": filename,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "target_role": target_role or "",
        }

        save_history({**meta, **analysis})
        pdf_path = generate_pdf(meta["id"], analysis, meta)
        session["analysis"], session["meta"] = analysis, meta

        flash("Analysis completed successfully!")
        return redirect(url_for("result"))

    @app.route("/result")
    def result():
        analysis = session.get("analysis")
        meta = session.get("meta")
        if not analysis:
            return redirect(url_for("upload_page"))
        return render_template("result.html", analysis=analysis, meta=meta)

    @app.route("/download_report/<report_id>")
    def download_report(report_id):
        path = UPLOADS / f"{report_id}.pdf"
        if not path.exists():
            flash("Report not found")
            return redirect(url_for("history_page"))
        return send_file(str(path), as_attachment=True)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=True)
