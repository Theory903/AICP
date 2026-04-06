import { Capability, ExecutionResult, PolicyResult } from "@aicp/core";
import { z } from "zod";

const ExecuteInputSchema = z.object({
  capability: z.string(),
  arguments: z.record(z.unknown()).optional(),
  session_id: z.string().optional(),
  idempotency_key: z.string().optional(),
});

export type ExecuteInput = z.infer<typeof ExecuteInputSchema>;

export interface AicpRuntimeOptions {
  baseUrl: string;
  apiKey?: string;
}

export class AicpRuntime {
  private readonly baseUrl: string;
  private readonly apiKey?: string;

  constructor(opts: AicpRuntimeOptions) {
    this.baseUrl = opts.baseUrl.replace(/\/$/, "");
    this.apiKey = opts.apiKey;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    if (this.apiKey) {
      headers["Authorization"] = `Bearer ${this.apiKey}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.message || `Request failed: ${response.status}`);
    }

    return response.json();
  }

  async execute(input: ExecuteInput): Promise<ExecutionResult> {
    return this.request("/v1/execute", {
      method: "POST",
      body: JSON.stringify(input),
    });
  }

  async listCapabilities(): Promise<Capability[]> {
    const response = await this.request<{ capabilities: Capability[] }>(
      "/v1/capabilities"
    );
    return response.capabilities;
  }

  async getCapability(name: string): Promise<Capability | null> {
    const capabilities = await this.listCapabilities();
    return capabilities.find((c) => c.name === name) ?? null;
  }

  async evaluatePolicy(
    capability: string,
    arguments_: Record<string, unknown>
  ): Promise<PolicyResult> {
    return this.request("/v1/policy/evaluate", {
      method: "POST",
      body: JSON.stringify({ capability, arguments: arguments_ }),
    });
  }
}
