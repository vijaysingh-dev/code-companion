import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { CodeCompanionConfig, DEFAULT_CONFIG, Provider } from "./types";

const CONFIG_FILENAME = "config.json";
const VALID_PROVIDERS: Provider[] = ["openai", "anthropic", "gemini"];

// ─── Resolve config file path from VS Code setting or default location ────────

export function getConfigFilePath(): string {
  const setting = vscode.workspace
    .getConfiguration("codeCompanion")
    .get<string>("codeCompanionConfig");

  if (setting && setting.trim()) {
    return setting.trim();
  }

  // Use ~/.code-companion/ directory for config
  const homeDir = process.env.HOME ?? require("os").homedir();
  const configDir = path.join(homeDir, ".code-companion");

  // Ensure the directory exists
  if (!fs.existsSync(configDir)) {
    fs.mkdirSync(configDir, { recursive: true });
  }

  return path.join(configDir, CONFIG_FILENAME);
}

// ─── Read and parse config, throwing descriptive errors on bad input ──────────

export function loadConfig(): CodeCompanionConfig {
  const filePath = getConfigFilePath();

  if (!fs.existsSync(filePath)) {
    throw new Error(
      `Config file not found: ${filePath}\n` +
        `Run "Code Companion: Open Config" to create it.`,
    );
  }

  let raw: string;
  try {
    raw = fs.readFileSync(filePath, "utf-8");
  } catch (e) {
    throw new Error(`Could not read config file: ${filePath}`);
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    throw new Error(`Config file has invalid JSON: ${filePath}`);
  }

  return validateConfig(parsed, filePath);
}

// ─── Validate required fields and provider values ────────────────────────────

function validateConfig(raw: unknown, filePath: string): CodeCompanionConfig {
  if (typeof raw !== "object" || raw === null) {
    throw new Error(`Config must be a JSON object: ${filePath}`);
  }

  const obj = raw as Record<string, unknown>;

  for (const slot of ["embedding", "inference"] as const) {
    const section = obj[slot];
    if (typeof section !== "object" || section === null) {
      throw new Error(`Config missing "${slot}" section: ${filePath}`);
    }

    const s = section as Record<string, unknown>;

    if (!s.provider || !VALID_PROVIDERS.includes(s.provider as Provider)) {
      throw new Error(
        `Config "${slot}.provider" must be one of: ${VALID_PROVIDERS.join(", ")}`,
      );
    }
    if (typeof s.model !== "string" || !s.model.trim()) {
      throw new Error(`Config "${slot}.model" must be a non-empty string`);
    }
    if (typeof s.apiKey !== "string" || !s.apiKey.trim()) {
      throw new Error(`Config "${slot}.apiKey" is missing or empty`);
    }
  }

  return raw as CodeCompanionConfig;
}

// ─── Write default config scaffold to disk ───────────────────────────────────

export function createDefaultConfig(filePath: string): void {
  fs.writeFileSync(filePath, JSON.stringify(DEFAULT_CONFIG, null, 2), "utf-8");
}
