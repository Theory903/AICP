import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, resolve } from "node:path";

import {
  isValidOperatorRuntimeUrl,
  isValidOperatorShellView,
  parseOperatorRuntimeUrl,
  parseOperatorShellConfig,
  parseOperatorShellView,
  type OperatorShellConfig
} from "./operator-shell-config";

export interface OperatorShellResolutionInput {
  configPath?: string;
  runtimeUrl?: string;
  view?: string;
}

export interface OperatorShellLoadInput {
  configPath?: string;
  overrides?: Partial<OperatorShellConfig>;
}

export function getDefaultOperatorShellConfigPath(): string {
  return resolve(homedir(), ".aicp", "operator-shell.json");
}

export function loadOperatorShellConfig(input: OperatorShellLoadInput = {}): OperatorShellConfig {
  const configPath = resolveConfigPath(input.configPath);
  const fileData = readConfigFile(configPath);
  const defaultRuntimeUrl = "http://127.0.0.1:10003";
  const defaultView = "overview" as const;
  const runtimeUrl = resolveRuntimeUrl({
    configPath,
    override: input.overrides?.runtimeUrl,
    fileValue: fileData.runtimeUrl,
    fallback: defaultRuntimeUrl
  });
  const view = resolveView({
    configPath,
    override: input.overrides?.view,
    fileValue: fileData.view,
    fallback: defaultView
  });

  return parseOperatorShellConfig({
    runtimeUrl,
    view
  });
}

export function resolveOperatorShellConfig(
  input: OperatorShellResolutionInput
): OperatorShellConfig {
  return loadOperatorShellConfig({
    configPath: input.configPath,
    overrides: {
      runtimeUrl: input.runtimeUrl,
      view: input.view as OperatorShellConfig["view"] | undefined
    }
  });
}

export function saveOperatorShellConfig(
  config: OperatorShellConfig,
  configPath?: string
): void {
  const outputPath = resolveConfigPath(configPath);
  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, `${JSON.stringify(config, null, 2)}\n`, "utf8");
}

function resolveConfigPath(configPath?: string): string {
  const candidate = String(configPath ?? "").trim();
  return candidate ? resolve(candidate) : getDefaultOperatorShellConfigPath();
}

function readConfigFile(configPath: string): Partial<OperatorShellConfig> {
  if (!existsSync(configPath)) {
    return {};
  }

  try {
    const parsed = JSON.parse(readFileSync(configPath, "utf8")) as unknown;
    if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Partial<OperatorShellConfig>;
    }

    console.warn(`Failed to load operator shell config from ${configPath}: config must be a JSON object`);
    return {};
  } catch (error) {
    console.warn(
      `Failed to load operator shell config from ${configPath}: ${error instanceof Error ? error.message : String(error)}`
    );
    return {};
  }
}

function resolveRuntimeUrl(input: {
  configPath: string;
  override: string | undefined;
  fileValue: string | undefined;
  fallback: string;
}): string {
  if (input.override !== undefined) {
    if (isValidOperatorRuntimeUrl(input.override)) {
      return parseOperatorRuntimeUrl(input.override, input.fallback);
    }

    console.warn(`Invalid operator shell runtimeUrl override for ${input.configPath}; ignoring CLI value`);
  }

  if (input.fileValue !== undefined) {
    if (isValidOperatorRuntimeUrl(input.fileValue)) {
      return parseOperatorRuntimeUrl(input.fileValue, input.fallback);
    }

    console.warn(`Invalid operator shell runtimeUrl in ${input.configPath}; using ${input.fallback}`);
  }

  return input.fallback;
}

function resolveView(input: {
  configPath: string;
  override: OperatorShellConfig["view"] | undefined;
  fileValue: OperatorShellConfig["view"] | undefined;
  fallback: OperatorShellConfig["view"];
}): OperatorShellConfig["view"] {
  if (input.override !== undefined) {
    if (isValidOperatorShellView(input.override)) {
      return parseOperatorShellView(input.override, input.fallback);
    }

    console.warn(`Invalid operator shell view override for ${input.configPath}; ignoring CLI value`);
  }

  if (input.fileValue !== undefined) {
    if (isValidOperatorShellView(input.fileValue)) {
      return parseOperatorShellView(input.fileValue, input.fallback);
    }

    console.warn(`Invalid operator shell view in ${input.configPath}; using ${input.fallback}`);
  }

  return input.fallback;
}
