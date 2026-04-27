import subprocess
from pathlib import Path

from veriflow.core.log_parser import parse_synth_log


def run_synthesis(
    rtl_files: list[Path],
    top_module: str,
    synth_log_path: Path,
) -> tuple[str, dict]:
    """
    Run Yosys synthesis.
    Returns (result, parsed_dict).
    result is 'PASS' or 'FAIL'.

    Gate rules (ISSUE-001):
    - FAIL if exit code != 0
    - FAIL if ERROR: found in log (real Yosys errors)
    - FAIL if latch inferred
    - Warning: messages are informative only — do not block
    """
    synth_log_path.parent.mkdir(parents=True, exist_ok=True)

    read_cmds = "\n".join(f"read_verilog {f.as_posix()}" for f in rtl_files)
    script = f"""
{read_cmds}
hierarchy -check -top {top_module}
synth
check
stat
"""
    result = subprocess.run(
        ["yosys", "-p", script],
        capture_output=True,
        text=True,
    )
    log_content = result.stdout + result.stderr
    synth_log_path.write_text(log_content, encoding="utf-8")

    parsed = parse_synth_log(log_content)

    has_errors = int(parsed.get("errors", "0")) > 0
    has_latches = parsed["has_latches"]

    if result.returncode != 0 or has_errors or has_latches:
        status = "FAIL"
    else:
        status = "PASS"

    return status, parsed
