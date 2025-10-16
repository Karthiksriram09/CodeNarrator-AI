#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
HireSense Pro — Backend API (Flask)
- Pure JSON API (no HTML rendering)
- ATS scoring vs role keywords
- JD similarity (TF-IDF) with fallback
- Role insights (models/role_insights.json)
- History (JSON) + optional PDF report
"""

import os, json, re, uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

# --- Local utils (keep your existing utils folder) ---
from utils.parser import extract_text_from_file
from utils.text_clean import normalize_text, simple_skill_extract

# ---------- Paths ----------
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"
UPLOADS = BASE_DIR / "uploads"
DATA = BASE_DIR / "data"
HISTORY_FILE = DATA / "history.json"

for p in (UPLOADS, DATA):
    p.mkdir(exist_ok=True)

# ---------- Models / Config ----------
ROLES_JSON = MODELS_DIR / "roles_keywords.json"
ROLE_INSIGHTS_PATH = MODELS_DIR / "role_insights.json"
ROLE_KEYWORDS = json.loads(ROLES_JSON.read_text(encoding="utf-8"))
ROLE_INSIGHTS = json.loads(ROLE_INSIGHTS_PATH.read_text(encoding="utf-8"))

# Optional spaCy
try:
    import spacy
    NLP = spacy.load("en_core_web_sm")
except Exception:
    NLP = None

# Optional TF-IDF for JD matching
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_OK = True
except Exception:
    SKLEARN_OK = False

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---------- Core Logic ----------
def extract_skills(text: str):
    """Prefer spaCy noun/ent extraction when available; fallback to heuristics."""
    skills = set()
    if NLP:
        doc = NLP(text)
        for tok in doc:
            if tok.ent_type_ in {"ORG", "PRODUCT"} or tok.pos_ == "PROPN":
                token = tok.text.strip().lower()
                if 2 <= len(token) <= 30 and re.search(r"[A-Za-z#\+\-\.]", token):
                    skills.add(token)
    skills |= set(simple_skill_extract(text))
    return sorted(skills)

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
    if target_role and target_role not in rec_roles and any(r == target_role for r, _ in scores):
        rec_roles.insert(0, target_role)
    return {
        "ats_score": scores[0][1] if scores else 0,
        "recommended_roles": rec_roles,
        "role_scores": scores[:6],
        "missing_skills": sorted(list(missing))[:12],
    }

def jd_similarity(resume_text: str, jd_text: str) -> float:
    """Return 0-100 JD match score using TF-IDF cosine when available; else keyword overlap."""
    if not jd_text.strip():
        return 0.0
    if SKLEARN_OK:
        vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        X = vec.fit_transform([resume_text, jd_text])
        return round(float(cosine_similarity(X[0:1], X[1:2])[0][0]) * 100, 2)
    r, j = set(resume_text.lower().split()), set(jd_text.lower().split())
    return round(100 * len(r & j) / len(j), 2) if j else 0.0

def save_history(entry):
    HISTORY_FILE.touch(exist_ok=True)
    try:
        data = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.stat().st_size > 0 else []
    except Exception:
        data = []
    data.insert(0, entry)
    HISTORY_FILE.write_text(json.dumps(data[:100], indent=2))

def load_history():
    if not HISTORY_FILE.exists() or HISTORY_FILE.stat().st_size == 0:
        return []
    try:
        return json.loads(HISTORY_FILE.read_text())
    except Exception:
        return []

# ---------- App Factory ----------
def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "hire-sense-v4"
    app.config["UPLOAD_FOLDER"] = str(UPLOADS)
    CORS(app)  # allow requests from Vercel frontend

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/role_insights")
    def role_insights():
        return jsonify(ROLE_INSIGHTS)

    # JSON payload endpoint (resume plain text)
    @app.post("/analyze")
    def analyze():
        payload = request.get_json(silent=True) or {}
        resume_text = (payload.get("resume") or "").strip()
        jd_text = (payload.get("jd") or "").strip()
        target_role = payload.get("target_role") or None

        clean_text = normalize_text(resume_text)
        skills = extract_skills(clean_text)
        scores = score_roles(set(skills), ROLE_KEYWORDS, target_role)
        jd_score = jd_similarity(clean_text, jd_text)

        analysis = {
            **scores,
            "extracted_skills": skills[:60],
            "jd_match": jd_score,
            "target_role": target_role or "",
        }

        meta = {
            "id": str(uuid.uuid4())[:8],
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "json",
        }
        save_history({**meta, **analysis})
        return jsonify(analysis)

    # Multipart endpoint (file upload)
    @app.post("/analyze_file")
    def analyze_file():
        jd_text = (request.form.get("jd") or "").strip()
        target_role = request.form.get("target_role") or None

        if "resume" not in request.files:
            return jsonify({"error": "No file part 'resume'"}), 400

        f = request.files["resume"]
        if not f.filename:
            return jsonify({"error": "No selected file"}), 400
        if not allowed_file(f.filename):
            return jsonify({"error": "Unsupported file type. Upload PDF, DOCX, or TXT."}), 400

        filename = secure_filename(f.filename)
        save_path = UPLOADS / filename
        f.save(str(save_path))

        raw_text = extract_text_from_file(str(save_path))
        clean_text = normalize_text(raw_text)
        skills = extract_skills(clean_text)
        scores = score_roles(set(skills), ROLE_KEYWORDS, target_role)
        jd_score = jd_similarity(clean_text, jd_text)

        analysis = {
            **scores,
            "extracted_skills": skills[:60],
            "jd_match": jd_score,
            "target_role": target_role or "",
            "filename": filename,
        }

        meta = {
            "id": str(uuid.uuid4())[:8],
            "filename": filename,
            "uploaded_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": "file",
        }
        save_history({**meta, **analysis})
        return jsonify(analysis)

    @app.get("/history")
    def history():
        return jsonify(load_history())

    @app.get("/download/<report_id>")
    def download(report_id):
        # If you later generate PDFs, serve from uploads/
        path = UPLOADS / f"{report_id}.pdf"
        if path.exists():
            return send_file(str(path), as_attachment=True)
        return jsonify({"error": "Report not found"}), 404

    return app


if __name__ == "__main__":
    # For local dev. On Render use: gunicorn app:app
    create_app().run(host="0.0.0.0", port=10000, debug=True)
