"""
app.py  —  Flask web dashboard for the AI Resume Portfolio Generator
Run locally:  python app.py
Deploy:       Render.com / Railway / PythonAnywhere
"""

import os
import re
import json
import time
import requests
import tempfile
from pathlib import Path
from flask import (Flask, render_template, request,
                   jsonify, send_file, session)

# ── Load .env ───────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Gemini SDK ───────────────────────────────────────────────────────────────
_USE_NEW_SDK = False
try:
    import google.genai as genai
    _USE_NEW_SDK = True
except ImportError:
    try:
        import google.generativeai as genai_legacy
    except ImportError:
        genai_legacy = None

# ── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "portfolio-generator-2026")

# ── Paths & config ───────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
TEMPLATE_FILE = BASE_DIR / "template.html"
CSS_FILE      = BASE_DIR / "style.css"
MODEL_NAME    = "gemini-3.6-flash"
MIN_CHARS     = 80
MAX_RETRIES   = 4          # retry up to 4 times on 503
RETRY_DELAYS  = [3, 6, 12, 20]  # seconds between retries (exponential)

# ── Gemini prompt ────────────────────────────────────────────────────────────
PROMPT_TEMPLATE = """
You are a professional portfolio content writer.
Read the resume below and extract the information into the JSON structure specified.

STRICT RULES:
- Use ONLY information present in the resume.
- Do NOT invent skills, projects, companies, dates, achievements, or links.
- If a field has no information, use an empty string "" or empty list [].
- Make the professional_summary highly engaging, extremely positive, and impactful. Use strong action verbs and highlight their best qualities to impress recruiters and HR professionals. (3-4 sentences).
- For the headline, make it a catchy, professional title (e.g., "Passionate Full-Stack Developer & Problem Solver").
- Return VALID JSON ONLY -- no markdown fences, no extra explanation.

REQUIRED JSON STRUCTURE:
{{
  "name": "",
  "headline": "",
  "professional_summary": "",
  "email": "",
  "phone": "",
  "linkedin": "",
  "github": "",
  "skills": [],
  "education": [
    {{"degree": "", "institution": "", "year": "", "grade": ""}}
  ],
  "experience": [
    {{"title": "", "company": "", "duration": "", "responsibilities": []}}
  ],
  "projects": [
    {{"name": "", "description": "", "technologies": [], "role": ""}}
  ],
  "achievements": [],
  "certifications": [],
  "interests": []
}}

RESUME:
{resume}
"""

# ════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ════════════════════════════════════════════════════════════════════════════
def clean_text(text: str) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def call_gemini(resume_text: str) -> dict:
    """Call Gemini with automatic retry on 503 (high demand) errors."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured on this server.")

    prompt = PROMPT_TEMPLATE.format(resume=resume_text)

    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            raw_text = ""
            if _USE_NEW_SDK:
                client   = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=MODEL_NAME, contents=prompt
                )
                raw_text = response.text.strip()
            elif genai_legacy:
                genai_legacy.configure(api_key=api_key)
                model    = genai_legacy.GenerativeModel(MODEL_NAME)
                response = model.generate_content(prompt)
                raw_text = response.text.strip()
            else:
                raise RuntimeError("No Gemini SDK installed. Run: pip install google-genai")

            # Strip accidental markdown fences
            raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
            raw_text = re.sub(r"\s*```$", "", raw_text)

            return json.loads(raw_text)

        except json.JSONDecodeError as e:
            raise ValueError(f"Gemini returned invalid JSON: {e}")

        except Exception as e:
            err_str   = str(e)
            last_error = err_str

            # Retry only on 503 (server overload) or rate limit errors
            is_retryable = any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])
            if is_retryable and attempt < MAX_RETRIES - 1:
                wait = RETRY_DELAYS[attempt]
                print(f"[retry {attempt+1}/{MAX_RETRIES}] Gemini busy — waiting {wait}s...")
                time.sleep(wait)
                continue

            # Non-retryable or final attempt — raise
            raise RuntimeError(err_str)

    raise RuntimeError(f"Gemini failed after {MAX_RETRIES} retries: {last_error}")


def assess_profile(data: dict) -> str:
    score  = min(len(data.get("achievements", [])) * 2, 6)
    score += min(len(data.get("projects", [])) * 2, 6)
    score += min(len(data.get("experience", [])) * 2, 4)
    score += min(len(data.get("certifications", [])), 3)
    for edu in data.get("education", []):
        g = edu.get("grade", "").lower()
        if any(x in g for x in ["9", "10", "distinction", "first class"]):
            score += 3
        elif any(x in g for x in ["8", "7.5", "merit"]):
            score += 2
        elif any(x in g for x in ["7", "6.5"]):
            score += 1
    score = min(score, 22)
    if score >= 12:
        return "strong", score
    elif score >= 6:
        return "mediocre", score
    return "weak", score


def _list_items(items, cls="tag"):
    return "".join(f'<span class="{cls}">{i}</span>' for i in items) if items else ""

def _skills_items(items):
    out = ""
    for i in items:
        out += f'<span class="skill-pill"><span class="skill-dot"></span>{i}</span>'
    return out

def _bullets(items):
    return '<ul class="timeline-resp">' + "".join(f"<li>{i}</li>" for i in items) + "</ul>" if items else ""

def _edu_cards(lst):
    cards = []
    for e in lst:
        grade_html = f'<span class="grade-badge">{e.get("grade","")}</span>' if e.get("grade") else ""
        cards.append(f"""
        <div class="edu-card">
          <div>
            <h3 class="edu-degree">{e.get('degree','')}</h3>
            <p class="edu-inst">{e.get('institution','')}</p>
          </div>
          <div class="edu-right">{grade_html}
            <span class="year-badge">{e.get('year','')}</span>
          </div>
        </div>""")
    return "".join(cards)

def _exp_cards(lst):
    cards = []
    for e in lst:
        cards.append(f"""
        <div class="timeline-item">
          <div class="timeline-left">
            <div class="timeline-dot"></div>
            <div class="timeline-line"></div>
          </div>
          <div class="timeline-content">
            <div class="timeline-header">
              <div>
                <h3 class="timeline-title">{e.get('title','')}</h3>
                <p class="timeline-company">{e.get('company','')}</p>
              </div>
              <span class="year-badge">{e.get('duration','')}</span>
            </div>
            {_bullets(e.get('responsibilities',[]))}
          </div>
        </div>""")
    return "".join(cards)

def _proj_cards(lst):
    cards = []
    for p in lst:
        techs = _list_items(p.get("technologies", []), "tech-tag")
        role  = f'<p class="project-role">Role: {p.get("role","")}</p>' if p.get("role") else ""
        cards.append(f"""
        <div class="project-card">
          <div class="project-header"></div>
          <div class="project-body">
            <h3 class="project-title">{p.get('name','')}</h3>
            <p class="project-desc">{p.get('description','')}</p>
            {role}
            <div class="tech-tags">{techs}</div>
          </div>
        </div>""")
    return "".join(cards)

def _ach_items(lst):
    return "".join(f"""
        <div class="achievement-row">
          <i class="fa-solid fa-star ach-icon" style="color: var(--accent)"></i>
          <span class="ach-text">{i}</span>
        </div>""" for i in lst)

def _cert_items(lst):
    return "".join(f"""
        <span class="cert-pill">
          <i class="fa-solid fa-certificate"></i> {i}
        </span>""" for i in lst)

def _hide_empty(html):
    pat = re.compile(r'<section[^>]*data-optional="true"[^>]*>(.*?)</section>', re.DOTALL)
    def _check(m):
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        return "" if not text else m.group(0)
    return pat.sub(_check, html)


def render_portfolio(data: dict, profile: str) -> str:
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    css_content = CSS_FILE.read_text(encoding="utf-8")
    
    # Embed CSS directly into template.html instead of linking it
    template = template.replace('<link rel="stylesheet" href="style.css" />', f'<style>\n{css_content}\n</style>')

    tone_cls = {"strong": "tone-strong", "mediocre": "tone-mediocre", "weak": "tone-weak"}.get(profile, "tone-strong")

    if profile != "strong":
        for edu in data.get("education", []):
            edu["grade"] = ""
        if profile == "weak":
            data["achievements"] = []
            data["education"] = []

    name = data.get("name", "Your Name")
    initials = "".join(w[0] for w in name.split()[:2]).upper() if name else "?"

    replacements = {
        "{{NAME}}":           name,
        "{{INITIAL}}":        initials,
        "{{HEADLINE}}":       data.get("headline", ""),
        "{{SUMMARY}}":        data.get("professional_summary", ""),
        "{{EMAIL}}":          data.get("email", ""),
        "{{PHONE}}":          data.get("phone", ""),
        "{{LINKEDIN}}":       data.get("linkedin", ""),
        "{{GITHUB}}":         data.get("github", ""),
        "{{SKILLS}}":         _skills_items(data.get("skills", [])),
        "{{EDUCATION}}":      _edu_cards(data.get("education", [])),
        "{{EXPERIENCE}}":     _exp_cards(data.get("experience", [])),
        "{{PROJECTS}}":       _proj_cards(data.get("projects", [])),
        "{{ACHIEVEMENTS}}":   _ach_items(data.get("achievements", [])),
        "{{CERTIFICATIONS}}": _cert_items(data.get("certifications", [])),
        "{{INTERESTS}}":      _list_items(data.get("interests", []), "tag"),
        "{{TONE_CLASS}}":     tone_cls,
        "{{PROFILE_LEVEL}}":  profile.upper(),
    }
    html = template
    for k, v in replacements.items():
        html = html.replace(k, str(v) if v else "")
    return _hide_empty(html)


def deploy_to_vercel(html_content: str, name: str) -> str:
    token = os.environ.get("VERCEL_TOKEN")
    if not token:
        return ""
    
    clean_name = re.sub(r'[^a-z0-9-]', '-', name.lower().strip())
    if not clean_name: clean_name = "portfolio"
    project_name = f"{clean_name}-folio"

    url = "https://api.vercel.com/v13/deployments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": project_name,
        "files": [
            {
                "file": "index.html",
                "data": html_content
            }
        ],
        "target": "production",
        "projectSettings": {
            "framework": None
        }
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return f"https://{data.get('url')}"
        return ""
    except:
        return ""

# ════════════════════════════════════════════════════════════════════════════
# Routes
# ════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("dashboard.html")


@app.route("/generate", methods=["POST"])
def generate():
    """Receive uploaded .txt file, call Gemini, return portfolio HTML."""
    if "resume" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["resume"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    # Read text
    try:
        raw = file.read().decode("utf-8", errors="replace").strip()
    except Exception as e:
        return jsonify({"error": f"Could not read file: {e}"}), 400

    if not raw:
        return jsonify({"error": "The uploaded file is empty."}), 400
    if len(raw) < MIN_CHARS:
        return jsonify({"error": f"File is too short ({len(raw)} chars). Please upload a complete resume."}), 400

    cleaned = clean_text(raw)

    # Call Gemini (with auto-retry built in)
    try:
        data = call_gemini(cleaned)
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "Gemini returned invalid JSON. Please click Generate again."}), 500
    except RuntimeError as e:
        err = str(e)
        if "503" in err or "UNAVAILABLE" in err or "retries" in err:
            return jsonify({
                "error": "Gemini servers are very busy right now. Please wait 10 seconds and click Generate again — it will work!"
            }), 503
        return jsonify({"error": f"API error: {err}"}), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    # Assess & render
    profile, score = assess_profile(data)
    portfolio_html = render_portfolio(data, profile)
    
    # Auto-deploy to Vercel
    live_url = deploy_to_vercel(portfolio_html, data.get("name", "portfolio"))

    return jsonify({
        "success": True,
        "name":    data.get("name", "Your Portfolio"),
        "profile": profile,
        "score":   score,
        "html":    portfolio_html,
        "json":    data,
        "live_url": live_url
    })


@app.route("/download", methods=["POST"])
def download():
    """Return the portfolio HTML as a downloadable file."""
    html_content = request.form.get("html", "")
    name         = request.form.get("name", "portfolio").replace(" ", "_")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8")
    tmp.write(html_content)
    tmp.close()

    return send_file(
        tmp.name,
        as_attachment=True,
        download_name=f"{name}_portfolio.html",
        mimetype="text/html"
    )


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    print(f"Dashboard running at: http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
