import json
import subprocess
import tempfile
from pathlib import Path


def generate_netlist_svg(
    rtl_files: list[Path],
    top_module: str,
    output_path: Path,
) -> bool:
    """
    Generate a netlist SVG using Yosys + netlistsvg.
    Returns True if successful.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Yosys generates JSON netlist
    json_path = Path(tempfile.mktemp(suffix=".json"))
    read_cmds = "\n".join(f"read_verilog {f.as_posix()}" for f in rtl_files)
    script = f"""
{read_cmds}
hierarchy -check -top {top_module}
proc
opt
write_json {json_path.as_posix()}
"""
    try:
        result = subprocess.run(
            ["yosys", "-p", script],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not json_path.exists():
            return False

        # Step 2: netlistsvg converts JSON to SVG
        result2 = subprocess.run(
            ["netlistsvg", str(json_path), "-o", str(output_path)],
            capture_output=True,
            text=True,
        )
        if result2.returncode == 0 and output_path.exists():
            svg = output_path.read_text(encoding="utf-8")
            # Insert white background rect as first child of SVG
            import re as _re
            # Find width and height from SVG tag
            w = _re.search(r'width="([^"]+)"', svg)
            h = _re.search(r'height="([^"]+)"', svg)
            if w and h:
                bg_rect = f'<rect width="{w.group(1)}" height="{h.group(1)}" fill="white"/>'
                svg = _re.sub(r'(<svg[^>]*>)', r'\1' + bg_rect, svg, count=1)
            output_path.write_text(svg, encoding="utf-8")
            return True
        return False
    except FileNotFoundError:
        return False
    finally:
        json_path.unlink(missing_ok=True)
