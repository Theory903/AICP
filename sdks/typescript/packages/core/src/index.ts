export * from "./capability";
export * from "./policy";
export * from "./execution-result";
export * from "./error";
export * from "./workflow";
export * from "./approval";

export interface DiscoveryResponse {
  version: string;
  capabilities?: import("./capability").Capability[];
  policies?: import("./policy").Policy[];
  workflows?: import("./workflow").WorkflowState[];
  metadata?: Record<string, unknown>;
}
