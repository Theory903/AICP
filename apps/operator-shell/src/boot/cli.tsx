import { render } from "ink";

import { createOperatorProgram, type OperatorInvocation } from "../commands/registry";
import { RuntimeControlClient } from "../connect/runtime-client";
import { OperatorShellApp } from "../ui/operator-shell-app";

async function runShell(config: OperatorInvocation): Promise<void> {
  const client = new RuntimeControlClient(config.runtimeUrl);
  const data = await client.readDashboardData();

  render(
    <OperatorShellApp runtimeUrl={config.runtimeUrl} initialView={config.view} data={data} />,
    { exitOnCtrlC: true }
  );
}

async function runSnapshot(config: OperatorInvocation): Promise<void> {
  const client = new RuntimeControlClient(config.runtimeUrl);
  const data = await client.readDashboardData();
  process.stdout.write(`${JSON.stringify(data, null, 2)}\n`);
}

const program = createOperatorProgram({ runShell, runSnapshot });

await program.parseAsync(process.argv);
