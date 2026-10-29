# scaffold.py - creates the repo layout from Architecture.md
from pathlib import Path

PACKAGES = [
    "data/loaders", "data/validators", "indicators", "structure", "patterns",
    "strategies", "risk", "costs", "engine", "validation", "stats",
    "execution", "monitoring", "experiments", "regime", "paper",
    "signals", "dashboard", "core",
]
PLAIN_DIRS = [
    "config", "tests", "reports", "docs/spec",
    "data/raw", "data/cache",          # datasets, gitignored
]
STRATEGIES = [
    "s1_ema_pullback", "s2_ema_crossover", "s3_sma_filter", "s4_rsi",
    "s5_fibonacci", "s6_order_block", "s7_fvg", "s8_ict_model",
    "s9_orb", "s10_chart_patterns",
]

root = Path(".")
for pkg in PACKAGES:
    p = root / pkg
    p.mkdir(parents=True, exist_ok=True)
    (p / "__init__.py").touch()
(root / "data" / "__init__.py").touch()
for d in PLAIN_DIRS:
    (root / d).mkdir(parents=True, exist_ok=True)
for s in STRATEGIES:                      # empty on purpose: no strategy code in Phase 0
    (root / "strategies" / f"{s}.py").touch()
(root / "tests" / "__init__.py").touch()
(root / "config" / "costs.yaml").touch()  # filled from the real broker charge sheet
for name in ("data/raw", "data/cache", "reports"):
    (root / name / ".gitkeep").touch()

gitignore = """.venv/
__pycache__/
*.pyc
.pytest_cache/
.hypothesis/
.ruff_cache/
.env
data/raw/*
data/cache/*
*.db
reports/*
!*/.gitkeep
"""
(root / ".gitignore").write_text(gitignore)
print("Scaffold created.")