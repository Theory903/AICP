import * as vscode from 'vscode';

export class MammothPanel {
  static currentPanel: MammothPanel | undefined;
  private readonly panel: vscode.WebviewPanel;

  static createOrShow(context: vscode.ExtensionContext): MammothPanel {
    if (MammothPanel.currentPanel) {
      MammothPanel.currentPanel.panel.reveal(vscode.ViewColumn.One);
      return MammothPanel.currentPanel;
    }
    const panel = vscode.window.createWebviewPanel(
      'mammothPanel',
      'Mammoth',
      vscode.ViewColumn.One,
      { enableScripts: true }
    );
    MammothPanel.currentPanel = new MammothPanel(panel);
    return MammothPanel.currentPanel;
  }

  constructor(panel: vscode.WebviewPanel) {
    this.panel = panel;
    this.panel.webview.html = this.getHtmlForWebview();
    this.panel.onDidDispose(() => {
      MammothPanel.currentPanel = undefined;
    });
  }

  addMessage(role: 'user' | 'assistant', content: string): void {
    this.panel.webview.postMessage({ type: 'message', role, content });
  }

  private getHtmlForWebview(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Mammoth</title></head>
<body>
<div id="messages"></div>
<input id="input" type="text" placeholder="Ask Mammoth..." />
<script>
  const vscode = acquireVsCodeApi();
  document.getElementById('input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      vscode.postMessage({ type: 'userMessage', content: e.target.value });
      e.target.value = '';
    }
  });
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg.type === 'message') {
      const div = document.createElement('div');
      div.textContent = msg.role + ': ' + msg.content;
      document.getElementById('messages').appendChild(div);
    }
  });
</script>
</body>
</html>`;
  }

  dispose(): void {
    this.panel.dispose();
  }
}
