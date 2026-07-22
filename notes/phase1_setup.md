# Phase 1: Environment & Tooling Setup

**Date:** July 22, 2026  
**Hardware:** Mac Mini (2024) — Apple M4 Chip, 16GB Unified Memory  
**Objective:** Set up an isolated Python development environment and run a local LLM using Ollama with Metal hardware acceleration.

---

## 1. Python Virtual Environment Setup

A virtual environment (`venv`) keeps our project dependencies isolated from the global Mac system settings.

```bash
# Check Python version (requires Python 3.10+)
python3 --version

# Create virtual environment named 'venv'
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate
# (Confirmation: Prompt should now display '(venv)' at the start)

# Prevent Git from tracking package files
echo "venv/" >> .gitignore
```

## 2. Local LLM Setup (Ollama)

Instead of relying on paid cloud APIs (e.g., OpenAI or Anthropic), we run open-source models locally using **Ollama**. On Apple Silicon (M4), Ollama automatically leverages Metal acceleration and Unified Memory to run models at high speeds with zero API cost and 100% data privacy.

### Installation & Execution
1. Installed **Ollama for macOS** from [ollama.com](https://ollama.com).
2. Opened the application and verified it runs in the background.
3. Downloaded and launched Meta's `Llama 3.2` model directly from the VS Code integrated terminal:

```bash
# Download and launch interactive chat with Llama 3.2 ollama run llama3.2
```

### Verification & Testing

- Model: ```Llama 3.2``` (~2.0 GB lightweight parameter model)
- Test Query: _"Give me a 1-sentence definition of credit risk in finance."_
- Exit Command: Type ```/bye``` to close the session.

## 3. Key Concepts Learned

* **Virtual Environment Isolation (`venv`):** Prevents project-specific dependencies from clashing with system-wide Python packages or other projects.
* **Local Inference vs. Cloud APIs:** Running models locally using Ollama keeps financial data completely private, eliminates token costs, and operates offline using Apple M4 Unified Memory.
* **Git Hygiene:** Using a `.gitignore` file ensures heavy binary files (like local virtual environments in `venv/` or cached database files) are never committed to GitHub, keeping the repository lightweight and clean.