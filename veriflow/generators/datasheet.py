from pathlib import Path


def _format_ports(ports_text: str) -> str:
    """Format ports as an HTML list for the datasheet."""
    lines = [l.strip() for l in ports_text.strip().splitlines() if l.strip()]
    items = "\n".join(f"  <li><code>{l}</code></li>" for l in lines)
    return f"<ul>\n{items}\n</ul>"


def generate_datasheet_md(
    repo_name: str,
    tile_config,
    run_date: str,
    connectivity: str,
    synthesis: str,
    cells: str,
    status: str,
    commit_sha: str,
    output_path: Path,
) -> Path:
    """Generate an HTML datasheet for the tile. Returns the output path."""

    cells_str  = cells if cells else "-"
    status_str = "PASS" if status == "PASS" else "FAIL"
    ports_html = _format_ports(tile_config.ports) if tile_config.ports.strip() else "<p>-</p>"
    commit_str = commit_sha[:7] if commit_sha else "-"
    version_str = tile_config.version if tile_config.version else "-"

    simulator_row = ""
    if tile_config.simulator:
        sim_ver = f" {tile_config.simulator_version}" if tile_config.simulator_version else ""
        simulator_row = f"  <strong>Simulator:</strong> {tile_config.simulator}{sim_ver} &nbsp;|&nbsp;"

    content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    margin: 2.5cm;
    color: #262626;
    line-height: 1.5;
  }}
  h1 {{ font-size: 20pt; border-bottom: 2px solid #555; padding-bottom: 6px; margin-bottom: 4px; }}
  h2 {{ font-size: 13pt; margin-top: 1.8em; border-bottom: 1px solid #ccc; padding-bottom: 3px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 0.8em 0; }}
  th {{ background: #ebebeb; padding: 6px 10px; text-align: left; font-size: 10pt; }}
  td {{ padding: 5px 10px; border-bottom: 1px solid #e0e0e0; font-size: 10pt; }}
  code {{ background: #f5f5f5; padding: 1px 5px; font-family: monospace; font-size: 10pt; border-radius: 3px; }}
  ul {{ margin: 0.5em 0; padding-left: 1.5em; }}
  li {{ margin-bottom: 3px; }}
  hr {{ border: none; border-top: 1px solid #ccc; margin: 1.5em 0; }}
  .meta {{ color: #666; font-size: 10pt; margin-top: 2px; }}
</style>
</head>
<body>

<h1>{tile_config.tile_name}</h1>
<p class="meta">
  <strong>Repository:</strong> {repo_name} &nbsp;|&nbsp;
  <strong>Author:</strong> {tile_config.tile_author} &nbsp;|&nbsp;
  <strong>Top Module:</strong> <code>{tile_config.top_module}</code> &nbsp;|&nbsp;
  <strong>Version:</strong> {version_str} &nbsp;|&nbsp;
  {simulator_row}
  <strong>Date:</strong> {run_date}
</p>

<hr>

<h2>Description</h2>
<p>{tile_config.description.strip()}</p>

<h2>Port Convention (SemiCoLab)</h2>
<table>
  <tr><th>Port</th><th>Direction</th><th>Width</th><th>Description</th></tr>
  <tr><td><code>clk</code></td><td>input</td><td>1</td><td>Clock</td></tr>
  <tr><td><code>arst_n</code></td><td>input</td><td>1</td><td>Async reset, active low</td></tr>
  <tr><td><code>csr_in</code></td><td>input</td><td>16</td><td>Control/Status Register input</td></tr>
  <tr><td><code>data_reg_a</code></td><td>input</td><td>32</td><td>Operand A</td></tr>
  <tr><td><code>data_reg_b</code></td><td>input</td><td>32</td><td>Operand B</td></tr>
  <tr><td><code>data_reg_c</code></td><td>output</td><td>32</td><td>Result</td></tr>
  <tr><td><code>csr_out</code></td><td>output</td><td>16</td><td>Control/Status Register output</td></tr>
  <tr><td><code>csr_in_re</code></td><td>output</td><td>1</td><td>CSR input read enable</td></tr>
  <tr><td><code>csr_out_we</code></td><td>output</td><td>1</td><td>CSR output write enable</td></tr>
</table>

<h2>Tile Port Usage</h2>
{ports_html}

<h2>Usage Guide</h2>
<p>{tile_config.usage_guide.strip()}</p>

<hr>

<h2>Precheck Result</h2>
<table>
  <tr><th>Stage</th><th>Result</th></tr>
  <tr><td>Connectivity Check</td><td>{connectivity}</td></tr>
  <tr><td>Synthesis</td><td>{synthesis}</td></tr>
  <tr><td>Cell Count</td><td>{cells_str}</td></tr>
  <tr><td><strong>Status</strong></td><td><strong>{status_str}</strong></td></tr>
</table>
<p class="meta">Commit: <code>{commit_str}</code></p>

</body>
</html>"""

    output_path.write_text(content, encoding="utf-8")
    return output_path


def convert_html_to_pdf(html_path: Path, pdf_path: Path) -> bool:
    """Convert HTML to PDF using WeasyPrint. Returns True if successful."""
    try:
        from weasyprint import HTML
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
        return pdf_path.exists()
    except ImportError as e:
        print(f"[precheck] WeasyPrint not available: {e}")
        return False
    except Exception as e:
        print(f"[precheck] PDF generation failed: {e}")
        return False
