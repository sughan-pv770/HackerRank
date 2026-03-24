# Codex Test 🚀

> Futuristic, secure student coding test platform with advanced anti-cheat mechanisms.

## Quick Start

### 1. Prerequisites
- Python 3.9+
- MongoDB running locally on `mongodb://localhost:27017`
- (Optional for Java/C/C++) JDK, GCC installed and in PATH

### 2. Install Dependencies
```bash
cd d:\test\terv-test
pip install -r requirements.txt
```

### 3. Run the Server
```bash
python app.py
```

The app runs at **http://localhost:5000**

---

## Access
| Page | URL |
|------|-----|
| Landing | http://localhost:5000/ |
| Login | http://localhost:5000/login |
| Register | http://localhost:5000/register |
| Admin Dashboard | http://localhost:5000/admin/dashboard |
| Student Dashboard | http://localhost:5000/student/dashboard |

## Roles
| Role | Access |
|------|--------|
| **Master** | Create problems/tests, view submissions, monitor students |
| **Student** | Attempt tests, write & run code, view own results |

## Exam Link Format
After creating a test in the admin dashboard, click **Copy Link** to get the student exam URL:
```
/student/exam?testId=<id>&problems=<id1,id2>&duration=60
```

## Supported Languages
- Python 🐍
- JavaScript (Node.js) ⚡
- Java ☕
- C 🔧
- C++ ⚙️

## Anti-Cheat System
- ✅ Tab switch detection (3 violations → auto-submit)
- ✅ Fullscreen enforcement
- ✅ Right-click & copy/paste disabled
- ✅ DevTools detection
- ✅ All events logged to admin dashboard

## Project Structure
```
terv-test/
├── app.py              # Flask entry point
├── config.py           # Configuration
├── requirements.txt
├── models/             # MongoDB schemas
├── routes/             # API blueprints
├── middleware/         # JWT & security
├── executor/           # Code sandbox
└── static/
    ├── index.html      # Landing page
    ├── login.html
    ├── register.html
    ├── css/            # Design system
    ├── js/             # Anti-cheat, editor, dashboards
    ├── admin/          # Admin pages
    └── student/        # Student pages + exam
```

---

## 🔬 Complexity Analyzer (New Feature)

The exam editor now includes a built-in **AI-powered Complexity Analyzer** — similar to LeetCode's AI analysis tool — powered by free HuggingFace models.

### How it works
1. Student writes code in the exam editor
2. Opens the **Complexity Analyzer** panel (bottom of the editor)
3. Enters their free HuggingFace API token (one-time, persists in session)
4. Clicks **⚡ Analyze** to get instant analysis

### What it returns
- ⏱ **Time Complexity** (Big-O)
- 🗄 **Space Complexity** (Big-O)
- 🧩 **Algorithm / Technique** (e.g. Hash Map, Dynamic Programming, Binary Search)
- 📖 **Explanation** of why
- ✨ **Optimization tip** (if applicable)

### Supported Models (free via HuggingFace Inference API)
| Model | Best for |
|---|---|
| `Qwen/Qwen2.5-Coder-7B-Instruct` | Code reasoning (recommended) |
| `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | Step-by-step reasoning |
| `meta-llama/Llama-3.1-8B-Instruct` | General purpose |
| `microsoft/Phi-3.5-mini-instruct` | Fast lightweight analysis |

### Backend API endpoint
```
POST /api/complexity/analyze
Authorization: Bearer <jwt_token>
{
  "code": "<source code>",
  "hfToken": "hf_...",
  "model": "Qwen/Qwen2.5-Coder-7B-Instruct"
}
```

### Security
- HF tokens are **never stored on the server** — they are sent per-request only
- The token is stored in `sessionStorage` on the client (cleared when browser tab closes)
- The backend proxies the request to HuggingFace and returns the parsed result
