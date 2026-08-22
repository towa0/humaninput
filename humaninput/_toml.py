"""TOML read shim: stdlib tomllib on 3.11+, tomli backport on 3.10."""

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on 3.10
    import tomli as tomllib

load = tomllib.load
loads = tomllib.loads
