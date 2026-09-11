#!/usr/bin/env python3
"""Run the frozen confirmation reference fixtures without rebuilding them."""

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "benchmarks/confirmation/build_cases.py"
spec = importlib.util.spec_from_file_location("confirmation_builder_read_only", path)
if spec is None or spec.loader is None:
    raise SystemExit(f"cannot load {path}")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
module.validate_references()
