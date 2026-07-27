import subprocess
result = subprocess.run(
    ["pnpm", "--dir", "packages/config", "exec", "tsc", "--noEmit"],
    cwd="/app",
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    check=False,
)
print(result.returncode)
print(result.stdout)
