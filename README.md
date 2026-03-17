<div align="center">

# 🤖 Self-Extending Agent
### *Powered by Google Agent Development Kit (ADK)*

<br/>

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Google ADK](https://img.shields.io/badge/Google_ADK-Latest-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://google.github.io/adk-docs/)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://deepmind.google/technologies/gemini/)
[![Qwen](https://img.shields.io/badge/Qwen-2.5_3B-000000?style=for-the-badge&logo=alibabacloud&logoColor=white)](https://qwenlm.github.io/)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)

<br/>

> **An AI agent that writes, stores, and reuses its own skills — growing smarter with every task.**

<br/>

</div>

---

## ✨ What is this?

**SelfExtendingAgent** is a full-stack agentic application built on **Google's Agent Development Kit (ADK)** that demonstrates a groundbreaking concept: an AI agent that can **dynamically create and reuse its own skills** at runtime.

### 🧠 Dual-Model "Smart Routing" Architecture
This project implements an efficient, cost-effective dual-model architecture:
- 🚀 **Qwen 2.5 (3B Local)** acts as the fast, low-latency conversational interface, formatting responses for the user without incurring API costs for simple or known queries.
- 💡 **Gemini 2.5 Flash** acts as the heavy-duty Orchestrator and Researcher. It evaluates intent, searches the web, and generates new robust technical definitions when a knowledge gap is detected.

Instead of being limited to a fixed set of capabilities, this agent:
- 🧠 **Understands** what it needs to do
- 🔍 **Checks** whether it already has a skill for it
- 🛠️ **Creates** a new skill on the fly if one doesn't exist
- ♻️ **Reuses** previously created skills for future tasks using Qwen

This is **self-extending intelligence** — the agent's capability surface grows automatically as it encounters new tasks.

---

## 🎬 See It In Action

### 🔄 Skill Reuse — Already Knows What to Do

When the agent encounters a task it has handled before, it intelligently detects the existing skill and applies it directly — zero redundancy, maximum efficiency delivered via Qwen.

<br/>

![Already Skill Use Demo](https://raw.githubusercontent.com/simranjeet97/SelfExtendingAgent_ADKGoogle/master/Already-Skill-Use.png)

<br/>

### ⚡ Skill Creation — Learning on the Fly

When a new task is encountered, the agent's **Skill Creator** module kicks in — Gemini researches, designs, writes, and stores a brand-new skill, then Qwen executes it immediately.

<br/>

![Skill Creator Demo](https://raw.githubusercontent.com/simranjeet97/SelfExtendingAgent_ADKGoogle/master/Skill-Creator-Demo.png)

<br/>

---

## 🏗️ Architecture

```
SelfExtendingAgent_ADKGoogle/
│
├── 🐍 backend/                  # ADK-powered Python agent core
│   └── agent logic, skill registry, tool definitions
│
├── 🎨 frontend/                 # Conversational UI
│   └── HTML + CSS + JS chat interface
│
├── 🤖 dev_assistant_app/        # ADK Dev Assistant application
│   └── skill-aware orchestration layer
│
├── 🔁 repro_answer.py           # Reproducible answer generation
├── 📦 requirements.txt          # Python dependencies
└── 🚀 run.sh                    # One-command launcher
```

### How the Dual-Model Loop Works

```
User Request
     │
     ▼
┌─────────────────────┐
│   Intent Matcher    │  ◄── Gemini 2.5 Flash
│   (ADK LlmAgent)    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐     YES ──► Route to Presenter
│  Skill Registry     │◄── Does a skill exist for this task?
│  (Persistent Store) │
└────────┬────────────┘
         │ NO
         ▼
┌─────────────────────┐
│   Skill Creator     │  ◄── Gemini 2.5 Flash (Web Research + Tool Use)
│   (Learn Pass)      │
└────────┬────────────┘
         │ Generates SKILL.md
         ▼
┌─────────────────────┐
│ Answer Presenter    │  ◄── Qwen 2.5 3B Local (Fast, cheap UI inference)
│   (Tool-Free)       │
└────────┬────────────┘
         │
         ▼
  Save to Registry ──► Execute New Skill ──► Return Result
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A Google AI / Gemini API key
- [Ollama](https://ollama.com/) (installed and running locally)
- Node.js (for frontend)

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/simranjeet97/SelfExtendingAgent_ADKGoogle.git
cd SelfExtendingAgent_ADKGoogle

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Pull the local Qwen model for UI formatting
ollama pull qwen2.5:3b

# 4. Set your API keys (create dev_assistant_app/.env)
# export GOOGLE_API_KEY="your_gemini_api_key_here"

# 5. Launch everything
bash run.sh
```

### Running with ADK CLI

```bash
# Start the ADK dev UI for the agent
adk web dev_assistant_app

# Or run in terminal mode
adk run dev_assistant_app
```

The app will be available at `http://localhost:8000`.

---

## 🧩 Core Concepts

### Agent Skills
Skills are self-contained knowledge modules (structured as `SKILL.md` files) that tell the agent *how* to perform a specific task. The agent discovers, activates, and creates these skills dynamically — keeping context lean while expanding capability.

### Multi-Model Execution
By routing heavy logic (planning, API tools, coding, routing) to **Gemini**, and conversational formatting and generation to **local Qwen models**, the app minimizes latency and cost without sacrificing intelligence.

### Google ADK Integration
Built on **Google's Agent Development Kit**, the agent leverages:
- `LlmAgent` — the reasoning core powered by LLMs
- **Tool Use** — custom tools for skill read/write operations

### Persistent Skill Registry
Created skills are persisted to disk and indexed — so the agent's knowledge compounds over time. Every new skill makes the agent permanently smarter for future sessions.

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | Google ADK (Agent Development Kit) |
| Reasoning Core | Gemini 2.5 Flash |
| UI/Inference Core | Ollama (Qwen 2.5 3B) |
| Backend | Python 3.10+ |
| Frontend | HTML, CSS, JavaScript |
| Skill Format | Markdown (`SKILL.md`) |

---

## 💡 Why Self-Extending?

Traditional AI agents have a fixed set of tools. When they encounter something new, they either fail or hallucinate. **SelfExtendingAgent** takes a different approach:

| Traditional Agent | Self-Extending Agent |
|-------------------|----------------------|
| Fixed capabilities | Grows with every task |
| Fails on unknown tasks | Creates skills for new tasks |
| Repeats work inefficiently | Reuses previously learned skills efficiently |
| Manual tool engineering | Autonomous skill generation |

---

## 🤝 Contributing

Contributions are welcome! Feel free to:
- 🐛 Open an issue for bugs
- 💬 Start a discussion for new ideas
- 🔀 Submit a pull request with improvements

---

## 📄 License

This project is open source. See [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ using [Google Agent Development Kit](https://google.github.io/adk-docs/), [Gemini](https://deepmind.google/technologies/gemini/), & [Ollama](https://ollama.com/)

**⭐ Star this repo if you found it useful!**

</div>
