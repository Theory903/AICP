import os
import sys
from pathlib import Path

# Fix PYTHONPATH
root = Path("/Users/abhishekjha/CODE/AICP")
sys.path.insert(0, str(root / "packages" / "cli" / "src"))
sys.path.insert(0, str(root / "packages" / "core" / "src"))
sys.path.insert(0, str(root / "packages" / "runtime" / "src"))

from aicp_cli.context import get_runtime_context

os.chdir(root / "_test_target")
print(f"CWD: {os.getcwd()}")

try:
    ctx = get_runtime_context()
    print(f"Project: {ctx.project.config.project_name}")
    print(f"Warnings: {ctx.project.warnings}")
    print(f"Capabilities found: {len(ctx.project.capabilities)}")
    for cap in ctx.project.capabilities:
        print(f" - {cap.name}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
