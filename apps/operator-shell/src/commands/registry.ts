import { Command } from "@commander-js/extra-typings";

import {
  resolveOperatorShellConfig,
  type OperatorShellResolutionInput
} from "../config/operator-shell-loader";

interface SharedOptions {
  config?: string;
  runtimeUrl?: string;
  view?: string;
}

export interface OperatorInvocation {
  runtimeUrl: string;
  view: "overview" | "approvals" | "workflows" | "providers";
}

export interface OperatorProgramHandlers {
  runShell(config: OperatorInvocation): Promise<void>;
  runSnapshot(config: OperatorInvocation): Promise<void>;
}

export function createOperatorProgram(
  handlers: OperatorProgramHandlers,
  resolveConfig: (input: OperatorShellResolutionInput) => OperatorInvocation =
    resolveOperatorShellConfig
): Command {
  const program = new Command()
    .name("aicp-operator")
    .description("Operator-facing terminal shell for AICP runtime supervision")
    .showHelpAfterError();

  addSharedOptions(
    program
      .command("shell")
      .description("Launch the interactive operator shell")
      .action(async (_args, command) => {
        const options = command.optsWithGlobals() as SharedOptions;
        await handlers.runShell(
          resolveConfig({
            configPath: options.config,
            runtimeUrl: options.runtimeUrl,
            view: options.view
          })
        );
      })
  );

  addSharedOptions(
    program
      .command("snapshot")
      .description("Print the latest operator snapshot as JSON")
      .action(async (_args, command) => {
        const options = command.optsWithGlobals() as SharedOptions;
        await handlers.runSnapshot(
          resolveConfig({
            configPath: options.config,
            runtimeUrl: options.runtimeUrl,
            view: options.view
          })
        );
      })
  );

  return program;
}

function addSharedOptions(command: Command): Command {
  return command
    .option("--config <path>", "Operator shell config file")
    .option("--runtime-url <url>", "AICP runtime base URL")
    .option("--view <name>", "Initial shell view");
}
