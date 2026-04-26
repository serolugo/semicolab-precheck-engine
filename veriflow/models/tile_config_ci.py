from dataclasses import dataclass


@dataclass
class TileConfigCI:
    """Tile config for SemiCoLab CI/precheck mode."""
    tile_name: str
    tile_author: str
    top_module: str
    version: str
    description: str
    ports: str
    usage_guide: str
    simulator: str
    simulator_version: str

    @classmethod
    def from_dict(cls, data: dict) -> "TileConfigCI":
        # Validate required fields
        required = ["tile_name", "tile_author", "top_module", "version",
                    "description", "ports", "usage_guide"]
        missing = [f for f in required if not data.get(f, "").strip()]
        if missing:
            from veriflow.core import VeriFlowError
            raise VeriFlowError(
                f"Missing required fields in tile_config.yaml: {', '.join(missing)}"
            )
        return cls(
            tile_name=data.get("tile_name", "").strip(),
            tile_author=data.get("tile_author", "").strip(),
            top_module=data.get("top_module", "").strip(),
            version=data.get("version", "").strip(),
            description=data.get("description", "") or "",
            ports=data.get("ports", "") or "",
            usage_guide=data.get("usage_guide", "") or "",
            simulator=data.get("simulator", "") or "",
            simulator_version=data.get("simulator_version", "") or "",
        )
