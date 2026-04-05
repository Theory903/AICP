import * as vscode from 'vscode';
import { MammothClient } from './MammothClient';
import { MammothPanel } from './MammothPanel';
import { GhostTextProvider } from './GhostTextProvider';
import { ApprovalForwarder } from './ApprovalForwarder';

let mammothClient: MammothClient | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const config = vscode.workspace.getConfiguration('mammoth');
  const baseUrl: string = config.get('serverUrl') ?? 'http://localhost:3080';

  mammothClient = new MammothClient({ baseUrl });

  const ghostProvider = new GhostTextProvider();
  context.subscriptions.push(
    vscode.languages.registerInlineCompletionItemProvider({ pattern: '**' }, ghostProvider)
  );

  const approvalForwarder = new ApprovalForwarder({ baseUrl });

  mammothClient.onMessage((content) => {
    MammothPanel.currentPanel?.addMessage('assistant', content);
  });

  mammothClient.onApprovalRequest((id, cap, desc) => {
    approvalForwarder.promptApproval(id, cap, desc);
  });

  mammothClient.connect();

  context.subscriptions.push(
    vscode.commands.registerCommand('mammoth.openPanel', () => {
      MammothPanel.createOrShow(context);
    })
  );
}

export function deactivate(): void {
  mammothClient?.disconnect();
}
