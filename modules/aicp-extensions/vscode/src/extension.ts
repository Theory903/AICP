import * as vscode from "vscode";
import { spawn, ChildProcess } from "child_process";
import * as path from "path";

let aicpProcess: ChildProcess | null = null;
let aicpOutputChannel: vscode.OutputChannel | null = null;

export function activate(context: vscode.ExtensionContext) {
  aicpOutputChannel = vscode.window.createOutputChannel("AICP");

  const startCommand = vscode.commands.registerCommand("aicp.start", async () => {
    if (aicpProcess) {
      vscode.window.showInformationMessage("AICP already running");
      return;
    }

    const terminal = vscode.window.createTerminal("AICP");
    terminal.sendText("aicp dev");
    terminal.show();
    aicpProcess = spawn("aicp", ["dev"], {
      cwd: vscode.workspace.workspaceFolders?.[0]?.uri.fsPath,
    });

    aicpOutputChannel?.appendLine("AICP started");
    vscode.window.showInformationMessage("AICP started");
  });

  const runCommand = vscode.commands.registerCommand("aicp.run", async () => {
    const capability = await vscode.window.showInputBox({
      prompt: "Enter capability name",
      validateInput: (value) => (value ? null : "Required"),
    });

    if (capability) {
      const terminal = vscode.window.createTerminal("AICP");
      terminal.sendText(`aicp run ${capability}`);
      terminal.show();
    }
  });

  const devCommand = vscode.commands.registerCommand("aicp.dev", async () => {
    const config = vscode.workspace.getConfiguration("aicp");
    const devUrl = config.get("devUrl", "http://localhost:8765");

    if (aicpProcess) {
      vscode.window.showInformationMessage("AICP dev server already running");
      return;
    }

    const terminal = vscode.window.createTerminal("AICP Dev");
    terminal.sendText("aicp dev");
    terminal.show();
    aicpOutputChannel?.appendLine(`AICP dev server starting at ${devUrl}`);
  });

  const apprCommand = vscode.commands.registerCommand("aicp.appr", async () => {
    const terminal = vscode.window.createTerminal("AICP Approvals");
    terminal.sendText("aicp appr ls");
    terminal.show();
  });

  context.subscriptions.push(startCommand, runCommand, devCommand, apprCommand);
}

export function deactivate() {
  if (aicpProcess) {
    aicpProcess.kill();
    aicpProcess = null;
  }
}
