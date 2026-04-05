import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { loadOperatorShellConfig } from "./operator-shell-loader";

describe("loadOperatorShellConfig", () => {
  it("loads config from disk and applies CLI overrides", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "aicp-operator-"));
    const configPath = join(tempDir, "operator-shell.json");

    writeFileSync(
      configPath,
      JSON.stringify({
        runtimeUrl: "http://runtime.internal:9100/",
        view: "workflows"
      })
    );

    const config = loadOperatorShellConfig({
      configPath,
      overrides: { view: "providers" }
    });

    expect(config).toEqual({
      runtimeUrl: "http://runtime.internal:9100",
      view: "providers"
    });
  });

  it("falls back to defaults when on-disk values are invalid", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "aicp-operator-"));
    const configPath = join(tempDir, "operator-shell.json");

    writeFileSync(
      configPath,
      JSON.stringify({
        runtimeUrl: "",
        view: "unknown"
      })
    );

    const config = loadOperatorShellConfig({ configPath });

    expect(config).toEqual({
      runtimeUrl: "http://127.0.0.1:10003",
      view: "overview"
    });
  });

  it("preserves a valid runtime URL when only the view is invalid", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "aicp-operator-"));
    const configPath = join(tempDir, "operator-shell.json");

    writeFileSync(
      configPath,
      JSON.stringify({
        runtimeUrl: "https://ops.example.internal/",
        view: "unknown"
      })
    );

    const config = loadOperatorShellConfig({ configPath });

    expect(config).toEqual({
      runtimeUrl: "https://ops.example.internal",
      view: "overview"
    });
  });

  it("preserves valid file values when CLI overrides are invalid", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "aicp-operator-"));
    const configPath = join(tempDir, "operator-shell.json");

    writeFileSync(
      configPath,
      JSON.stringify({
        runtimeUrl: "https://ops.example.internal/",
        view: "workflows"
      })
    );

    const config = loadOperatorShellConfig({
      configPath,
      overrides: {
        runtimeUrl: "not-a-url",
        view: "invalid" as never
      }
    });

    expect(config).toEqual({
      runtimeUrl: "https://ops.example.internal",
      view: "workflows"
    });
  });

  it("treats non-object JSON config as invalid and falls back safely", () => {
    const tempDir = mkdtempSync(join(tmpdir(), "aicp-operator-"));
    const configPath = join(tempDir, "operator-shell.json");

    writeFileSync(configPath, "null");

    const config = loadOperatorShellConfig({ configPath });

    expect(config).toEqual({
      runtimeUrl: "http://127.0.0.1:10003",
      view: "overview"
    });
  });
});
