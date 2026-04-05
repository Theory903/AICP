import { z } from "zod";

import { SHELL_VIEWS, type ShellView } from "../state/control-shell-state";
import { normalizeBaseUrl } from "../connect/runtime-client";

const ShellViewSchema = z.enum(SHELL_VIEWS);
const RuntimeUrlSchema = z
  .string()
  .trim()
  .min(1)
  .refine((value) => isAbsoluteHttpUrl(value), "runtimeUrl must be an absolute http(s) URL")
  .transform((value) => normalizeBaseUrl(value));

export const OperatorShellConfigSchema = z.object({
  runtimeUrl: RuntimeUrlSchema,
  view: ShellViewSchema.default("overview")
});

export interface OperatorShellConfig {
  runtimeUrl: string;
  view: ShellView;
}

export function parseOperatorShellConfig(input: unknown): OperatorShellConfig {
  return OperatorShellConfigSchema.parse(input);
}

export function parseOperatorRuntimeUrl(value: unknown, fallback: string): string {
  const parsed = RuntimeUrlSchema.safeParse(value);
  return parsed.success ? parsed.data : fallback;
}

export function parseOperatorShellView(value: unknown, fallback: ShellView): ShellView {
  const parsed = ShellViewSchema.safeParse(value);
  return parsed.success ? parsed.data : fallback;
}

export function isValidOperatorRuntimeUrl(value: unknown): boolean {
  return RuntimeUrlSchema.safeParse(value).success;
}

export function isValidOperatorShellView(value: unknown): boolean {
  return ShellViewSchema.safeParse(value).success;
}

function isAbsoluteHttpUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}
