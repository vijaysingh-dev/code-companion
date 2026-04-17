import { ModelConfig } from "../config/types";
import { BuiltContext } from "../context/contextBuilder";

// ─── Unified interface — each provider adapter must implement this ────────────

interface InferenceAdapter {
  query(systemPrompt: string, userPrompt: string): Promise<string>;
}

// ─── OpenAI inference adapter ─────────────────────────────────────────────────

class OpenAIInferenceAdapter implements InferenceAdapter {
  private client: import("openai").default;

  constructor(private config: ModelConfig) {
    const OpenAI = require("openai").default;
    this.client = new OpenAI({ apiKey: config.apiKey });
  }

  async query(systemPrompt: string, userPrompt: string): Promise<string> {
    const res = await this.client.chat.completions.create({
      model: this.config.model,
      temperature: 0.2,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
    });
    return res.choices[0].message.content ?? "No response.";
  }
}

// ─── Google Gemini inference adapter ─────────────────────────────────────────

class GeminiInferenceAdapter implements InferenceAdapter {
  private genai: import("@google/generative-ai").GoogleGenerativeAI;

  constructor(private config: ModelConfig) {
    const { GoogleGenerativeAI } = require("@google/generative-ai");
    this.genai = new GoogleGenerativeAI(config.apiKey);
  }

  async query(systemPrompt: string, userPrompt: string): Promise<string> {
    const model = this.genai.getGenerativeModel({
      model: this.config.model,
      systemInstruction: systemPrompt,
    });
    const result = await model.generateContent(userPrompt);
    return result.response.text();
  }
}

// ─── Anthropic Claude inference adapter ──────────────────────────────────────

class AnthropicInferenceAdapter implements InferenceAdapter {
  private client: import("@anthropic-ai/sdk").default;

  constructor(private config: ModelConfig) {
    const Anthropic = require("@anthropic-ai/sdk").default;
    this.client = new Anthropic({ apiKey: config.apiKey });
  }

  async query(systemPrompt: string, userPrompt: string): Promise<string> {
    const res = await this.client.messages.create({
      model: this.config.model,
      max_tokens: 2048,
      system: systemPrompt,
      messages: [{ role: "user", content: userPrompt }],
    });

    const block = res.content[0];
    return block.type === "text" ? block.text : "No response.";
  }
}

// ─── Public service — delegates to correct adapter, builds final prompt ───────

export class InferenceService {
  private adapter: InferenceAdapter;

  constructor(config: ModelConfig) {
    switch (config.provider) {
      case "openai":
        this.adapter = new OpenAIInferenceAdapter(config);
        break;
      case "gemini":
        this.adapter = new GeminiInferenceAdapter(config);
        break;
      case "anthropic":
        this.adapter = new AnthropicInferenceAdapter(config);
        break;
      default:
        throw new Error(
          `Unknown inference provider: ${(config as ModelConfig).provider}`,
        );
    }
  }

  async query(question: string, ctx: BuiltContext): Promise<string> {
    const systemPrompt =
      "You are a senior software engineer and debugging expert. " +
      "Give precise, actionable answers. Use markdown formatting. " +
      "If you spot bugs or issues, be explicit about them.";

    const userPrompt = buildPrompt(question, ctx);
    return this.adapter.query(systemPrompt, userPrompt);
  }
}

// ─── Assemble selected code + retrieved context into the final prompt ─────────

function buildPrompt(question: string, ctx: BuiltContext): string {
  const parts: string[] = [];

  parts.push(`## Question\n${question}`);

  if (ctx.selectedCode.trim()) {
    parts.push(`## Selected Code\n\`\`\`\n${ctx.selectedCode}\n\`\`\``);
  }

  if (ctx.attachments.length > 0) {
    const attachmentText = ctx.attachments
      .map(
        (attachment, i) =>
          `### Attachment ${i + 1}: ${attachment.description}\nPath: ${attachment.path}\n\`\`\`\n${attachment.content}\n\`\`\``,
      )
      .join("\n\n");
    parts.push(`## Attached Content\n${attachmentText}`);
  }

  if (ctx.retrievedChunks.length > 0) {
    const chunksText = ctx.retrievedChunks
      .map((chunk, i) => `### Chunk ${i + 1}\n\`\`\`\n${chunk}\n\`\`\``)
      .join("\n\n");
    parts.push(`## Related Codebase Context\n${chunksText}`);
  }

  return parts.join("\n\n");
}
