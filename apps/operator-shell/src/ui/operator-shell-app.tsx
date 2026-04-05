import { useMemo, useState } from "react";
import { Box, Text, useApp, useInput } from "ink";

import {
  SHELL_VIEWS,
  type ApprovalQueueItem,
  type ProviderPulseItem,
  type ShellData,
  type ShellView,
  type WorkflowRunItem
} from "../state/control-shell-state";

export interface OperatorShellAppProps {
  runtimeUrl: string;
  initialView: ShellView;
  data: ShellData;
}

export function OperatorShellApp(props: OperatorShellAppProps) {
  const { exit } = useApp();
  const [view, setView] = useState<ShellView>(props.initialView);
  const viewIndex = useMemo(() => SHELL_VIEWS.indexOf(view), [view]);

  useInput((input, key) => {
    if (input === "q") {
      exit();
      return;
    }

    if (input === "1") {
      setView("overview");
      return;
    }

    if (input === "2") {
      setView("approvals");
      return;
    }

    if (input === "3") {
      setView("workflows");
      return;
    }

    if (input === "4") {
      setView("providers");
      return;
    }

    if (key.leftArrow) {
      setView(SHELL_VIEWS[(viewIndex - 1 + SHELL_VIEWS.length) % SHELL_VIEWS.length]!);
      return;
    }

    if (key.rightArrow) {
      setView(SHELL_VIEWS[(viewIndex + 1) % SHELL_VIEWS.length]!);
    }
  });

  return (
    <Box flexDirection="column" padding={1} gap={1}>
      <Text color="cyan">AICP Operator Shell</Text>
      <Text color="gray">Runtime: {props.runtimeUrl}</Text>
      <Text color={props.data.snapshot.overallStatus === "healthy" ? "green" : "yellow"}>
        Status: {props.data.snapshot.overallStatus}
      </Text>
      <Text color="gray">
        Views: [1] overview  [2] approvals  [3] workflows  [4] providers  [q] quit
      </Text>
      <Box marginTop={1} flexDirection="column">
        {renderView(view, props.data)}
      </Box>
    </Box>
  );
}

function renderView(view: ShellView, data: ShellData) {
  switch (view) {
    case "approvals":
      return renderApprovals(data.approvals);
    case "workflows":
      return renderWorkflows(data.workflows);
    case "providers":
      return renderProviders(data.providers);
    case "overview":
    default:
      return renderOverview(data);
  }
}

function renderOverview(data: ShellData) {
  return (
    <Box flexDirection="column">
      <Text>Pending approvals: {data.snapshot.pendingApprovals}</Text>
      <Text>Active workflows: {data.snapshot.activeWorkflows}</Text>
      <Text>Recent executions: {data.snapshot.recentExecutions}</Text>
      <Text>Unhealthy providers: {data.snapshot.unhealthyProviders}</Text>
    </Box>
  );
}

function renderApprovals(approvals: ApprovalQueueItem[]) {
  if (approvals.length === 0) {
    return <Text color="green">No pending approvals.</Text>;
  }

  return (
    <Box flexDirection="column">
      {approvals.slice(0, 8).map((approval) => (
        <Text key={approval.id}>
          {approval.id}  {approval.capability_name ?? "unknown-capability"}  {approval.status}
        </Text>
      ))}
    </Box>
  );
}

function renderWorkflows(workflows: WorkflowRunItem[]) {
  if (workflows.length === 0) {
    return <Text color="yellow">No workflows are currently registered.</Text>;
  }

  return (
    <Box flexDirection="column">
      {workflows.slice(0, 8).map((workflow) => (
        <Text key={workflow.id}>
          {workflow.id}  {workflow.name ?? "unnamed-flow"}  {workflow.status}
        </Text>
      ))}
    </Box>
  );
}

function renderProviders(providers: ProviderPulseItem[]) {
  if (providers.length === 0) {
    return <Text color="yellow">No provider health data yet.</Text>;
  }

  return (
    <Box flexDirection="column">
      {providers.slice(0, 8).map((provider) => (
        <Text
          key={provider.provider_name}
          color={provider.health_status === "healthy" ? "green" : "red"}
        >
          {provider.provider_name}  {provider.health_status}
        </Text>
      ))}
    </Box>
  );
}
