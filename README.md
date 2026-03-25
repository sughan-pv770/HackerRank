# HackerRank — Online Coding Exam Platform 🚀

A futuristic, secure student coding test platform with live code execution, AI-powered complexity analysis, and advanced anti-cheat mechanisms.

---

## 🌐 Live Demo

Hosted on Railway → codex-testtt-production.up.railway.app

---

## ✨ Features

- 🖥️ **Live Code Execution** — Run and submit code in 5 languages instantly
- 🤖 **AI Complexity Analyzer** — Powered by HuggingFace LLMs (Time & Space complexity)
- 🛡️ **Anti-Cheat System** — Tab switch detection, fullscreen enforcement, DevTools detection
- 👨‍💼 **Admin Dashboard** — Create tests, manage students, view submissions
- 🎓 **Student Portal** — Attempt tests, view results, track progress
- 🔐 **JWT Authentication** — Secure login with role-based access

---

## 💻 Supported Languages

| Language   | Runtime         |
|------------|-----------------|
| Python     | python3         |
| JavaScript | Node.js         |
| Java       | JDK (javac + java) |
| C          | gcc             |
| C++        | g++             |

---

## 🚀 Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in with GitHub
2. Click **New Project** → **Deploy from GitHub repo**
3. Select this repository
4. Go to **Variables** tab and add:

| Variable | Description |
|---|---|
| `MONGO_URI` | Your MongoDB Atlas connection string |
| `JWT_SECRET_KEY` | A strong secret key for JWT tokens |
| `SECRET_KEY` | Flask secret key |
| `HF_API_TOKEN` | HuggingFace API token for complexity analysis |
| `FLASK_DEBUG` | Set to `false` for production |

5. Go to **Settings → Networking → Generate Domain** to get your public URL

Railway auto-detects the `Dockerfile` — no Procfile needed. ✅

---

## 🐳 Run Locally with Docker

```bash
# Clone the repo
git clone https://github.com/sughan-pv770/HackerRank.git
cd HackerRank

# Create your .env file (see Environment Variables below)
cp .env.example .env

# Build and run
docker build -t hackerrank .
docker run -p 5000:5000 --env-file .env hackerrank
```

App runs at **http://localhost:5000**

---

## ⚙️ Run Locally without Docker

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

> Make sure `python3`, `node`, `java`, `gcc`, `g++` are installed on your system.

---

## 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
MONGO_URI=mongodb+srv://<user>:<password>@<cluster>/<db>?retryWrites=true&w=majority
JWT_SECRET_KEY=your-secret-key-here
SECRET_KEY=flask-secret-key-here
HF_API_TOKEN=hf_...
FLASK_DEBUG=false
```

---

## 📁 Project Structure

```
HackerRank/
├── app.py                  # Flask app factory & routes
├── config.py               # Configuration (reads .env)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Installs all runtimes + starts gunicorn
├── executor/
│   └── sandbox.py          # Native multi-language code runner
├── routes/
│   ├── auth.py             # Login / Register
│   ├── submissions.py      # Run & Submit code
│   ├── complexity.py       # AI complexity analysis
│   ├── admin.py            # Admin APIs
│   ├── student.py          # Student APIs
│   ├── problems.py         # Problem management
│   ├── tests.py            # Test management
│   └── activity.py         # Anti-cheat activity logs
├── models/                 # MongoDB document schemas
├── middleware/             # JWT auth & security headers
└── static/
    ├── index.html          # Landing page
    ├── login.html
    ├── register.html
    ├── css/                # Stylesheets
    ├── js/                 # Anti-cheat, editor, dashboards
    ├── admin/              # Admin dashboard pages
    └── student/            # Student exam pages
```

---

## 🔗 Page URLs

| Page | URL |
|---|---|
| Landing | `/` |
| Login | `/login` |
| Register | `/register` |
| Admin Dashboard | `/admin/dashboard` |
| Create Test | `/admin/create-test` |
| Student Dashboard | `/student/dashboard` |
| Exam | `/student/exam?testId=<id>` |

---

## 👥 Roles

| Role | Access |
|---|---|
| **Master (Admin)** | Create problems & tests, monitor students, view all submissions |
| **Student** | Attempt tests, run & submit code, view own results |

---

## 🔬 AI Complexity Analyzer

Powered by free HuggingFace models. Analyzes your code and returns:

- ⏱ **Time Complexity** (Big-O notation)
- 🗄 **Space Complexity** (Big-O notation)
- 🧩 **Algorithm / Technique** used
- 📖 **Explanation** of the complexity
- ✨ **Optimization suggestion** (if applicable)

**Supported Models:**

| Model | Best For |
|---|---|
| `Qwen/Qwen2.5-Coder-7B-Instruct` | Code reasoning ⭐ Recommended |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | Step-by-step reasoning |
| `meta-llama/Llama-3.1-8B-Instruct` | General purpose |
| `microsoft/Phi-3.5-mini-instruct` | Fast & lightweight |

---

## 🛡️ Anti-Cheat System

| Feature | Details |
|---|---|
| Tab switch detection | 3 violations → auto-submit |
| Fullscreen enforcement | Exam exits if fullscreen is exited |
| Right-click disabled | Prevents copy/paste via context menu |
| DevTools detection | Alerts and logs if DevTools are opened |
| Activity logging | All events logged and visible to admin in real time |

---

## 📡 API Overview

```
POST /api/auth/login          → Login
POST /api/auth/register       → Register
POST /api/submissions/run     → Run code against sample test cases
POST /api/submissions/submit  → Submit code against all test cases
POST /api/complexity/analyze  → AI complexity analysis
GET  /api/admin/students      → List all students (admin only)
GET  /api/problems            → List problems
```

---

## 🏗️ Built With

- **Flask** — Python web framework
- **MongoDB** — Database (via MongoDB Atlas)
- **JWT** — Authentication
- **Gunicorn** — Production WSGI server
- **Docker** — Containerization
- **Railway** — Cloud hosting
- **HuggingFace** — AI complexity analysis
- **CodeMirror** — In-browser code editor

---

## 📄 License

MIT License — feel free to use and modify.
