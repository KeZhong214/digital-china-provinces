"""第五阶段视觉规范：在第四阶段体系上增加地图与主图专用色板。

所有图仍复用 stage4_style 的字号、页眉、图注、提示带与保存逻辑，保证 4/5 阶段风格连续。
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage4_style as base  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports/figures_stage5"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# 复用第四阶段调色板
INK = base.INK
INK_SOFT = base.INK_SOFT
MUTED = base.MUTED
HAIRLINE = base.HAIRLINE
GRID = base.GRID
PAPER = base.PAPER
PANEL = base.PANEL
ACCENT = base.ACCENT
REGION_COLORS = base.REGION_COLORS
REGION_ORDER = base.REGION_ORDER
TIER_COLORS = base.TIER_COLORS
TIER_TEXT = base.TIER_TEXT
TIER_ORDER = base.TIER_ORDER
Canvas = base.Canvas
style_axes = base.style_axes
axes_region_legend = base.axes_region_legend
note_band = None  # 见 figures 脚本内的实现

# ---------------------------------------------------------------- 地图色板
# 单色顺序色阶（浅→深），用于两张地图，保证"同一含义同一颜色"
MAP_RAMP = ["#DCE6E4", "#B9CFCB", "#8DAFAC", "#5A8789", "#2E6373"]
MAP_TEXT_ON = ["#1C1C1A", "#1C1C1A", "#1C1C1A", "#FFFFFF", "#FFFFFF"]
MAP_BASE = "#E9E7E1"        # 非研究区（港澳台）
MAP_BASE_EDGE = "#FFFFFF"
MAP_EDGE = "#FFFFFF"        # 省界
MAP_JD = "#6E6A63"          # 九段线
MAP_SEA = "#FBFBFA"

FONT = base.FONT
FS_KICKER = base.FS_KICKER
FS_TITLE = base.FS_TITLE
FS_SUBTITLE = base.FS_SUBTITLE
FS_NOTE = base.FS_NOTE


def use_style() -> None:
    base.use_style()


def save(fig, name: str) -> list[Path]:
    png = FIG_DIR / f"{name}.png"
    pdf = FIG_DIR / f"{name}.pdf"
    fig.savefig(png, dpi=300, facecolor=PAPER)
    fig.savefig(pdf, facecolor=PAPER)
    plt.close(fig)
    return [png, pdf]


def quintile_classes(values: np.ndarray, k: int = 5) -> list[float]:
    """按分位数给出 k-1 个断点（升序）。"""
    qs = np.linspace(0, 1, k + 1)[1:-1]
    return [float(np.quantile(values, q)) for q in qs]


def assign_class(value: float, breaks: list[float]) -> int:
    for i, b in enumerate(breaks):
        if value < b:
            return i
    return len(breaks)


def class_label(idx: int, breaks: list[float], fmt: str = "{:.1f}") -> str:
    lo = "–∞" if idx == 0 else fmt.format(breaks[idx - 1])
    hi = "∞" if idx == len(breaks) else fmt.format(breaks[idx])
    if idx == 0:
        return f"< {hi}"
    if idx == len(breaks):
        return f"≥ {lo}"
    return f"{lo} – {hi}"
