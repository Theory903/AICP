import * as vscode from 'vscode';

export class GhostTextProvider implements vscode.InlineCompletionItemProvider {
  private suggestion: string | undefined;

  get currentSuggestion(): string | undefined {
    return this.suggestion;
  }

  setSuggestion(text: string): void {
    this.suggestion = text;
  }

  clearSuggestion(): void {
    this.suggestion = undefined;
  }

  provideInlineCompletionItems(
    _document: vscode.TextDocument,
    _position: vscode.Position,
    _context: vscode.InlineCompletionContext,
    _token: vscode.CancellationToken,
  ): vscode.ProviderResult<vscode.InlineCompletionList> {
    if (!this.suggestion) {
      return new vscode.InlineCompletionList([]);
    }
    return new vscode.InlineCompletionList([
      new vscode.InlineCompletionItem(this.suggestion),
    ]);
  }
}
