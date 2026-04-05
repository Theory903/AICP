import { describe, expect, it, vi } from "vitest";

import { createOperatorProgram } from "./registry";

describe("createOperatorProgram", () => {
  it("leaves runtime and view undefined when only config file should supply them", async () => {
    const runShell = vi.fn(async () => undefined);
    const runSnapshot = vi.fn(async () => undefined);
    const resolveConfig = vi.fn(() => ({
      runtimeUrl: "http://config-driven-runtime",
      view: "workflows" as const
    }));
    const program = createOperatorProgram({ runShell, runSnapshot }, resolveConfig);

    await program.parseAsync([
      "node",
      "aicp-operator",
      "shell",
      "--config",
      "/tmp/aicp-operator.json"
    ]);

    expect(resolveConfig).toHaveBeenCalledWith({
      configPath: "/tmp/aicp-operator.json",
      runtimeUrl: undefined,
      view: undefined
    });
    expect(runShell).toHaveBeenCalledWith({
      runtimeUrl: "http://config-driven-runtime",
      view: "workflows"
    });
  });

  it("resolves shell config from flags before invoking handlers", async () => {
    const runShell = vi.fn(async () => undefined);
    const runSnapshot = vi.fn(async () => undefined);
    const resolveConfig = vi.fn(() => ({
      runtimeUrl: "http://localhost:9100",
      view: "providers" as const
    }));
    const program = createOperatorProgram({ runShell, runSnapshot }, resolveConfig);

    await program.parseAsync([
      "node",
      "aicp-operator",
      "shell",
      "--config",
      "/tmp/aicp-operator.json",
      "--runtime-url",
      "http://localhost:9100/",
      "--view",
      "providers"
    ]);

    expect(resolveConfig).toHaveBeenCalledWith({
      configPath: "/tmp/aicp-operator.json",
      runtimeUrl: "http://localhost:9100/",
      view: "providers"
    });
    expect(runShell).toHaveBeenCalledWith({
      runtimeUrl: "http://localhost:9100",
      view: "providers"
    });
    expect(runSnapshot).not.toHaveBeenCalled();
  });
});
