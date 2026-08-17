# AI-Assisted Resume Portfolio Generator

> **Group Project** &nbsp;|&nbsp; Python + Gemini API + JSON + HTML + CSS  
> Duration: 3 weeks &nbsp;|&nbsp; Group size: 5 students

A Python application that reads a plain-text resume, sends it to the **Google Gemini API**, receives structured **JSON** data, and automatically generates a styled **HTML portfolio webpage**.

---

## Table of Contents

1. [Project Overview](#-project-overview)
2. [Screenshots](#-screenshots)
3. [Setup — Step-by-Step](#-setup--step-by-step)
4. [How to Run](#-how-to-run)
5. [Project Workflow](#-project-workflow)
6. [File Structure](#-file-structure)
7. [Portfolio Tone System](#-portfolio-tone-system)
8. [Prompt Design](#-prompt-design)
9. [Responsible AI & Privacy](#-responsible-ai--privacy)
10. [Testing Results](#-testing-results)
11. [AI Usage Log](#-ai-usage-log)
12. [Deploy to Vercel (Free Hosting)](#-deploy-to-vercel-free-hosting)
13. [Limitations & Hallucination Risks](#-limitations--hallucination-risks)
14. [Team](#-team)

---

## Project Overview

```
resume.txt  →  main.py  →  Gemini API  →  portfolio_data.json  →  portfolio.html
```

One resume text file goes in → one beautiful portfolio HTML file comes out.

---

## Screenshots

> Add screenshots here after running the project.  
> Place them in a `screenshots/` folder and reference like:
> `![Portfolio](screenshots/portfolio.png)`

---

## Setup — Step-by-Step

### Step 1 — Prerequisites

Make sure you have **Python 3.9 or higher** installed.

```bash
python --version
```

### Step 2 — Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/resume-portfolio-generator.git
cd resume-portfolio-generator
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `google-genai` — Gemini API client
- `python-dotenv` — loads `.env` file automatically

### Step 4 — Get a Gemini API key (FREE)

1. Go to **[Google AI Studio](https://aistudio.google.com/app/apikey)**
2. Sign in with your Google account
3. Click **"Create API key"**
4. Copy the key (starts with `AIza...`)

> The free tier is enough for this project — no credit card needed.

### Step 5 — Set up your API key

Copy the example env file and add your key:

```bash
# Windows (PowerShell)
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

Open `.env` and replace the placeholder:

```
GEMINI_API_KEY=AIzaSyYour_Real_Key_Here
```

> **NEVER upload your `.env` file to GitHub.** It is already listed in `.gitignore`.

### Step 6 — Add your resume

Open `resume.txt` and replace the sample content with **your own resume**.

The file should contain plain text — no special formatting needed.

---

## How to Run

```bash
python main.py
```

That's it. The program will:

1. Read and validate `resume.txt`
2. Call the Gemini API
3. Parse the JSON response
4. Assess your profile strength
5. Generate `portfolio.html`

Then open `portfolio.html` in any browser.

---

## Project Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  1. Read resume.txt                                         │
│     - Validate: exists, not empty, >= 100 chars             │
│     - Clean: remove extra blank lines, trailing whitespace  │
├─────────────────────────────────────────────────────────────┤
│  2. Build structured prompt                                 │
│     - Include cleaned resume text                           │
│     - Specify exact JSON schema                             │
│     - Instruct Gemini NOT to invent information             │
├─────────────────────────────────────────────────────────────┤
│  3. Call Gemini API (gemini-2.0-flash)                      │
│     - Handle API errors gracefully                          │
│     - Strip accidental markdown fences                      │
│     - Parse JSON safely                                     │
├─────────────────────────────────────────────────────────────┤
│  4. Assess profile strength                                 │
│     - Score: achievements, projects, experience, certs      │
│     - Result: strong / mediocre / weak                      │
│     - Drives portfolio tone and what is displayed           │
├─────────────────────────────────────────────────────────────┤
│  5. Render HTML from template.html                          │
│     - Replace {{PLACEHOLDERS}} with content                 │
│     - Hide empty optional sections automatically            │
│     - Apply tone-aware CSS class                            │
├─────────────────────────────────────────────────────────────┤
│  6. Save portfolio.html                                     │
│     - Also saves portfolio_data.json for verification       │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
resume-portfolio-generator/
├── main.py               ← Core application
├── render_only.py        ← Render HTML from existing JSON (no API call)
├── resume.txt            ← Your resume input
├── template.html         ← HTML portfolio template
├── style.css             ← Dark theme CSS
├── requirements.txt      ← Python dependencies
├── README.md             ← This file
├── .gitignore            ← Excludes .env, portfolio.html, __pycache__
├── .env.example          ← API key template (safe to commit)
├── .env                  ← Your real API key (NEVER commit this)
├── portfolio.html        ← Generated output (git-ignored)
└── portfolio_data.json   ← Generated JSON (for verification)
```

---

## Portfolio Tone System

The program automatically scores your profile and adapts the portfolio:

| Profile Score | Tone | Behaviour |
|---|---|---|
| ≥ 12 / 22 | **STRONG** (blue) | Standard high-quality portfolio, shows grades |
| 6 – 11 | **MEDIOCRE** (green) | Downplays grades, highlights skills & projects |
| < 6 | **WEAK** (orange) | Hides results entirely, focuses on skills learned |

Scoring factors: achievements (+2 each, max 6), projects (+2 each, max 6), experience (+2 each, max 4), certifications (+1 each, max 3), education grade (+1–3).

---

## Prompt Design

The Gemini prompt follows these principles:

- **Strict grounding**: "Use ONLY information present in the resume."
- **No hallucination**: "Do NOT invent skills, projects, companies, dates, or links."
- **Structured output**: Defines the exact JSON schema including all required fields.
- **Graceful missing data**: "Use empty string or empty list for missing fields."
- **Format control**: "Return valid JSON ONLY — no markdown fences."

The prompt is stored as `PROMPT_TEMPLATE` in `main.py` and can be modified to improve output quality.

---

## Responsible AI & Privacy

- **Do not include** passwords, government IDs, financial information, or highly sensitive data in `resume.txt`.
- **Never upload** the real API key (`.env`) to GitHub.
- **Every generated claim** must be verified against the original resume before submission.
- **Browser-side key exposure**: The Python program calls the API server-side. The API key is never in the HTML or JavaScript.

---

## Testing Results

| Test Case | Expected Behaviour | Result |
|---|---|---|
| Missing `resume.txt` | Clear error, safe exit | PASS |
| Empty `resume.txt` | Reject with message | PASS |
| Resume < 100 chars | Reject with message | PASS |
| Valid full resume | Generate `portfolio.html` | PASS |
| Resume with missing sections | Generate available sections | PASS |
| Missing API key | Configuration error message | PASS |
| Invalid JSON from API | Parse error, safe exit | PASS |

To run any test case manually:

```bash
# Test missing file
python -c "import main; main.read_resume('nonexistent.txt')"

# Test empty file
echo "" > resume.txt && python main.py
```

---

## AI Usage Log

| Tool Used | Prompt Given | What It Generated | Changes Made |
|---|---|---|---|
| Antigravity (Gemini) | "Build a complete AI portfolio generator project based on the project brief..." | Full Python, HTML, CSS, README | Reviewed all logic, fixed SDK version, fixed Windows encoding |
| Gemini API (runtime) | Structured resume-to-JSON prompt | Portfolio JSON data | Verified all fields match the resume |

---

## Deploy to Vercel (Free Hosting)

Since `portfolio.html` is a **static file**, you can host it for free on **Vercel** in a few steps.

### Step 1 — Install Vercel CLI

```bash
npm install -g vercel
```

> You need Node.js installed. Get it from [nodejs.org](https://nodejs.org).

### Step 2 — Login to Vercel

```bash
vercel login
```

Follow the link in your email.

### Step 3 — Deploy

```bash
cd resume-portfolio-generator
vercel --prod
```

When asked:
- **Set up and deploy?** → Yes
- **Project name** → (press Enter for default)
- **Which directory?** → `./` (current folder)
- **Override settings?** → No

Vercel will give you a **public URL** like `https://your-portfolio.vercel.app` that anyone can open.

### Step 4 — Redeploy after changes

After regenerating `portfolio.html`:

```bash
vercel --prod
```

> **Note**: Make sure `.gitignore` does NOT exclude `portfolio.html` when deploying. For Vercel deployment only, you can temporarily remove `portfolio.html` from `.gitignore`.

---

## Limitations & Hallucination Risks

1. **Gemini may hallucinate** despite the strict prompt — always verify every generated field against the original resume.
2. **Missing information**: If the resume is vague, Gemini may generate generic placeholder text. Review `portfolio_data.json` before sharing.
3. **JSON format errors**: Occasionally Gemini may return malformed JSON on unusual resume formats. The program handles this with a clear error message.
4. **API rate limits**: The free Gemini tier has rate limits. If you get an error, wait 60 seconds and try again.
5. **Unicode/encoding**: The program forces UTF-8 output. Make sure your resume.txt is saved as UTF-8.

---

## Team

| Name | Role |
|---|---|
| Shivam Kumar | Team Lead — Prompt Design, JSON Parsing, HTML Template |
| Member 2 | Python Input Pipeline, Validation |
| Member 3 | CSS Styling, Portfolio Tone System |
| Member 4 | Testing, Error Handling |
| Member 5 | README, GitHub Setup, Deployment |

---

*Generated portfolio is a draft. All content must be verified against the original resume before sharing.*
