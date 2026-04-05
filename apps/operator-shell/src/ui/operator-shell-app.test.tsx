import { describe, expect, it } from "vitest";
import { render } from "ink-testing-library";

import { OperatorShellApp } from "./operator-shell-app";

describe("OperatorShellApp", () => {
  it("renders the overview with operator-centric status text", () => {
    const { lastFrame } = render(
      <OperatorShellApp
        runtimeUrl="http://127.0.0.1:10003"
        initialView="overview"
        data={{
          approvals: [{ id: "apr_1", status: "pending", capability_name: "orders.place" }],
          workflows: [{ id: "wf_1", status: "running", name: "trade_flow" }],
          executions: [{ execution_id: "exe_1", status: "completed", capability_name: "orders.place" }],
          providers: [{ provider_name: "broker-http", health_status: "healthy" }],
          snapshot: {
            pendingApprovals: 1,
            activeWorkflows: 1,
            recentExecutions: 1,
            unhealthyProviders: 0,
            overallStatus: "healthy"
          }
        }}
      />
    );

    expect(lastFrame()).toContain("AICP Operator Shell");
    expect(lastFrame()).toContain("Pending approvals: 1");
    expect(lastFrame()).toContain("Runtime: http://127.0.0.1:10003");
  });
});
