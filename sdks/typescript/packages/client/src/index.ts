import {
  Capability,
  ExecutionResult,
  Policy,
  WorkflowState,
  ApprovalRequest,
  ApprovalDecision,
  Error,
} from "@aicp/core";
import { AicpRuntime } from "@aicp/runtime";

export interface ClientOptions {
  baseUrl: string;
  apiKey?: string;
  timeout?: number;
}

export class AicpClient {
  private readonly runtime: AicpRuntime;
  private readonly timeout: number;

  constructor(opts: ClientOptions) {
    this.runtime = new AicpRuntime({ baseUrl: opts.baseUrl, apiKey: opts.apiKey });
    this.timeout = opts.timeout ?? 30000;
  }

  async discover(): Promise<{
    version: string;
    capabilities: Capability[];
    policies: Policy[];
  }> {
    return this.runtime.execute({ capability: "discovery.discover" } as any).then(
      (r) => r.data as any
    );
  }

  async listCapabilities(): Promise<Capability[]> {
    return this.runtime.listCapabilities();
  }

  async getCapability(name: string): Promise<Capability | null> {
    return this.runtime.getCapability(name);
  }

  async execute(capability: string, args?: Record<string, unknown>): Promise<ExecutionResult> {
    return this.runtime.execute({ capability, arguments: args });
  }

  async listPolicies(): Promise<Policy[]> {
    return this.runtime
      .execute({ capability: "policy.list" } as any)
      .then((r) => (r.data as any).policies ?? []);
  }

  async getPolicy(name: string): Promise<Policy | null> {
    const policies = await this.listPolicies();
    return policies.find((p) => p.name === name) ?? null;
  }

  async listWorkflows(): Promise<WorkflowState[]> {
    return this.runtime
      .execute({ capability: "workflow.list" } as any)
      .then((r) => (r.data as any).workflows ?? []);
  }

  async getWorkflow(id: string): Promise<WorkflowState | null> {
    return this.runtime
      .execute({ capability: "workflow.get", arguments: { workflow_id: id } } as any)
      .then((r) => r.data as any);
  }

  async createWorkflow(definition: unknown): Promise<WorkflowState> {
    return this.runtime
      .execute({ capability: "workflow.create", arguments: { definition } } as any)
      .then((r) => r.data as any);
  }

  async resumeWorkflow(id: string, input?: unknown): Promise<ExecutionResult> {
    return this.runtime.execute({
      capability: "workflow.resume",
      arguments: { workflow_id: id, input },
    });
  }

  async listApprovals(): Promise<ApprovalRequest[]> {
    return this.runtime
      .execute({ capability: "approval.list" } as any)
      .then((r) => (r.data as any).approvals ?? []);
  }

  async getApproval(id: string): Promise<ApprovalRequest | null> {
    return this.runtime
      .execute({ capability: "approval.get", arguments: { approval_id: id } } as any)
      .then((r) => r.data as any);
  }

  async decideApproval(id: string, decision: ApprovalDecision): Promise<ExecutionResult> {
    return this.runtime.execute({
      capability: "approval.decide",
      arguments: { approval_id: id, decision: decision.decision, reason: decision.reason },
    });
  }

  async approve(id: string, reason?: string): Promise<ExecutionResult> {
    return this.decideApproval(id, { decision: "approve", reason });
  }

  async deny(id: string, reason: string): Promise<ExecutionResult> {
    return this.decideApproval(id, { decision: "deny", reason });
  }

  async health(): Promise<{ status: string; version: string }> {
    return this.runtime
      .execute({ capability: "system.health" } as any)
      .then((r) => r.data as any);
  }
}

export { Capability, ExecutionResult, Policy, WorkflowState, ApprovalRequest, ApprovalDecision, Error };
