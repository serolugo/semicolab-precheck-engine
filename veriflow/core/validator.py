import shutil
from pathlib import Path

from veriflow.core import VeriFlowError


def validate_tools() -> None:
    """Validate that iverilog and yosys are available in PATH."""
    for tool in ("iverilog", "yosys"):
        if shutil.which(tool) is None:
            raise VeriFlowError(
                f"Tool not found in PATH: {tool}\n"
                f"  Install OSS CAD Suite and ensure it is on your PATH."
            )
