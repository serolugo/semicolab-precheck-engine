# semicolab-precheck-engine

CI engine for the SemiCoLab IP tile submission workflow. Called from GitHub Actions in a participant's tile repository — validates RTL against the SemiCoLab port convention, runs synthesis, generates documentation, and produces a submission package on success.

Based on [veriflow-precheck](https://github.com/serolugo/veriflow-precheck).

---

## What it does

1. Reads `tile_config.yaml`
2. Finds RTL in `rtl/`
3. Runs connectivity check (Icarus Verilog) — validates SemiCoLab 9-port convention
4. Runs synthesis (Yosys) — validates the design is synthesizable
5. Generates `outputs/docs/` — results.json, netlist.svg, datasheet.pdf
6. Updates `README.md` with pass/fail status and results
7. On PASS — generates `outputs/docs/submit.yaml` and a pre-filled submit button

Simulation is **never run in CI**. The `tests/` directory is treated as user reference only.

---

## Requirements

- Python 3.10+
- [OSS CAD Suite](https://github.com/YosysHQ/oss-cad-suite-build/releases) (`iverilog`, `yosys`)
- `pip install pyyaml weasyprint`
- Node.js + `npm install -g netlistsvg`

---

## Expected repo structure

```
ip-tile-template/
├── rtl/
│   └── top_module.v
├── tests/              ← optional, not run in CI
├── tile_config.yaml
└── .github/
    └── workflows/
        └── precheck.yml
```

---

## tile_config.yaml

```yaml
tile_name:          ""    # required
tile_author:        ""    # required
top_module:         ""    # required — must match RTL filename
version:            ""    # required — e.g. "1.0.0"

description: |
  # required

ports: |
  # required — describe how your tile uses the SemiCoLab port convention

usage_guide: |
  # required

simulator:          ""    # optional — tool used locally
simulator_version:  ""    # optional
```

---

## SemiCoLab port convention (9 ports)

| Port | Direction | Width |
|---|---|---|
| `clk` | input | 1 |
| `arst_n` | input | 1 |
| `csr_in` | input | 16 |
| `data_reg_a` | input | 32 |
| `data_reg_b` | input | 32 |
| `data_reg_c` | output | 32 |
| `csr_out` | output | 16 |
| `csr_in_re` | output | 1 |
| `csr_out_we` | output | 1 |

---

## Exit codes

| Code | Condition |
|---|---|
| `0` | Precheck PASS |
| `1` | Connectivity FAIL, Synthesis FAIL, or error |

---

## Part of the SemiCoLab ecosystem

```
semicolab-precheck-engine   → CI gate: connectivity + synthesis
ip-tile-template            → participant template repo
semicolab-registry          → central Issue Form for submissions
```

---

## Related

- [veriflow](https://github.com/serolugo/veriflow) — local verification tool with simulation and waveforms
- [veriflow-precheck](https://github.com/serolugo/veriflow-precheck) — original precheck engine this is based on
