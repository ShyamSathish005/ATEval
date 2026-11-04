# ATEval Desktop Model Setup & Local Inference

## 1. Overview & Privacy Principles

ATEval Desktop provides AI-assisted academic writing revision powered by local Large Language Models (LLMs).

Unlike commercial writing assistants that send research drafts to proprietary cloud APIs, ATEval adheres to a **100% local inference philosophy**:
- **Zero Cloud Transmission**: Your manuscript text never leaves your computer.
- **No Unsolicited Multi-GB Downloads**: ATEval never downloads multi-gigabyte neural weights automatically without your explicit consent.
- **Open Standards**: Relies on [Ollama](https://ollama.com) via standard loopback HTTP (`http://127.0.0.1:11434`).

---

## 2. Recommended Models

ATEval is calibrated to work with parameter-efficient, instruction-tuned academic revision models:

| Model | Parameters | Quantization | RAM Required | Best For | Command |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ateval-xtragpt-1_5b-q8_0`** | 1.5B | Q8_0 | ~2.5 GB | Primary academic revision, claim preservation, hedging | `ollama run ateval-xtragpt-1_5b-q8_0` |
| **`llama3.2:3b`** | 3.2B | Q4_K_M | ~3.5 GB | General academic restructuring and clarity | `ollama run llama3.2:3b` |
| **`qwen2.5:3b`** | 3.0B | Q4_K_M | ~3.2 GB | Technical and mathematical exposition | `ollama run qwen2.5:3b` |

---

## 3. Step-by-Step Setup

### Step 1: Install Ollama
If you haven't already installed Ollama:
- Download the macOS installer from: [https://ollama.com/download](https://ollama.com/download)
- Drag Ollama to your Applications folder and launch it once to initialize the background service.

### Step 2: Start the Recommended Model
Open your Terminal and run:
```bash
ollama run ateval-xtragpt-1_5b-q8_0
```
*(If `ateval-xtragpt-1_5b-q8_0` is not yet published in your local Ollama library, use `ollama run llama3.2:3b` as a drop-in standard alternative).*

### Step 3: Verify in ATEval Desktop
1. Open ATEval Desktop.
2. The **Model Setup badge** in the top header will transition to:
   `Model: Active (Ollama)` with a green indicator.
3. Open the **Manuscript Workspace**, import your manuscript (`.tex`, `.docx`, `.md`), and click **"Generate Revision Proposals"**.
4. The local model will evaluate each flagged sentence span and produce structured revisions with SCAR claim preservation.

---

## 4. Troubleshooting & FAQ

### "Ollama Not Detected" / "Connection Refused"
- Ensure Ollama is running in your menu bar or run `ollama serve` in a terminal window.
- Verify connectivity: `curl http://127.0.0.1:11434/api/tags`. It should return a JSON list of installed models.

### Can I run ATEval without Ollama?
- **Yes.** All core descriptive statistics, readability metrics (Flesch, Gunning-Fog, MTLD, TTR), sentence segmentation, LaTeX and Word document parsing, and manual revision exports work completely offline without Ollama. Ollama is only required for automated neural candidate generation.
