import {
  composeShellData,
  type ApprovalQueueItem,
  type ExecutionFeedItem,
  type ProviderPulseItem,
  type ShellData,
  type WorkflowRunItem
} from "../state/control-shell-state";

export type FetchLike = typeof fetch;

export class RuntimeControlClient {
  readonly baseUrl: string;

  constructor(baseUrl: string, private readonly fetchImpl: FetchLike = fetch) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
  }

  async readDashboardData(): Promise<ShellData> {
    const [approvals, workflows, executions, providers] = await Promise.all([
      this.requestJson<ApprovalQueueItem[]>("/v1/approvals?status_filter=pending"),
      this.requestJson<WorkflowRunItem[]>("/workflows"),
      this.requestJson<ExecutionFeedItem[]>("/v1/executions?limit=12"),
      this.requestJson<ProviderPulseItem[]>("/providers/health?limit=12")
    ]);

    return composeShellData({
      approvals,
      workflows,
      executions,
      providers
    });
  }

  private async requestJson<T>(path: string): Promise<T> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`);
    if (!response.ok) {
      throw new Error(`Runtime request failed for ${path}: ${response.status} ${response.statusText}`);
    }

    return (await response.json()) as T;
  }
}

export function normalizeBaseUrl(baseUrl: string): string {
  const normalized = String(baseUrl).trim();
  if (!normalized) {
    throw new Error("runtimeUrl cannot be empty");
  }

  return normalized.replace(/\/+$/, "");
}
