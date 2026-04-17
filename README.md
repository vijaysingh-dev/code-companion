# Code Companion

A VS Code extension that provides code-aware AI assistance for debugging, understanding, and improving code directly in your editor.

## Features

- **Ask About Code**: Select code snippets and ask questions to get AI-powered explanations and insights.
- **Code Indexing**: Embed and index your codebase for context-aware responses.
- **Configurable**: Use a JSON config file to set up embedding and inference services.

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Start ChromaDB (Vector Database)

Code Companion uses ChromaDB for storing and retrieving code embeddings. Run ChromaDB locally using Docker:

```bash
pip install chromadb
docker run -d --name chromadb -p 8000:8000 -v chroma_data:/chroma/chroma -e IS_PERSISTENT=TRUE -e PERSIST_DIRECTORY=/chroma/chroma chromadb/chroma
```

This starts ChromaDB on port 8000 with persistent storage.

### 3. Configure the Extension

Create a configuration file named `code-companion.config.json` in your workspace root (or specify a custom path in VS Code settings).

Example configuration:

```json
{
  "embedding": {
    "provider": "openai",
    "apiKey": "sk-your-openai-api-key",
    "model": "text-embedding-3-small"
  },
  "inference": {
    "provider": "openai",
    "apiKey": "sk-your-openai-api-key",
    "model": "gpt-4o"
  },
  "chroma": {
    "host": "localhost",
    "port": 8000
  }
}
```

- **embedding**: Configure the embedding service (OpenAI, Anthropic, etc.).
- **inference**: Configure the AI model for answering questions.
- **chroma**: Connection details for ChromaDB.

To open or create the config file:

- Use the command `Code Companion: Open Config` from the Command Palette.

Alternatively, set the config file path in VS Code settings:

- Go to Settings → Extensions → Code Companion → Config File Path.
- Enter the absolute path to your `code-companion.config.json`.

### 4. Compile and Run

```bash
npm run compile
```

Press `F5` in VS Code to launch the Extension Development Host and test the extension.

## Commands

| Command                                   | Description                                   |
| ----------------------------------------- | --------------------------------------------- |
| `Code Companion: Ask About Selected Code` | Select code and ask questions for AI insights |
| `Code Companion: Index Current File`      | Embed the currently open file into ChromaDB   |
| `Code Companion: Index Entire Workspace`  | Embed all code files in the workspace         |
| `Code Companion: Open Config`             | Open or create the configuration file         |

Access these via Command Palette (`Ctrl+Shift+P`) by searching for "Code Companion".

## Workflow

1. **Index Your Code**: Run `Index Entire Workspace` or `Index Current File` to embed your codebase.
2. **Ask Questions**: Select code in the editor, right-click → "Code Companion: Ask About Selected Code", or use the command.
3. **Attach More Context**: Optionally attach additional files or code snippets.
4. **Get Response**: The AI analyzes the selected code plus relevant context from your indexed codebase and provides a response in a side panel.

## Project Structure

```
src/
├── extension.ts          # Extension entry point
├── commands.ts           # Command registrations and logic
├── config/
│   ├── configLoader.ts   # Configuration file handling
│   └── types.ts          # Type definitions
├── context/
│   └── contextBuilder.ts # Code indexing and retrieval
├── services/
│   ├── chromaService.ts  # ChromaDB client
│   ├── embeddingService.ts # Embedding generation
│   └── inferenceService.ts # AI inference calls
├── ui/
│   └── responsePanel.ts  # Response display panel
└── utils/
    ├── chunker.ts        # Code chunking utilities
    └── editorUtils.ts    # Editor interaction helpers
```

## Dependencies

- **ChromaDB**: Vector database for code embeddings.
- **OpenAI/Anthropic SDKs**: For embeddings and inference.
- **VS Code API**: For extension functionality.

## Contributing

1. Clone the repository.
2. Install dependencies: `npm install`.
3. Make changes.
4. Compile: `npm run compile`.
5. Test with `F5`.

## License

See LICENSE file.
