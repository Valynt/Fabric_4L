import subprocess
import sys

try:
    result = subprocess.run(['wmic', 'process', 'where', 'name like \"%pytest%\"', 'get', 'processid,commandline'], capture_output=True, text=True, timeout=10)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
except Exception as e:
    print(f"Error: {e}")
