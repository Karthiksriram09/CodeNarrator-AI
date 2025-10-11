# 🧠 CodeNarrator AI  
### *The AI that reads your code so you don’t have to.*

---

## 🚀 Overview
**CodeNarrator AI** is an open-source project that understands and documents your codebase automatically.  
Upload any Python/JS project, and it will:
- Parse your source files using `AST`
- Generate human-readable explanations with a local Transformer model
- Visualize class/function relationships via Mermaid.js

> 🧩 *Built completely from scratch — no paid APIs.*

---

## 🏗️ Tech Stack
| Layer | Technologies |
|-------|---------------|
| Backend | Flask, Python, Transformers |
| AI Engine | CodeBERT / T5 (Hugging Face) |
| Parser | Python AST, Astor |
| Database | SQLite |
| Frontend | HTML + Tailwind + Mermaid.js |
| Vector Search (later) | FAISS / ChromaDB |

---

## 📂 Project Structure
```

app/
├── routes/
├── services/
├── templates/
└── static/
database/
tests/

````

---

## 🧠 Core Features
- 📄 Code summarization  
- 🔍 Function/class extraction  
- 📊 Dependency visualization  
- 💾 Local storage of analysis  
- 🗣️ Explain-your-repo chat (v1.1)

---

## 🧩 Planned Milestones
| Version | Focus |
|----------|--------|
| v0.1 | Single-file analysis |
| v0.5 | Whole-repo upload + summaries |
| v1.0 | Interactive repo visualizer |
| v1.1 | Ask-Your-Repo Q&A |
| v2.0 | VS Code Plugin Integration |

---

## 🧰 Setup Guide
```bash
git clone https://github.com/karthiksriram09/CodeNarrator-AI.git
cd CodeNarrator-AI
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app/main.py
````

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

---

## 💡 Vision

> “I built AI that understands humans through **HireSense Pro**,
> now I’m building AI that understands **code** through **CodeNarrator AI**.”

---

## 🧑‍💻 Author

**Kudali Karthik Sriram**
🎓 B.Tech CSE (AI & Intelligent Process Automation) @ KL University
🔗 [GitHub](https://github.com/karthiksriram09) • [LinkedIn](https://www.linkedin.com/in/kudalikarthiksriram/)
