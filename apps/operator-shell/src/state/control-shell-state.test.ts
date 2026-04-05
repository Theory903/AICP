import { describe, expect, it } from "vitest";

import { deriveShellSnapshot } from "./control-shell-state";

describe("deriveShellSnapshot", () => {
  it("summarizes runtime health for the operator shell", () => {
    const snapshot = deriveShellSnapshot({
      approvals: [
        { id: "apr_1", status: "pending" },
        { id: "apr_2", status: "approved" }
      ],
      workflows: [
        { id: "wf_1", status: "running" },
        { id: "wf_2", status: "completed" }
      ],
      executions: [
        { execution_id: "exe_1", status: "completed", capability_name: "orders.place" },
        { execution_id: "exe_2", status: "failed", capability_name: "orders.track" }
      ],
      providers: [
        { provider_name: "crm-http", health_status: "healthy" },
        { provider_name: "broker-http", health_status: "unhealthy" }
      ]
    });

    expect(snapshot.pendingApprovals).toBe(1);
    expect(snapshot.activeWorkflows).toBe(1);
    expect(snapshot.recentExecutions).toBe(2);
    expect(snapshot.unhealthyProviders).toBe(1);
    expect(snapshot.overallStatus).toBe("attention");
  });
});
