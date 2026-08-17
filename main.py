"""
AI-Assisted Resume Portfolio Generator
Group Project -- Python + Gemini API + JSON + HTML + CSS
"""

import os
import json
import sys
import re
from pathlib import Path

# Force UTF-8 output so emoji work on Windows PowerShell
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ------------------------------------------------------------------ Load .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv optional; key can be set as a real env variable

# ----------------------------------------------------------- Gemini SDK import
# Prefer new google-genai SDK; fall back to legacy google-generativeai
_USE_NEW_SDK = False
try:
    import google.genai as genai                    # new SDK
    from google.genai import types as genai_types
    _USE_NEW_SDK = True
except ImportError:
    try:
        import google.generativeai as genai_legacy  # legacy SDK
    except ImportError:
        print("ERROR: Neither google-genai nor google-generativeai is installed.")
        print("  Run:  pip install google-genai")
        sys.exit(1)

# ------------------------------------------------------------------ Constants
RESUME_FILE   = "resume.txt"
OUTPUT_FILE   = "portfolio.html"
TEMPLATE_FILE = "template.html"
MODEL_NAME    = "gemini-3.6-flash"
MIN_CHARS     = 100


# ===========================================================================
# STEP 1 -- Read and validate resume.txt
# ===========================================================================
def read_resume(path: str) -> str:
    """Read, validate, and clean the resume text file."""
    p = Path(path)

    if not p.exists():
        print(f"ERROR: '{path}' not found.")
        print("  Please create a file named resume.txt in this folder.")
        sys.exit(1)

    raw = p.read_text(encoding="utf-8").strip()

    if not raw:
        print(f"ERROR: '{path}' is empty. Please add your resume content.")
        sys.exit(1)

    if len(raw) < MIN_CHARS:
        print(f"ERROR: '{path}' is too short ({len(raw)} chars).")
        print(f"  The resume must contain at least {MIN_CHARS} characters.")
        sys.exit(1)

    # Clean: collapse multiple blank lines, strip trailing whitespace per line
    cleaned = "\n".join(line.rstrip() for line in raw.splitlines())
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    print(f"[OK] Resume loaded -- {len(cleaned)} characters")
    return cleaned


# ===========================================================================
# STEP 2 -- Build prompt and call Gemini
# ===========================================================================
PROMPT_TEMPLATE = """
You are a professional portfolio content writer.
Read the resume below and extract the information into the JSON structure specified.

STRICT RULES:
- Use ONLY information present in the resume.
- Do NOT invent skills, projects, companies, dates, achievements, or links.
- If a field has no information, use an empty string "" or empty list [].
- Keep the professional_summary concise (2-3 sentences, factual).
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
    {{
      "degree": "",
      "institution": "",
      "year": "",
      "grade": ""
    }}
  ],
  "experience": [
    {{
      "title": "",
      "company": "",
      "duration": "",
      "responsibilities": []
    }}
  ],
  "projects": [
    {{
      "name": "",
      "description": "",
      "technologies": [],
      "role": ""
    }}
  ],
  "achievements": [],
  "certifications": [],
  "interests": []
}}

RESUME:
{resume}
"""


def call_gemini(resume_text: str) -> dict:
    """Send resume to Gemini, receive and parse JSON portfolio data."""

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY is not set.")
        print("  Create a .env file with: GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    print("[..] Connecting to Gemini API ...")
    prompt = PROMPT_TEMPLATE.format(resume=resume_text)

    raw_text = ""
    try:
        if _USE_NEW_SDK:
            client   = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
            raw_text = response.text.strip()
        else:
            genai_legacy.configure(api_key=api_key)
            model    = genai_legacy.GenerativeModel(MODEL_NAME)
            response = model.generate_content(prompt)
            raw_text = response.text.strip()
    except Exception as e:
        print(f"ERROR during API call: {e}")
        sys.exit(1)

    # Strip accidental markdown code fences
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    try:
        data = json.loads(raw_text)
        print("[OK] Gemini responded with valid JSON")
        return data
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON parse failed: {e}")
        print("Raw response preview (first 500 chars):")
        print(raw_text[:500])
        sys.exit(1)


# ===========================================================================
# STEP 3 -- Assess profile strength (drives portfolio tone)
# ===========================================================================
def assess_profile(data: dict) -> str:
    """
    Return 'strong', 'mediocre', or 'weak' based on resume signals.
    Controls how the portfolio is styled and what it emphasises.
    """
    score = 0

    score += min(len(data.get("achievements", [])) * 2, 6)
    score += min(len(data.get("projects", [])) * 2, 6)
    score += min(len(data.get("experience", [])) * 2, 4)
    score += min(len(data.get("certifications", [])), 3)

    for edu in data.get("education", []):
        grade = edu.get("grade", "").lower()
        if any(x in grade for x in ["9", "10", "distinction", "first class"]):
            score += 3
        elif any(x in grade for x in ["8", "7.5", "merit"]):
            score += 2
        elif any(x in grade for x in ["7", "6.5"]):
            score += 1

    print(f"[..] Profile score: {score}/22")

    if score >= 12:
        return "strong"
    elif score >= 6:
        return "mediocre"
    else:
        return "weak"


# ===========================================================================
# STEP 4 -- Load template
# ===========================================================================
def load_template() -> str:
    p = Path(TEMPLATE_FILE)
    if not p.exists():
        print(f"ERROR: '{TEMPLATE_FILE}' not found.")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


# ===========================================================================
# STEP 5 -- Render portfolio data into HTML
# ===========================================================================
def _list_items(items: list, cls: str = "tag") -> str:
    if not items:
        return ""
    return "".join(f'<span class="{cls}">{item}</span>' for item in items)


def _bullet_items(items: list) -> str:
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _education_cards(edu_list: list) -> str:
    if not edu_list:
        return ""
    cards = []
    for edu in edu_list:
        grade_html = (
            f'<span class="grade-badge">{edu.get("grade","")}</span>'
            if edu.get("grade") else ""
        )
        cards.append(f"""
        <div class="card edu-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">{edu.get('degree','')}</h3>
              <p class="card-sub">{edu.get('institution','')}</p>
            </div>
            <div class="card-meta">
              {grade_html}
              <span class="year-badge">{edu.get('year','')}</span>
            </div>
          </div>
        </div>""")
    return "".join(cards)


def _experience_cards(exp_list: list) -> str:
    if not exp_list:
        return ""
    cards = []
    for exp in exp_list:
        resp = _bullet_items(exp.get("responsibilities", []))
        cards.append(f"""
        <div class="card exp-card">
          <div class="card-header">
            <div>
              <h3 class="card-title">{exp.get('title','')}</h3>
              <p class="card-sub">{exp.get('company','')}</p>
            </div>
            <span class="year-badge">{exp.get('duration','')}</span>
          </div>
          {resp}
        </div>""")
    return "".join(cards)


def _project_cards(proj_list: list) -> str:
    if not proj_list:
        return ""
    cards = []
    for proj in proj_list:
        techs = _list_items(proj.get("technologies", []), "tech-tag")
        role  = (
            f'<p class="role-badge">Role: {proj.get("role","")}</p>'
            if proj.get("role") else ""
        )
        cards.append(f"""
        <div class="card project-card">
          <h3 class="card-title">{proj.get('name','')}</h3>
          <p class="card-desc">{proj.get('description','')}</p>
          {role}
          <div class="tech-stack">{techs}</div>
        </div>""")
    return "".join(cards)


def _achievement_items(items: list) -> str:
    if not items:
        return ""
    return "".join(f"""
        <div class="achievement-item">
          <span class="ach-icon">&#127942;</span>
          <span>{item}</span>
        </div>""" for item in items)


def _cert_items(items: list) -> str:
    if not items:
        return ""
    return "".join(f"""
        <div class="cert-item">
          <span class="cert-icon">&#128220;</span>
          <span>{item}</span>
        </div>""" for item in items)


def render_html(template: str, data: dict, profile: str) -> str:
    """Inject portfolio data into the HTML template."""

    tone_class = {
        "strong":   "tone-strong",
        "mediocre": "tone-mediocre",
        "weak":     "tone-weak",
    }.get(profile, "tone-strong")

    # Hide education grade for non-strong profiles
    if profile != "strong":
        for edu in data.get("education", []):
            edu["grade"] = ""

    replacements = {
        "{{NAME}}":           data.get("name", ""),
        "{{HEADLINE}}":       data.get("headline", ""),
        "{{SUMMARY}}":        data.get("professional_summary", ""),
        "{{EMAIL}}":          data.get("email", ""),
        "{{PHONE}}":          data.get("phone", ""),
        "{{LINKEDIN}}":       data.get("linkedin", ""),
        "{{GITHUB}}":         data.get("github", ""),
        "{{SKILLS}}":         _list_items(data.get("skills", []), "tag"),
        "{{EDUCATION}}":      _education_cards(data.get("education", [])),
        "{{EXPERIENCE}}":     _experience_cards(data.get("experience", [])),
        "{{PROJECTS}}":       _project_cards(data.get("projects", [])),
        "{{ACHIEVEMENTS}}":   _achievement_items(data.get("achievements", [])),
        "{{CERTIFICATIONS}}": _cert_items(data.get("certifications", [])),
        "{{INTERESTS}}":      _list_items(data.get("interests", []), "tag"),
        "{{TONE_CLASS}}":     tone_class,
        "{{PROFILE_LEVEL}}":  profile.upper(),
    }

    html = template
    for key, value in replacements.items():
        html = html.replace(key, str(value) if value is not None else "")

    html = _hide_empty_sections(html)
    return html


def _hide_empty_sections(html: str) -> str:
    """Remove optional sections whose content resolved to nothing."""
    pattern = re.compile(
        r'<section[^>]*data-optional="true"[^>]*>(.*?)</section>',
        re.DOTALL
    )
    def remove_if_empty(m):
        inner = m.group(1)
        text  = re.sub(r'<[^>]+>', '', inner).strip()
        return "" if not text else m.group(0)
    return pattern.sub(remove_if_empty, html)


# ===========================================================================
# STEP 6 -- Save portfolio.html
# ===========================================================================
def save_portfolio(html: str):
    Path(OUTPUT_FILE).write_text(html, encoding="utf-8")
    abs_path = Path(OUTPUT_FILE).resolve()
    print(f"[OK] Portfolio saved -> {OUTPUT_FILE}")
    print(f"     Open in browser: file:///{abs_path}")


# ===========================================================================
# MAIN
# ===========================================================================
def main():
    print("=" * 55)
    print("  AI-Assisted Resume Portfolio Generator")
    print("  Python + Gemini API")
    print("=" * 55)

    resume_text    = read_resume(RESUME_FILE)
    portfolio_data = call_gemini(resume_text)

    # Save raw JSON for inspection / verification
    json_path = Path("portfolio_data.json")
    json_path.write_text(json.dumps(portfolio_data, indent=2), encoding="utf-8")
    print(f"[..] Raw JSON saved -> {json_path}")

    profile  = assess_profile(portfolio_data)
    print(f"[..] Portfolio tone: {profile.upper()}")

    template = load_template()
    html     = render_html(template, portfolio_data, profile)
    save_portfolio(html)

    print("=" * 55)
    print("  Done! Open portfolio.html in your browser.")
    print("=" * 55)


if __name__ == "__main__":
    main()
