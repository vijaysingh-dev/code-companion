import * as vscode from "vscode";

import { Api, getTokenExpiryMs } from "./api.js";

// Auth domain: the VS Code equivalent of a login page. The backend token is
// issued out-of-band by the admin CLI (`python -m app.cli.main token <user>`);
// "logging in" means pasting that token, which we validate and stash in
// SecretStorage. "Redirect to login" is requireLogin() below.

// Prompt for a token, reject an expired/invalid one, and store it. Returns whether sign-in happened.
export async function login(): Promise<boolean> {
  const token = await vscode.window.showInputBox({
    title: "Sign in to Code Companion",
    prompt: "Paste the token from `python -m app.cli.main token <user>`",
    password: true,
    ignoreFocusOut: true,
  });
  if (!token) {
    return false;
  }
  const trimmed = token.trim();
  if (getTokenExpiryMs(trimmed) <= 0) {
    void vscode.window.showErrorMessage("That token is invalid or already expired.");
    return false;
  }
  await Api.setToken(trimmed);
  return true;
}

export async function logout(): Promise<void> {
  await Api.logout();
}

// Called when a request needs auth but the session is gone (startup-expired or a 401).
export async function requireLogin(): Promise<void> {
  const choice = await vscode.window.showWarningMessage(
    "Your Code Companion session has expired. Sign in again to continue.",
    "Sign In",
  );
  if (choice === "Sign In") {
    await login();
  }
}
