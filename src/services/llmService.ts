import OpenAI from "openai";
import { getConfig } from "../config";
import { BuildContext } from "../context/contextBuilder";

export class LLMService {
  private client: OpenAI;

  constructor() {
    this.client = new OpenAI({ apiKey: getConfig("openaiApiKey") });
  }

  // Assemble context into a structured prompt and get a GPT-4o response
  async query(question: string, builtContext: BuildContext): Promise<string> {
    const prompt = buildPrompt(question, builtContext);

    const response = await this.client.chat.completions.create({
      model: "gpt-4o",
      messages: [
        {
          role: "system",
          content:
            "You are a senior software engineer and debugging expert. " +
            "Give precise, actionable answers. Use markdown formatting. " +
            "If you spot bugs or issues, be explicit about them.",
        },
        { role: "user", content: prompt },
      ],
      temperature: 0.2,
    });

    return response.choices[0].message.content ?? "No response received.";
  }
}

// Construct the final prompt with selected code and retrieved context sections
function buildPrompt(question: string, ctx: BuildContext): string {
  const parts: string[] = [];

  parts.push(`## Question\n${question}`);
  parts.push(`## Selected Code\n\`\`\`\n${ctx.selectedCode}\n\`\`\``);

  if (ctx.retrievedChunks.length > 0) {
    const chunksText = ctx.retrievedChunks
      .map((chunk, i) => `### Chunk ${i + 1}\n\`\`\`\n${chunk}\n\`\`\``)
      .join("\n\n");
    parts.push(`## Related Codebase Context\n${chunksText}`);
  }

  return parts.join("\n\n");
}
