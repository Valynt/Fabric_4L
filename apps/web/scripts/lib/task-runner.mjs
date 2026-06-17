import { spawnSync } from "node:child_process";

export function runTask(task, options = {}) {
  const { cwd, env = process.env } = options;
  const command = task.command;
  const args = task.args || [];

  const spawnCommand = process.platform === "win32" ? "cmd.exe" : command;
  const spawnArgs =
    process.platform === "win32"
      ? ["/d", "/s", "/c", `${command} ${args.join(" ")}`]
      : args;

  const result = spawnSync(spawnCommand, spawnArgs, {
    cwd,
    stdio: "inherit",
    shell: false,
    env,
  });

  if (result.error) {
    return {
      status: 1,
      error: result.error,
    };
  }

  return {
    status: result.status || 0,
    error: null,
  };
}