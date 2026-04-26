from pathlib import Path


def _parse_ports(ports_text: str) -> list[tuple[str, str]]:
    """Parse port lines into (port_name, description) tuples."""
    ports = []
    for line in ports_text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if " - " in line:
            name, desc = line.split(" - ", 1)
        elif " — " in line:
            name, desc = line.split(" — ", 1)
        else:
            name, desc = line, ""
        ports.append((name.strip(), desc.strip()))
    return ports


def generate_readme_ci(
    repo_name: str,
    tile_config,
    run_date: str,
    connectivity: str,
    synthesis: str,
    cells: str,
    status: str,
    commit_sha: str,
    badge_url: str,
    has_testbench: bool,
    submit_url: str | None,
    output_path: Path,
) -> None:
    """Generate the tile README for CI mode."""

    status_emoji = "✅" if status == "PASS" else "❌"
    cells_str    = cells if cells else "-"
    commit_str   = commit_sha[:7] if commit_sha else "-"

    # ── Ports grid (2-column HTML table) ─────────────────────────────────────
    ports = _parse_ports(tile_config.ports)
    if ports:
        rows = ""
        for i in range(0, len(ports), 2):
            left_name, left_desc = ports[i]
            if i + 1 < len(ports):
                right_name, right_desc = ports[i + 1]
                right_td = f"<td><code>{right_name}</code> — {right_desc}</td>"
            else:
                right_td = "<td></td>"
            rows += f"<tr><td><code>{left_name}</code> — {left_desc}</td>{right_td}</tr>\n"
        ports_section = f"<table>\n{rows}</table>"
    else:
        ports_section = "_No ports defined._"

    # ── Usage guide ───────────────────────────────────────────────────────────
    usage_md = "  \n".join(tile_config.usage_guide.strip().splitlines())

    # ── Tests row ─────────────────────────────────────────────────────────────
    tests_row = (
        "| Tests        | Testbench provided (not run in CI) |\n"
        if has_testbench
        else "| Tests        | No testbench provided |\n"
    )
    testbench_note = (
        "\n> ℹ️ Testbench provided as user reference only — simulation is not run in CI.\n"
        if has_testbench
        else ""
    )

    # ── Failure details ───────────────────────────────────────────────────────
    fail_section = ""
    if status == "FAIL":
        fail_details = []
        if connectivity == "FAIL":
            fail_details.append(
                "- **Connectivity check failed** — verify port names and connections "
                "match the SemiCoLab convention"
            )
            fail_details.append("  See `outputs/logs/connectivity.log` for details")
        if synthesis == "FAIL":
            fail_details.append(
                "- **Synthesis failed** — check for unsupported constructs or inferred latches"
            )
            fail_details.append("  See `outputs/logs/synth.log` for details")
        fail_section = (
            "\n> ❌ **Precheck failed.** Fix the issues below and push again.\n>\n"
            + "\n".join(f"> {l}" for l in fail_details)
            + "\n\n"
        )

    # ── Badges ────────────────────────────────────────────────────────────────
    cells_badge = (
        f"![Cells](https://img.shields.io/badge/Cells-{cells_str}-blue)"
        if cells_str != "-"
        else ""
    )

    # ── Submit section (only on PASS) ─────────────────────────────────────────
    submit_section = ""
    if status == "PASS" and submit_url:
        submit_section = (
            f"\n[📬 Submit to SemiCoLab Registry →]({submit_url})"
            f"  \n📄 [Submission data](outputs/docs/submit.yaml)\n"
        )

    content = f"""# {repo_name}

![Precheck Status]({badge_url}) {cells_badge}

---
{fail_section}
**{tile_config.tile_name}** · {tile_config.tile_author} · `{tile_config.top_module}` · v{tile_config.version}

{tile_config.description.strip()}

---

## Ports

{ports_section}

## Usage guide

{usage_md}

---

## Precheck result

| Stage        | Result |
|---|---|
| Connectivity | {connectivity} |
| Synthesis    | {synthesis} |
| Cells        | {cells_str} |
{tests_row}| **Status**   | **{status_emoji} {status}** |

Commit: `{commit_str}` · {run_date}
{testbench_note}{submit_section}
---

## Netlist

![Netlist](outputs/docs/netlist.svg)

📄 [Datasheet](outputs/docs/datasheet.pdf) · 📊 [results.json](outputs/docs/results.json)
"""
    output_path.write_text(content, encoding="utf-8")
