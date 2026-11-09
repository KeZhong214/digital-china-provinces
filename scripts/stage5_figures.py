"""第五阶段图表：高级版主图与辅图。

用法：
    python scripts/stage5_figures.py            # 全部
    python scripts/stage5_figures.py map_d1     # 单图

数据：data/processed/stage5/ + 阶段3审核面板；底图：data/raw/geo/china_provinces_100000_full.json。
不新增检索、不合成综合分、不改动任何省的原始值。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage4_style as base  # noqa: E402
import stage5_geo as geo  # noqa: E402
import stage5_style as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/stage5"
S4 = ROOT / "data/processed/stage4"
CMAP = geo.ChinaMap()
MAIN_WINDOW = CMAP.main_window(lat_min=17.4)
INSET_WINDOW = geo.window_from_lonlat(105.0, 125.0, 2.2, 24.6)

# 省名避让：dx, dy（英寸，正右/正上）+ 是否需要引线
LABELS: dict[str, tuple[float, float, bool]] = {
    "北京": (0.04, 0.40, True),
    "天津": (0.50, 0.10, True),
    "河北": (-0.02, -0.20, False),
    "山西": (-0.06, -0.10, False),
    "内蒙古": (-0.10, 0.06, False),
    "上海": (0.60, 0.02, True),
    "江苏": (0.02, 0.16, False),
    "浙江": (0.14, -0.18, True),
    "安徽": (-0.18, -0.10, False),
    "福建": (0.16, -0.10, False),
    "江西": (-0.04, 0.08, False),
    "山东": (0.08, 0.10, False),
    "河南": (-0.10, -0.10, False),
    "湖北": (-0.08, 0.10, False),
    "湖南": (-0.06, -0.14, False),
    "广东": (-0.12, -0.10, False),
    "广西": (-0.14, 0.04, False),
    "海南": (-0.04, -0.24, True),
    "重庆": (-0.22, 0.06, True),
    "四川": (-0.20, 0.00, False),
    "贵州": (-0.10, -0.12, False),
    "云南": (-0.16, -0.02, False),
    "西藏": (-0.08, 0.06, False),
    "陕西": (0.02, 0.12, False),
    "甘肃": (-0.24, 0.06, False),
    "青海": (-0.12, 0.04, False),
    "宁夏": (-0.16, 0.36, True),
    "辽宁": (0.16, 0.04, False),
    "吉林": (0.10, 0.10, False),
    "黑龙江": (0.04, 0.14, False),
    "新疆": (-0.04, 0.02, False),
}


def draw_note_band(c, y_top: float, title: str, text: str, left: float = 0.62,
                   width: float | None = None, pad: float = 0.13, text_size: float = 8.5):
    """绘图区下方通栏提示带：浅底 + 左侧色条 + 标题 + 折行说明。返回占用高度。"""
    width = width or (c.w - 2 * left)
    max_units = (width - 0.42) * 72 / text_size * 0.96
    wrapped = base.wrap_display(text, max_units)
    line_h = 0.195
    height = pad * 2 + 0.27 + line_h * len(wrapped)
    c.fig.add_artist(
        FancyBboxPatch(
            (c.fx(left), c.fy(y_top + height)),
            c.fx(width),
            height / c.h,
            boxstyle="round,pad=0,rounding_size=0.006",
            transform=c.fig.transFigure,
            facecolor=base.PANEL,
            edgecolor="none",
            zorder=4,
        )
    )
    c.fig.add_artist(
        plt.Line2D(
            [c.fx(left + 0.055), c.fx(left + 0.055)],
            [c.fy(y_top + 0.075), c.fy(y_top + height - 0.075)],
            color=base.ACCENT, lw=2.4, solid_capstyle="round",
            transform=c.fig.transFigure, zorder=5,
        )
    )
    c.text(left + 0.16, y_top + pad - 0.02, title, size=9.3, color=base.ACCENT, weight="bold", zorder=6)
    y = y_top + pad + 0.245
    for line in wrapped:
        c.text(left + 0.16, y, line, size=text_size, color=base.INK_SOFT, zorder=6)
        y += line_h
    return height


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, encoding="utf-8-sig")


def key_numbers() -> dict:
    return json.loads((DATA / "stage5_key_numbers.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 地图绘制
def draw_provinces(ax, values, breaks, *, lw=0.55, edge=st.MAP_EDGE):
    for f in CMAP.features:
        if f.adcode in geo.ADCODE_SHORT:
            fc = st.MAP_RAMP[st.assign_class(values[f.short], breaks)]
            ax.add_collection(PolyCollection(f.rings, facecolors=fc, edgecolors=edge,
                                             linewidths=lw, zorder=3))
        else:
            ax.add_collection(PolyCollection(f.rings, facecolors=st.MAP_BASE, edgecolors=edge,
                                             linewidths=0.35, zorder=2))


def draw_jd(ax, lw=0.9):
    ax.add_collection(PolyCollection(CMAP.jd_rings, facecolors=st.MAP_JD, edgecolors=st.MAP_JD,
                                     linewidths=lw, zorder=4))


def province_labels(ax, values, breaks, *, size=6.2, skip: set[str] | None = None,
                    value_labels: set[str] | None = None, fmt="{:.2f}"):
    skip = skip or set()
    value_labels = value_labels or set()
    for f in CMAP.features:
        if f.adcode not in geo.ADCODE_SHORT or f.center is None or f.short in skip:
            continue
        cls = st.assign_class(values[f.short], breaks)
        color = st.MAP_TEXT_ON[cls]
        halo = "white" if color != "#FFFFFF" else "#12333D"
        text = f.short
        if f.short in value_labels:
            text = f"{f.short}\n{fmt.format(values[f.short])}"
            color = st.ACCENT
            halo = "white"
        dx, dy, arrow = LABELS.get(f.short, (0.0, 0.0, False))
        kw = dict(
            textcoords="offset points", xytext=(dx * 72, dy * 72), ha="center", va="center",
            fontsize=size, color=color, zorder=8, fontweight="bold" if f.short in value_labels else "normal",
            linespacing=0.95,
            path_effects=[pe.withStroke(linewidth=1.6, foreground=halo)],
        )
        if arrow:
            ax.annotate(text, xy=(f.center[0], f.center[1]), arrowprops=dict(
                arrowstyle="-", color=color, lw=0.55, alpha=0.9, shrinkA=1, shrinkB=2), **kw)
        else:
            ax.annotate(text, xy=(f.center[0], f.center[1]), **kw)


def draw_map_panel(c, box, values, breaks, *, labels=True, label_size=6.2, skip_labels=None,
                   value_labels=None, fmt="{:.2f}"):
    x0, y0, w, h = box
    x_min, x_max, y_min, y_max = MAIN_WINDOW
    aspect = (x_max - x_min) / (y_max - y_min)
    if w / h > aspect:
        hh, ww = h, h * aspect
        left, top = x0 + (w - ww) / 2, y0
    else:
        ww, hh = w, w / aspect
        left, top = x0, y0 + (h - hh) / 2
    ax = c.axes(left, top, ww, hh)
    ax.set_aspect("equal")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.axis("off")
    draw_provinces(ax, values, breaks)
    draw_jd(ax, lw=0.85)
    if labels:
        province_labels(ax, values, breaks, size=label_size, skip=skip_labels,
                        value_labels=value_labels, fmt=fmt)
    return ax, (left, top, ww, hh)


def draw_inset(c, box, values, breaks):
    x0, y0, w, h = box
    x_min, x_max, y_min, y_max = INSET_WINDOW
    ax = c.axes(x0, y0, w, h)
    ax.set_aspect("auto")
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_facecolor(st.MAP_SEA)
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_color(st.HAIRLINE)
        spine.set_linewidth(0.8)
    draw_provinces(ax, values, breaks, lw=0.3)
    draw_jd(ax, lw=0.7)
    ax.text(0.5, 0.035, "南海诸岛", transform=ax.transAxes, ha="center", va="bottom",
            fontsize=6.0, color=st.MUTED)
    return ax


def legend_vertical(c, x, y_top, breaks, *, fmt="{:.1f}", unit="", title="分级（五分位）", pitch=0.20):
    c.text(x, y_top, title, size=7.4, color=st.MUTED, weight="bold")
    y = y_top + 0.19
    for i in range(4, -1, -1):
        c.fig.add_artist(
            Rectangle((c.fx(x), c.fy(y + 0.13)), c.fx(0.22), 0.13 / c.h,
                      facecolor=st.MAP_RAMP[i], edgecolor=st.HAIRLINE, linewidth=0.6,
                      transform=c.fig.transFigure, zorder=5)
        )
        c.text(x + 0.30, y + 0.01, st.class_label(i, breaks, fmt), size=7.2, color=st.INK_SOFT)
        y += pitch
    c.text(x, y + 0.00, unit, size=7.2, color=st.MUTED)


def legend_horizontal(c, x, y, breaks, *, fmt="{:.1f}", unit="", pitch=0.72):
    """横向五级图例：色块在上，区间文字在色块下方。"""
    for i in range(5):
        cx = x + i * pitch
        c.fig.add_artist(
            Rectangle((c.fx(cx), c.fy(y + 0.16)), c.fx(0.34), 0.16 / c.h,
                      facecolor=st.MAP_RAMP[i], edgecolor=st.HAIRLINE, linewidth=0.6,
                      transform=c.fig.transFigure, zorder=5)
        )
        c.text(cx + 0.17, y + 0.24, st.class_label(i, breaks, fmt), size=6.6, color=st.INK_SOFT,
               ha="center")
    c.text(x + 5 * pitch + 0.10, y + 0.18, f"单位：{unit}", size=6.8, color=st.MUTED)


def callout(c, ax, name, value, *, dx_km, dy_km, ha="left", color=st.ACCENT, fmt="{:.2f}",
            skip_label: bool = True):
    """在地图数据坐标中，从省会中心引一条短线到偏移点，标注省名与数值。"""
    f = CMAP.by_short()[name]
    tx, ty = f.center[0] + dx_km, f.center[1] + dy_km
    ax.annotate(
        "",
        xy=(f.center[0], f.center[1]),
        xycoords="data",
        xytext=(tx, ty),
        textcoords="data",
        arrowprops=dict(arrowstyle="-", color=color, lw=0.7, shrinkA=2, shrinkB=3, alpha=0.95),
        annotation_clip=False,
        zorder=9,
    )
    ax.text(tx + (18 if ha == "left" else -18), ty, f"{name} {fmt.format(value)}",
            fontsize=8.4, color=color, weight="bold", ha=ha, va="center", zorder=10,
            path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])


# ------------------------------------------------------------------ 地图主图
def map_figure(metric: str, combo: bool) -> list[Path]:
    keys = key_numbers()
    panel = read(f"map_panel_{metric}.csv")
    cls_df = read(f"map_classes_{metric}.csv")
    breaks = [float(b) for b in cls_df["break_value"].tolist() if str(b) not in ("", "nan")]
    values = dict(zip(panel["short_name"], panel["value"]))
    fmt = "{:.2f}"

    st.use_style()
    if combo:
        c = st.Canvas(13.333, 7.5)
    else:
        c = st.Canvas(10.6, 8.4)

    kicker = f"图 {'A' if metric == 'd1' else 'B'} ｜ 主图 · {'D1' if metric == 'd1' else 'D2'}"
    if metric == "d1":
        title = "企业数字交易应用：北京最高，东部并非整体高位"
        subtitle = ("2024年全年 ｜ 31个省级行政区 ｜ 单位：% ｜ 五分位分级 ｜ "
                    "调查企业电商参与比例，不是数字经济规模")
    else:
        title = "固定宽带接入配置：海南最高，广东最低"
        subtitle = ("2024年末 ｜ 31个省级行政区 ｜ 单位：户/百人 ｜ 五分位分级 ｜ "
                    "每百人固定宽带账户数，只测接入配置")
    head_bottom = c.header(kicker, title, subtitle, left=0.55, top=0.38, title_size=19 if not combo else 20)

    if combo:
        map_box = (0.40, head_bottom + 0.16, 8.00, 5.12)
    else:
        map_box = (0.55, head_bottom + 0.16, 9.50, 5.72)
    key_provs = {"北京", "河北"} if metric == "d1" else {"广东", "宁夏"}
    ax, rect = draw_map_panel(c, map_box, values, breaks, label_size=6.2 if combo else 6.6,
                              value_labels=key_provs)

    if combo:
        legend_vertical(c, 8.35, 5.42, breaks, fmt="{:.1f}",
                        unit=("%" if metric == "d1" else "户/百人"), pitch=0.20)
    else:
        legend_horizontal(c, 0.55, c.h - 1.28, breaks, fmt="{:.1f}",
                          unit=("%" if metric == "d1" else "户/百人"))

    # 南海诸岛小图（地图右下角空白处）
    draw_inset(c, (rect[0] + rect[2] - 1.10, rect[1] + rect[3] - 1.28, 1.02, 1.20), values, breaks)

    if combo:
        top5 = panel.nlargest(5, "value")
        bot5 = panel.nsmallest(5, "value")
        rx = 8.35
        c.text(rx, head_bottom + 0.26, "前五", size=9.0, color=st.ACCENT, weight="bold")
        y = head_bottom + 0.52
        for _, r in top5.iterrows():
            c.text(rx, y, r["short_name"], size=10.0, color=st.INK)
            c.text(rx + 1.60, y, fmt.format(r["value"]), size=10.0, color=st.INK_SOFT, ha="right")
            c.text(rx + 1.82, y, f"{int(r['rank'])}", size=8.2, color=st.MUTED)
            y += 0.27
        y += 0.16
        c.rule(rx, rx + 2.10, y - 0.08, color=st.GRID, lw=0.7)
        y += 0.08
        c.text(rx, y, "后五", size=9.0, color=st.INK_SOFT, weight="bold")
        y += 0.24
        for _, r in bot5.iterrows():
            c.text(rx, y, r["short_name"], size=10.0, color=st.INK)
            c.text(rx + 1.60, y, fmt.format(r["value"]), size=10.0, color=st.INK_SOFT, ha="right")
            c.text(rx + 1.82, y, f"{int(r['rank'])}", size=8.2, color=st.MUTED)
            y += 0.27

    note = (
        "指标定义：有电子商务交易活动企业数 ÷ 同表调查企业数 × 100；调查范围为规模以上工业等一套表企业，不是全部企业或居民。"
        if metric == "d1" else
        "指标定义：固定宽带账户（万户）÷ 年末常住人口（万人）× 100；分子含家庭与机构账户，不测速率、覆盖或使用体验。"
    )
    src = ("数据：国家统计局《中国统计年鉴2025》表16-39（E02）；统计期2024年全年。"
           if metric == "d1" else
           "数据：国家统计局《中国统计年鉴2025》表16-36、表2-5（I203/A01）；统计期2024年末。")
    c.footer(
        [
            src,
            note,
            "分级断点为31省排序的五等分中点（见 data/processed/stage5/map_classes_*.csv）；灰色为港澳台，不在研究范围；"
            "底图为阿里云 DataV 省级边界，仅作示意。",
        ],
        left=0.55,
        bottom=0.22,
        width=c.w - 1.10,
    )
    names = {
        ("d1", True): "map_ecommerce_2024_combo",
        ("d1", False): "map_ecommerce_2024",
        ("d2", True): "map_accounts_2024_combo",
        ("d2", False): "map_accounts_2024",
    }
    return st.save(c.fig, names[(metric, combo)])


def map_d1() -> list[Path]:
    return map_figure("d1", combo=False)


def map_d1_combo() -> list[Path]:
    return map_figure("d1", combo=True)


def map_d2() -> list[Path]:
    return map_figure("d2", combo=False)


def map_d2_combo() -> list[Path]:
    return map_figure("d2", combo=True)


# ------------------------------------------------------------------ 区域哑铃图
def regional_mean_median() -> list[Path]:
    df = read("regional_mean_median.csv")
    keys = key_numbers()
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 C ｜ 区域差异",
        "四大区域：均值与中位数给出的答案不完全相同",
        "2024年 ｜ 东部10 · 中部6 · 西部12 · 东北3 ｜ 实心圆＝等权均值，空心菱形＝中位数 ｜ 左图单位%，右图单位户/百人",
        left=0.62,
        top=0.40,
        title_size=21,
    )

    panel_w, panel_h = 4.85, 3.15
    specs = [("d1", 1.05, (7.6, 14.3), [8, 10, 12, 14], "%"), ("d2", 7.55, (40.6, 53.6), [42, 45, 48, 51], "户/百人")]
    for metric, left, xlim, xticks, unit in specs:
        ax = c.axes(left=left, top=head_bottom + 0.55, width=panel_w, height=panel_h)
        st.style_axes(ax, grid_axis="x")
        sub = df[df["metric"] == metric].set_index("region")
        ys = np.arange(4)
        for yi, region in enumerate(st.REGION_ORDER):
            row = sub.loc[region]
            color = st.REGION_COLORS[region]
            ax.plot([row["mean"], row["median"]], [yi, yi], color=color, lw=1.4, alpha=0.55, zorder=3)
            ax.scatter([row["mean"]], [yi], s=130, color=color, edgecolor="white", linewidth=1.6, zorder=5)
            ax.scatter([row["median"]], [yi], s=78, marker="D", facecolor="white", edgecolor=color,
                       linewidth=1.6, zorder=6)
            ax.text(row["mean"], yi - 0.22, f"{row['mean']:.2f}", ha="center", va="bottom",
                    fontsize=8.6, color=st.INK_SOFT, zorder=7)
            ax.text(row["median"], yi + 0.22, f"{row['median']:.2f}", ha="center", va="top",
                    fontsize=8.6, color=st.MUTED, zorder=7)
        ax.set_xlim(*xlim)
        ax.set_xticks(xticks)
        ax.set_ylim(3.55, -0.85)
        ax.set_yticks(ys)
        ax.set_yticklabels([f"{r}（n={int(sub.loc[r,'n'])}）" for r in st.REGION_ORDER], fontsize=9.4,
                           color=st.INK)
        ax.tick_params(axis="y", pad=8)
        ax.tick_params(axis="x", labelsize=8.6, colors=st.MUTED)
        ax.text(0.0, 1.02, f"{'D1 企业数字交易应用' if metric=='d1' else 'D2 固定宽带接入配置'}（{unit}）",
                transform=ax.transAxes, fontsize=9.6, color=st.INK, fontweight="bold")

        # 右侧"均值/中位数名次"对照
        for yi, region in enumerate(st.REGION_ORDER):
            row = sub.loc[region]
            flip = int(row["mean_rank"]) != int(row["median_rank"])
            ax.text(1.035, yi, f"{int(row['mean_rank'])} → {int(row['median_rank'])}",
                    transform=ax.get_yaxis_transform(), fontsize=8.6,
                    color=st.ACCENT if flip else st.MUTED, va="center",
                    fontweight="bold" if flip else "normal")
        ax.text(1.035, -0.72, "均值→中位\n名次", transform=ax.get_yaxis_transform(),
                fontsize=6.8, color=st.MUTED, va="bottom")

    # 关键提示
    c.text(1.05, head_bottom + 4.06,
           "D1：西部均值 11.80 高于中部 11.36，但中位数 11.40 低于中部 12.23——次序对调",
           size=8.8, color=st.ACCENT, weight="bold")
    c.text(7.55, head_bottom + 4.06,
           "D2：均值与中位数排序一致；两区域差距很小（均值差 0.22）",
           size=8.8, color=st.MUTED)

    band_text = (
        "中西部在 D1 上整体接近：按省份等权均值西部略高，按中位数中部略高，且西部均值受重庆一省拉动"
        "（删重庆后西部 11.32）。因此本研究的结论是“接近、排序不稳健”，而不是“谁更高”。"
    )
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(base.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    footer_top = c.h - 0.92
    band_top = footer_top - band_h - 0.08
    draw_note_band(c, band_top, "排序依赖口径，这本身是研究发现", band_text, left=0.62, width=band_w)

    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39（E02）、表16-36与表2-5（I203/A01）；区域值为省内各省等权平均，未按人口或企业数加权。",
            "右列为该区域在“均值口径”与“中位数口径”下的名次（1＝最高）；红色表示两种口径名次不一致。区域名后括号为省数。",
            "底表 data/processed/stage5/regional_mean_median.csv；五分位分级与地图一致，见 figure_index_revised.md。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "regional_mean_median_comparison")


# ------------------------------------------------------------------ 散点（象限版）
def scatter_quadrant() -> list[Path]:
    df = read("scatter_quadrant_panel.csv")
    counts = read("scatter_quadrant_counts.csv")
    keys = key_numbers()
    xm = keys["quadrant"]["x_mean"]
    ym = keys["quadrant"]["y_mean"]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 D ｜ 结构关系",
        "企业应用与接入配置：两个维度几乎不重合",
        "2024年全年企业调查 × 2024年末固定宽带账户 ｜ 31个省级行政区 ｜ 虚线为31省均值（描述性参考，不是优劣分界）",
        left=0.62,
        top=0.40,
        title_size=21,
    )

    ax = c.axes(left=1.05, top=head_bottom + 0.50, width=8.30, height=4.10)
    st.style_axes(ax, grid_axis="both")
    ax.axvline(xm, color=st.MUTED, lw=0.9, ls=(0, (2.5, 2.5)), alpha=0.7, zorder=1)
    ax.axhline(ym, color=st.MUTED, lw=0.9, ls=(0, (2.5, 2.5)), alpha=0.7, zorder=1)

    for region in st.REGION_ORDER:
        sub = df[df["region_4"] == region]
        ax.scatter(sub["accounts_per100"], sub["ecommerce_pct"], s=120, color=st.REGION_COLORS[region],
                   edgecolor="white", linewidth=1.5, zorder=4)

    labels = {
        "北京": (14, -2, "left"), "河北": (0, -15, "center"), "广东": (-13, 0, "right"),
        "宁夏": (14, 6, "left"), "重庆": (14, 4, "left"), "上海": (0, 15, "center"),
        "江苏": (10, -12, "left"), "海南": (-13, 5, "right"), "山东": (-13, 5, "right"),
    }
    for name, (dx, dy, ha) in labels.items():
        row = df[df["short_name"] == name].iloc[0]
        ax.annotate(name, xy=(row["accounts_per100"], row["ecommerce_pct"]), xytext=(dx, dy),
                    textcoords="offset points", ha=ha, va="center", fontsize=9.2, color=st.INK,
                    zorder=6, path_effects=[pe.withStroke(linewidth=1.6, foreground="white")])

    ax.set_xlim(38.0, 59.6)
    ax.set_ylim(6.4, 25.2)
    ax.set_xticks([40, 45, 50, 55])
    ax.set_yticks([8, 12, 16, 20, 24])
    ax.tick_params(axis="both", labelsize=8.8, colors=st.MUTED)
    ax.set_xlabel("固定宽带接入配置（户/百人，2024年末）", fontsize=9.6, color=st.INK_SOFT, labelpad=7)
    ax.set_ylabel("企业数字交易应用（%，2024年全年）", fontsize=9.6, color=st.INK_SOFT, labelpad=8)
    st.axes_region_legend(ax)
    ax.text(xm + 0.3, 25.0, "31省均值", fontsize=7.4, color=st.MUTED, ha="left", va="top")
    ax.text(59.4, ym + 0.28, "31省均值", fontsize=7.4, color=st.MUTED, ha="right", va="bottom")

    # 右侧：象限计数
    rx = 9.85
    c.text(rx, head_bottom + 0.55, "按均值线划分的四组", size=9.2, color=st.INK, weight="bold")
    y = head_bottom + 0.85
    mapping = {r["quadrant"]: int(r["n"]) for _, r in counts.iterrows()}
    for label, key in [
        ("配置高 · 应用高", "配置高于均值·应用高于均值"),
        ("配置低 · 应用高", "配置低于均值·应用高于均值"),
        ("配置高 · 应用低", "配置高于均值·应用低于均值"),
        ("配置低 · 应用低", "配置低于均值·应用低于均值"),
    ]:
        c.text(rx, y, label, size=9.0, color=st.INK_SOFT)
        c.text(rx + 2.05, y, f"{mapping.get(key, 0)} 省", size=9.0, color=st.INK, ha="right")
        y += 0.30
    c.text(rx, y + 0.10, "仅按均值线划分的描述性计数，\n不构成类型学或优劣判断。", size=7.4, color=st.MUTED)

    c.footer(
        [
            "数据：2024年全年企业调查（《中国统计年鉴2025》表16-39，E02）× 2024年末固定宽带账户（同书表16-36、表2-5，I203/A01）。",
            "虚线为31省等权均值；相关系数仅作描述（未做检验），本图不构成因果推断，也不对省份贴“领先/滞后”标签。",
            "底表 data/processed/stage5/scatter_quadrant_panel.csv、scatter_quadrant_counts.csv。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "scatter_ecommerce_accounts_quadrant")


# ------------------------------------------------------------------ 政府档级
def gov_category() -> list[Path]:
    df = read("gov_category_counts.csv")
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 E ｜ 数字政府档级",
        "2024年网上政府档级：不是一条从东到西的直线",
        "调查窗口 2024年9月上旬—10月上旬 ｜ 31个省级行政区 ｜ 优秀 / 良好 / 中等 ｜ 只作分类展示，不转换为分数",
        left=0.62,
        top=0.40,
        title_size=21,
    )

    ax = c.axes(left=2.05, top=head_bottom + 0.62, width=9.3, height=3.35)
    ax.set_xlim(0, 100)
    ax.set_ylim(5.55, -0.75)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, pad=4)
    ax.set_facecolor(st.PAPER)

    order = ["东部", "中部", "西部", "东北", "全国31省"]
    for i, region in enumerate(order):
        row = df[df["region"] == region].iloc[0]
        yi = i if region != "全国31省" else 5
        if region == "全国31省":
            ax.axhspan(yi - 0.44, yi + 0.44, color=st.PANEL, zorder=0)
        left = 0.0
        for tier, col, pct_col in [("优秀", "excellent", "excellent_pct"),
                                   ("良好", "good", "good_pct"),
                                   ("中等", "medium", "medium_pct")]:
            w = row[pct_col]
            if w <= 0:
                continue
            ax.barh([yi], [w], left=[left], height=0.58, color=st.TIER_COLORS[tier],
                    edgecolor=st.PAPER, linewidth=1.8, zorder=3)
            ax.text(left + w / 2, yi, f"{int(row[col])} 省　{w:.1f}%", ha="center", va="center",
                    fontsize=9.0, color=st.TIER_TEXT[tier], zorder=5)
            left += w
        name = "全国 31 省" if region == "全国31省" else region
        ax.text(-2.5, yi, name, ha="right", va="center", fontsize=10.5, color=st.INK)
        if region != "全国31省":
            ax.text(-2.5, yi + 0.33, f"n={int(row['n'])}", ha="right", va="center", fontsize=7.8,
                    color=st.MUTED)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8.4, color=st.MUTED)
    ax.grid(axis="x", color=st.GRID, lw=0.8, zorder=0)

    # 档级图例
    lx = 9.95
    for i, tier in enumerate(st.TIER_ORDER):
        cx = lx + i * 0.95
        c.fig.add_artist(Rectangle((c.fx(cx), c.fy(head_bottom + 0.16)), c.fx(0.16), 0.16 / c.h,
                                   facecolor=st.TIER_COLORS[tier], edgecolor="none",
                                   transform=c.fig.transFigure, zorder=5))
        c.text(cx + 0.22, head_bottom + 0.005, tier, size=9, color=st.INK_SOFT)

    band_text = (
        "东部 10 省中 7 省优秀（70.0%），中部 6 省中仅 1 省（16.7%），西部 12 省中 5 省（41.7%）；"
        "东北 3 省无优秀、2 省为中等。若档级是一条从东到西的直线，西部不应高于中部——"
        "这提示政府数字化与经济发展水平并不同步。"
    )
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(base.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    band_top = c.h - 0.92 - band_h - 0.08
    draw_note_band(c, band_top, "档级分布与“东中西”梯度不一致", band_text, left=0.62, width=band_w)

    c.footer(
        [
            "数据：2024年网上政府发展档级调查（S27），调查窗口2024年9月上旬—10月上旬，31省全覆盖，档级沿用原报告分类。",
            "档级只作分类与占比展示，不转换为分数、不推定档内名次、不与其他指数拼接；东北仅3省，比例解读需谨慎。",
            "底表 data/processed/stage5/gov_category_counts.csv。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "gov_category_distribution")


FIGURES = {
    "map_d1": map_d1,
    "map_d1_combo": map_d1_combo,
    "map_d2": map_d2,
    "map_d2_combo": map_d2_combo,
    "regional_mean_median": regional_mean_median,
    "scatter_quadrant": scatter_quadrant,
    "gov_category": gov_category,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", default=None)
    args = parser.parse_args()
    for name in args.names or list(FIGURES):
        paths = FIGURES[name]()
        print(name, "->", ", ".join(str(p.relative_to(ROOT)) for p in paths))


if __name__ == "__main__":
    main()
