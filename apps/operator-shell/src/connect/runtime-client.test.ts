import { describe, expect, it } from "vitest";

import { RuntimeControlClient } from "./runtime-client";

describe("RuntimeControlClient", () => {
  it("fetches the dashboard inputs from the AICP runtime surface", async () => {
    const visited: string[] = [];
    const client = new RuntimeControlClient(
      "http://127.0.0.1:10003",
      async (input) => {
        const url = String(input);
        visited.push(url);
        return new Response("[]", {
          status: 200,
          headers: { "content-type": "application/json" }
        });
      }
    );

    await client.readDashboardData();

    expect(visited).toEqual([
      "http://127.0.0.1:10003/v1/approvals?status_filter=pending",
      "http://127.0.0.1:10003/workflows",
      "http://127.0.0.1:10003/v1/executions?limit=12",
      "http://127.0.0.1:10003/providers/health?limit=12"
    ]);
  });
});
