import * as vscode from 'vscode';
import type { MammothClientOptions } from './MammothClient';

export class ApprovalForwarder {
  private readonly baseUrl: string;

  constructor(opts: MammothClientOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, '');
  }

  async promptApproval(
    approvalId: string,
    capabilityName: string,
    description: string,
  ): Promise<boolean> {
    const message = `Mammoth needs approval: **${capabilityName}**\n${description}`;
    const choice = await vscode.window.showInformationMessage(message, 'Approve', 'Deny');
    const approved = choice === 'Approve';
    try {
      await fetch(`${this.baseUrl}/ext/approval`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_id: approvalId, approved, decided_by: 'vscode' }),
      });
    } catch {
      // best-effort: server may be unreachable
    }
    return approved;
  }
}
