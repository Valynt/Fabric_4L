import json, sys

for id_str in sys.stdin.read().split():
    if not id_str.strip(): continue
    try:
        # Use python to call the mcp via sub-process? No, I can't call mcp from python.
        pass
    except Exception as e:
        pass
