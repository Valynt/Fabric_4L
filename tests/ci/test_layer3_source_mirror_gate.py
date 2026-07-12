import subprocess
from pathlib import Path


def test_layer3_source_mirror_gate_passes() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "ci" / "check_layer3_source_mirror.py"
    result = subprocess.run(["python", str(script)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
