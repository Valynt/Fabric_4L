import subprocess
import sys

try:
    # Find pytest processes
    result = subprocess.run(['powershell', '-Command', 'Get-Process -Name "pytest" -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'], capture_output=True, text=True, timeout=10)
    pids = [p.strip() for p in result.stdout.strip().split('\n') if p.strip()]
    for pid in pids:
        print(f"Killing pytest process {pid}")
        subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
    print("Done")
except Exception as e:
    print(f"Error: {e}")
