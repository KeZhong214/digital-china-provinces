"""第四阶段图表视觉规范（V1）实现。

统一字体、字号层级、留白、配色、参考线、图注写法与输出方式。
所有图形脚本只从这里取颜色和排版，避免各图各写一套。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports/figures_stage4"
FIG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 配色
INK = "#1C1C1A"          # 主文字
INK_SOFT = "#41403C"     # 次主文字 / 数值标签
MUTED = "#76736B"        # 图注、坐标轴
HAIRLINE = "#D9D5CC"     # 细分隔线
GRID = "#E7E3DA"         # 网格线
PAPER = "#FFFFFF"
PANEL = "#F5F3EE"        # 浅底块

REGION_COLORS = {
    "东部": "#2E6373",   # 深青（低饱和）
    "中部": "#A97845",   # 赭石
    "西部": "#5F7F5C",   # 灰绿
    "东北": "#7C6A86",   # 灰紫
}
REGION_ORDER = ["东部", "中部", "西部", "东北"]

ACCENT = "#B24A32"       # 强调 / 案例标注
ACCENT_SOFT = "#E9D3C9"
NEUTRAL = "#C9C4B8"      # 背景比较用条形

TIER_COLORS = {"优秀": "#33443E", "良好": "#93A69F", "中等": "#DBD8CF"}
TIER_TEXT = {"优秀": "#FFFFFF", "良好": "#1C1C1A", "中等": "#1C1C1A"}
TIER_ORDER = ["优秀", "良好", "中等"]

# 字号层级（pt）
FS_KICKER = 8.5
FS_TITLE = 20
FS_SUBTITLE = 11
FS_AXIS = 9.5
FS_TICK = 9.5
FS_LABEL = 9.5
FS_VALUE = 9
FS_NOTE = 8
FS_CALLOUT = 9.5

FONT = "Microsoft YaHei"


def use_style() -> None:
    plt.rcParams.update(
        {
            "font.family": FONT,
            "font.size": 10,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": PAPER,
            "axes.facecolor": PAPER,
            "savefig.facecolor": PAPER,
            "savefig.pad_inches": 0,
            "text.color": INK,
            "axes.edgecolor": HAIRLINE,
            "axes.labelcolor": INK_SOFT,
            "xtick.color": MUTED,
            "ytick.color": INK,
            "xtick.labelsize": FS_TICK,
            "ytick.labelsize": FS_TICK,
            "figure.dpi": 110,
        }
    )


class Canvas:
    """以英寸定位画布，便于精确控制留白。"""

    def __init__(self, width: float, height: float):
        self.w = width
        self.h = height
        self.fig = plt.figure(figsize=(width, height))

    # 英寸（左上原点）→ figure 坐标
    def fx(self, inch: float) -> float:
        return inch / self.w

    def fy(self, inch_from_top: float) -> float:
        return 1.0 - inch_from_top / self.h

    def axes(self, left: float, top: float, width: float, height: float):
        """left/top/width/height 均为英寸，左上原点。"""
        return self.fig.add_axes(
            [self.fx(left), self.fy(top + height), self.fx(width), height / self.h]
        )

    def text(
        self,
        x: float,
        y_from_top: float,
        s: str,
        size: float = FS_LABEL,
        color: str = INK,
        weight: str = "normal",
        ha: str = "left",
        va: str = "top",
        **kwargs,
    ):
        return self.fig.text(
            self.fx(x),
            self.fy(y_from_top),
            s,
            fontsize=size,
            color=color,
            fontweight=weight,
            ha=ha,
            va=va,
            fontfamily=FONT,
            **kwargs,
        )

    # ------------------------------------------------------------ 版式组件
    def header(
        self,
        kicker: str,
        title: str,
        subtitle: str | None = None,
        left: float = 0.35,
        top: float = 0.42,
        title_size: float = FS_TITLE,
    ) -> float:
        """返回标题区下沿的英寸位置。"""
        y = top
        self.text(left, y, kicker, size=FS_KICKER, color=MUTED, weight="bold")
        y += 0.30
        self.text(left, y, title, size=title_size, color=INK, weight="bold")
        y += 0.42
        if subtitle:
            self.text(left, y, subtitle, size=FS_SUBTITLE, color=INK_SOFT)
            y += 0.30
        return y

    def rule(self, x0: float, x1: float, y_from_top: float, color: str = HAIRLINE, lw: float = 0.8):
        self.fig.add_artist(
            plt.Line2D(
                [self.fx(x0), self.fx(x1)],
                [self.fy(y_from_top), self.fy(y_from_top)],
                color=color,
                lw=lw,
                transform=self.fig.transFigure,
                zorder=5,
            )
        )

    def footer(self, lines: list[str], left: float = 0.35, bottom: float = 0.30, width: float | None = None,
               max_units: float | None = None, line_h: float = 0.165):
        """底部图注：细分隔线 + 多行小字；自动按显示宽度折行并保证不越出画布。"""
        width = width or (self.w - 2 * left)
        max_units = max_units or (width * 72 / FS_NOTE)
        wrapped: list[str] = []
        for line in lines:
            wrapped.extend(wrap_display(line, max_units))
        rule_y = self.h - bottom - 0.08 - line_h * len(wrapped)
        self.rule(left, left + width, rule_y)
        y = rule_y + 0.07
        for line in wrapped:
            self.text(left, y, line, size=FS_NOTE, color=MUTED, va="top")
            y += line_h

    def legend_regions(self, x: float, y_from_top: float, gap: float = 1.05, labels: list[str] | None = None):
        labels = labels or REGION_ORDER
        for i, region in enumerate(labels):
            cx = x + i * gap
            self.fig.add_artist(
                Rectangle(
                    (self.fx(cx), self.fy(y_from_top + 0.11)),
                    self.fx(0.13),
                    (0.11) / self.h,
                    facecolor=REGION_COLORS[region],
                    edgecolor="none",
                    transform=self.fig.transFigure,
                    zorder=5,
                )
            )
            self.text(cx + 0.19, y_from_top, region, size=8.8, color=INK_SOFT, va="top")


def style_axes(ax, *, grid_axis: str | None = "x", grid_color: str = GRID) -> None:
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, pad=4)
    if grid_axis:
        ax.grid(axis=grid_axis, color=grid_color, lw=0.8, zorder=0)
        ax.set_axisbelow(True)
    ax.set_facecolor(PAPER)


def axes_region_legend(ax, x: float = 0.012, y: float = 0.982, gap: float = 0.088, size: float = 8.2) -> None:
    """在坐标轴内部左上角画紧凑的区域图例（散点等单轴图使用）。"""
    for i, region in enumerate(REGION_ORDER):
        cx = x + i * gap
        ax.add_patch(
            Rectangle(
                (cx, y - 0.011),
                0.0105,
                0.022,
                transform=ax.transAxes,
                facecolor=REGION_COLORS[region],
                edgecolor="none",
                zorder=7,
                clip_on=False,
            )
        )
        ax.text(cx + 0.016, y, region, transform=ax.transAxes, fontsize=size, color=INK_SOFT,
                va="center", zorder=7)


def save(fig, name: str) -> list[Path]:
    png = FIG_DIR / f"{name}.png"
    pdf = FIG_DIR / f"{name}.pdf"
    fig.savefig(png, dpi=300, facecolor=PAPER)
    fig.savefig(pdf, facecolor=PAPER)
    plt.close(fig)
    return [png, pdf]


def value_label(v: float, digits: int = 1) -> str:
    return f"{v:.{digits}f}"


def display_width(text: str) -> float:
    """按显示宽度估算：全角字符 1，半角 0.55。"""
    return sum(1.0 if ord(ch) >= 128 else 0.55 for ch in text)


def wrap_display(text: str, max_units: float) -> list[str]:
    """按显示宽度折行，优先在中文标点处断开：避免行首标点，也避免行尾只剩收尾括号。"""
    if display_width(text) <= max_units:
        return [text]
    breaks = "；，。、）】｜： 　"
    closers = "）：；，。、」】"
    lines: list[str] = []
    cur = ""
    cur_w = 0.0
    for ch in text:
        w = 1.0 if ord(ch) >= 128 else 0.55
        if cur_w + w > max_units and cur:
            idx = max((cur.rfind(p) for p in breaks), default=-1)
            if idx >= len(cur) * 0.45:
                cut = idx + 1
                while cut < len(cur) and cur[cut] in closers:
                    cut += 1
                lines.append(cur[:cut])
                cur = cur[cut:]
            else:
                lines.append(cur)
                cur = ""
            cur_w = display_width(cur)
        cur += ch
        cur_w += w
    if cur:
        lines.append(cur)
    return lines
