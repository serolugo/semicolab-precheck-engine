"""
SemiCoLab Precheck Command
CI engine for SemiCoLab IP tile repositories.
Runs connectivity check + synthesis, generates documentation and submission package.

Based on veriflow-precheck (https://github.com/serolugo/veriflow-precheck)
"""

import json
import os
import urllib.parse
from datetime import date
from pathlib import Path

import yaml

from veriflow.core import VeriFlowError
from veriflow.core.sim_runner import run_connectivity_check
from veriflow.core.synth_runner import run_synthesis
from veriflow.core.validator import validate_tools
from veriflow.models.tile_config_ci import TileConfigCI

REGISTRY_ISSUE_FORM_URL = (
    "https://github.com/mifral/semicolab-registry/issues/new"
    "?template=submit_tile.yml"
)


def cmd_precheck(
    repo_root: Path,
    run_number: str,
    commit_sha: str = "",
    commit_author: str = "",
) -> None:
    """Run SemiCoLab IP tile precheck from the repo root."""

    # ── Validate tools ────────────────────────────────────────────────────────
    validate_tools()

    # ── Read tile_config.yaml ─────────────────────────────────────────────────
    tile_cfg_path = repo_root / "tile_config.yaml"
    if not tile_cfg_path.exists():
        raise VeriFlowError(f"tile_config.yaml not found at repo root: {repo_root}")

    raw = yaml.safe_load(tile_cfg_path.read_text(encoding="utf-8")) or {}
    tile_config = TileConfigCI.from_dict(raw)

    # ── Find RTL sources ──────────────────────────────────────────────────────
    rtl_dir = repo_root / "rtl"
    if not rtl_dir.exists():
        raise VeriFlowError(f"rtl/ directory not found at: {rtl_dir}")

    rtl_files = sorted(rtl_dir.glob("*.v"))
    if not rtl_files:
        raise VeriFlowError("No .v files found in rtl/")

    top_file = rtl_dir / f"{tile_config.top_module}.v"
    if not top_file.exists():
        raise VeriFlowError(
            f"No .v file found for top_module='{tile_config.top_module}' in rtl/"
        )

    # ── Detect testbench ──────────────────────────────────────────────────────
    tests_dir = repo_root / "tests"
    has_testbench = tests_dir.exists() and any(tests_dir.glob("*.v"))

    # ── Setup output directories ──────────────────────────────────────────────
    outputs_dir = repo_root / "outputs"
    docs_dir    = outputs_dir / "docs"
    logs_dir    = outputs_dir / "logs"

    docs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # ── Delete submit.yaml from previous run (always) ─────────────────────────
    submit_yaml_path = docs_dir / "submit.yaml"
    submit_yaml_path.unlink(missing_ok=True)

    # ── Repo identity ─────────────────────────────────────────────────────────
    github_repo = os.environ.get("GITHUB_REPOSITORY", "")
    repo_name   = github_repo.split("/")[-1] if github_repo else repo_root.name
    repo_owner  = github_repo.split("/")[0] if "/" in github_repo else ""
    tile_id     = repo_name
    today_str   = date.today().isoformat()

    print(f"[precheck] Tile   : {tile_config.tile_name} ({tile_id})")
    print(f"[precheck] Commit : {commit_sha[:7] if commit_sha else 'local'}")

    # ── Template files (tb_base + tb_tasks for connectivity check) ────────────
    template_dir  = Path(__file__).parent.parent / "template"
    tb_base_path  = template_dir / "tb_base.v"
    tb_tasks_path = template_dir / "tb_tasks.v"

    if not tb_base_path.exists():
        raise VeriFlowError(f"tb_base.v not found: {tb_base_path}")
    if not tb_tasks_path.exists():
        raise VeriFlowError(f"tb_tasks.v not found: {tb_tasks_path}")

    # ── Result accumulators ───────────────────────────────────────────────────
    conn_result  = "SKIPPED"
    synth_result = "SKIPPED"
    synth_parsed = {"cells": "", "warnings": "0", "errors": "0", "has_latches": False}

    conn_log_path  = logs_dir / "connectivity.log"
    synth_log_path = logs_dir / "synth.log"

    # ── Connectivity check ────────────────────────────────────────────────────
    print("[precheck] Running connectivity check...")
    conn_result = run_connectivity_check(
        rtl_files=rtl_files,
        tb_base_path=tb_base_path,
        tb_tasks_path=tb_tasks_path,
        top_module=tile_config.top_module,
        log_path=conn_log_path,
    )
    print(f"[precheck] Connectivity: {conn_result}")

    if conn_result == "FAIL":
        print("[precheck] Connectivity FAILED — generating report and stopping")
        _finalize(
            repo_root=repo_root, docs_dir=docs_dir, logs_dir=logs_dir,
            tile_id=tile_id, repo_name=repo_name, repo_owner=repo_owner,
            tile_config=tile_config,
            conn_result=conn_result, synth_result="SKIPPED",
            synth_parsed={"cells": "", "warnings": "0", "errors": "0", "has_latches": False},
            commit_sha=commit_sha, commit_author=commit_author,
            rtl_files=rtl_files, has_testbench=has_testbench,
            today_str=today_str,
        )
        raise VeriFlowError("Precheck FAILED — connectivity check did not pass")

    # ── Synthesis ─────────────────────────────────────────────────────────────
    print("[precheck] Running synthesis...")
    synth_result, synth_parsed = run_synthesis(
        rtl_files=rtl_files,
        top_module=tile_config.top_module,
        synth_log_path=synth_log_path,
    )
    print(f"[precheck] Synthesis: {synth_result}")

    # ── Finalize ──────────────────────────────────────────────────────────────
    _finalize(
        repo_root=repo_root, docs_dir=docs_dir, logs_dir=logs_dir,
        tile_id=tile_id, repo_name=repo_name, repo_owner=repo_owner,
        tile_config=tile_config,
        conn_result=conn_result, synth_result=synth_result,
        synth_parsed=synth_parsed, commit_sha=commit_sha,
        commit_author=commit_author, rtl_files=rtl_files,
        has_testbench=has_testbench, today_str=today_str,
    )
    if synth_result == "FAIL":
        raise VeriFlowError("Precheck FAILED — synthesis did not pass")


def _finalize(
    repo_root, docs_dir, logs_dir,
    tile_id, repo_name, repo_owner,
    tile_config, conn_result, synth_result, synth_parsed,
    commit_sha, commit_author, rtl_files,
    has_testbench, today_str,
):
    cells  = synth_parsed.get("cells", "")
    status = "PASS" if conn_result == "PASS" and synth_result == "PASS" else "FAIL"

    # ── results.json ──────────────────────────────────────────────────────────
    results = {
        "tile_id":      tile_id,
        "status":       status,
        "connectivity": conn_result,
        "synthesis":    synth_result,
        "cells":        int(cells) if cells else 0,
        "date":         today_str,
        "commit":       commit_sha,
        "author":       commit_author,
        "rtl_path":     "rtl",
    }
    (docs_dir / "results.json").write_text(
        json.dumps(results, indent=2), encoding="utf-8"
    )
    print("[precheck] Updated results.json")

    # ── netlist.svg ───────────────────────────────────────────────────────────
    from veriflow.generators.netlist_svg import generate_netlist_svg
    svg_ok = generate_netlist_svg(
        rtl_files=rtl_files,
        top_module=tile_config.top_module,
        output_path=docs_dir / "netlist.svg",
    )
    print(f"[precheck] {'Generated' if svg_ok else 'Skipped'} netlist.svg")

    # ── datasheet.pdf ─────────────────────────────────────────────────────────
    from veriflow.generators.datasheet import generate_datasheet_md, convert_html_to_pdf
    html_path = docs_dir / "datasheet.html"
    generate_datasheet_md(
        repo_name=repo_name,
        tile_config=tile_config,
        run_date=today_str,
        connectivity=conn_result,
        synthesis=synth_result,
        cells=cells,
        status=status,
        commit_sha=commit_sha,
        output_path=html_path,
    )
    pdf_ok = convert_html_to_pdf(html_path, docs_dir / "datasheet.pdf")
    if pdf_ok:
        html_path.unlink(missing_ok=True)
    print(f"[precheck] {'Generated' if pdf_ok else 'Skipped'} datasheet.pdf")

    # ── submit.yaml (only on PASS) ────────────────────────────────────────────
    submit_url = None
    if status == "PASS":
        repo_url = f"https://github.com/{repo_owner}/{repo_name}" if repo_owner else ""
        _generate_submit_yaml(
            path=docs_dir / "submit.yaml",
            tile_config=tile_config,
            repo_url=repo_url,
            commit_sha=commit_sha,
        )
        submit_url = _build_submit_url(
            tile_config=tile_config,
            repo_url=repo_url,
            commit_sha=commit_sha,
        )
        print("[precheck] Generated submit.yaml")

    # ── README.md ─────────────────────────────────────────────────────────────
    github_repository = os.environ.get("GITHUB_REPOSITORY", repo_root.name)
    badge_url = (
        f"https://github.com/{github_repository}/"
        f"actions/workflows/precheck.yml/badge.svg"
    )
    from veriflow.generators.readme_ci import generate_readme_ci
    generate_readme_ci(
        repo_name=repo_name,
        tile_config=tile_config,
        run_date=today_str,
        connectivity=conn_result,
        synthesis=synth_result,
        cells=cells,
        status=status,
        commit_sha=commit_sha,
        badge_url=badge_url,
        has_testbench=has_testbench,
        submit_url=submit_url,
        output_path=repo_root / "README.md",
    )
    print("[precheck] Updated README.md")

    print()
    print(f"Precheck {'PASSED' if status == 'PASS' else 'FAILED'}.")
    print(f"  Tile   : {tile_config.tile_name}")
    print(f"  Status : {status}")
    if status == "PASS":
        print(f"  Submit : outputs/docs/submit.yaml")


def _generate_submit_yaml(
    path: Path,
    tile_config: TileConfigCI,
    repo_url: str,
    commit_sha: str,
) -> None:
    """Write submit.yaml with submission data."""
    lines = [
        f"tile_name:    \"{tile_config.tile_name}\"",
        f"tile_author:  \"{tile_config.tile_author}\"",
        f"top_module:   \"{tile_config.top_module}\"",
        f"version:      \"{tile_config.version}\"",
        f"repo_url:     \"{repo_url}\"",
        f"commit:       \"{commit_sha[:7] if commit_sha else ''}\"",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _build_submit_url(
    tile_config: TileConfigCI,
    repo_url: str,
    commit_sha: str,
) -> str:
    """Build pre-filled GitHub Issue Form URL."""
    title = urllib.parse.quote(f"Tile Submission: {tile_config.tile_name}")
    body_lines = [
        f"**Tile Name:** {tile_config.tile_name}",
        f"**Author:** {tile_config.tile_author}",
        f"**Top Module:** {tile_config.top_module}",
        f"**Version:** {tile_config.version}",
        f"**Repo URL:** {repo_url}",
        f"**Commit:** {commit_sha[:7] if commit_sha else ''}",
    ]
    body = urllib.parse.quote("\n".join(body_lines))
    return f"{REGISTRY_ISSUE_FORM_URL}&title={title}&body={body}"
