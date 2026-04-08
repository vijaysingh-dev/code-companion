# AI Debugging Copilot

A VS Code extension that brings code-aware AI assistance directly into your editor.

## Setup

### 1. Start Chroma

```bash
pip install chromadb
chroma run --path ./chroma-data
```

### 2. Install dependencies

```bash
npm install
```

### 3. Add your OpenAI API key

In `.vscode/settings.json`:

```json
{
  "codeCompanion.openaiApiKey": "sk-your-key-here"
}
```

### 4. Compile and run

Press `F5` in VS Code to launch the Extension Development Host.

---

## Commands

| Command                                   | What it does                              |
| ----------------------------------------- | ----------------------------------------- |
| `Code Companion: Ask About Selected Code` | Select code → ask a question → get answer |
| `Code Companion: Index Current File`      | Embed the open file into Chroma           |
| `Code Companion: Index Entire Workspace`  | Embed all code files in the workspace     |

Open Command Palette (`Ctrl+Shift+P`) and search for "Code Companion".

---

## Flow

```
Select code → Ctrl+Shift+P → Ask About Selected Code
                    ↓
            Embed question + code
                    ↓
         Retrieve top-5 related chunks
                    ↓
              GPT-4o call
                    ↓
         Response shown in side panel
```

---

## Project Structure

```
src/
├── extension.ts          # Entry point
├── commands.ts           # Command registrations
├── config.ts             # VS Code settings reader
├── context/
│   └── contextBuilder.ts # Indexing + retrieval logic
├── services/
│   ├── chromaService.ts  # Chroma vector DB client
│   ├── embeddingService.ts # OpenAI embeddings
│   └── llmService.ts     # GPT-4o prompt + call
├── ui/
│   └── responsePanel.ts  # Webview response panel
└── utils/
    ├── chunker.ts        # Code chunking logic
    └── editorUtils.ts    # VS Code editor helpers
```
