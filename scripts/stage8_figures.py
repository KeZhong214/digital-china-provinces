"""第八阶段图表：同分不同构对照图、分类敏感性区间图、画像图精修版。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.lines  # noqa: E402
import stage5_style as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/stage8"
FIG = ROOT / "reports/figures_stage8"
FIG.mkdir(parents=True, exist_ok=True)

A_COLOR = "#2E6373"   # 甲
B_COLOR = "#A97845"   # 乙
DIM_LABEL = {"D1": "D1 企业数字交易应用", "D2": "D2 固定宽带接入配置", "D3": "D3 数字政府发展指数"}


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, encoding="utf-8-sig")


def save(fig, name: str) -> list[Path]:
    png, pdf = FIG / f"{name}.png", FIG / f"{name}.pdf"
    fig.savefig(png, dpi=300, facecolor=st.PAPER)
    fig.savefig(pdf, facecolor=st.PAPER)
    import matplotlib.pyplot as plt

    plt.close(fig)
    return [png, pdf]


# ------------------------------------------------------------------ 结构对照
def structure_contrast() -> list[Path]:
    cp = read("contrast_pairs.csv")
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header("主图 6 ｜ 结构对照",
                    "同分不同构：两组省份的三维结构对照",
                    "标准化分0—100（每维在31省内 Min–Max）｜ 左：浙江 vs 北京 ｜ 右：广东 vs 宁夏 ｜ 颜色仅标识省份",
                    left=0.55, top=0.32, title_size=20)

    panels = [("A", 0.55, "浙江", "北京"), ("B", 6.90, "广东", "宁夏")]
    for gid, left, pa, pb in panels:
        a = cp[(cp.group == gid) & (cp.province == pa)].iloc[0]
        b = cp[(cp.group == gid) & (cp.province == pb)].iloc[0]
        top = head + 0.55
        c.text(left, top, f"{gid} 组", size=9.0, color=st.MUTED, weight="bold")
        c.text(left + 0.52, top - 0.04, f"{pa} {a['composite']:.2f}　vs　{pb} {b['composite']:.2f}",
               size=13.0, color=st.INK, weight="bold")
        c.text(left + 0.52, top + 0.24, f"综合分差 {a['composite_gap']:.2f} 分", size=8.6, color=st.ACCENT)
        c.rule(left, left + 5.85, top + 0.44, color=st.HAIRLINE, lw=0.9)

        bar_x0, bar_w = left + 1.45, 3.55
        row0 = top + 0.80
        for i, dim in enumerate(["D1", "D2", "D3"]):
            y = row0 + i * 0.98
            c.text(left + 0.02, y + 0.20, DIM_LABEL[dim], size=8.0, color=st.MUTED, va="center")
            for v in [0, 25, 50, 75, 100]:
                x = bar_x0 + bar_w * v / 100
                c.fig.add_artist(matplotlib.lines.Line2D(
                    [c.fx(x), c.fx(x)], [c.fy(y), c.fy(y + 0.56)], color=st.GRID, lw=0.6,
                    transform=c.fig.transFigure, zorder=1))
            for j, (row, color) in enumerate([(a, A_COLOR), (b, B_COLOR)]):
                v = float(row[f"{dim}_z"])
                ytop = y + j * 0.28
                c.fig.add_artist(Rectangle((c.fx(bar_x0), c.fy(ytop + 0.20)),
                                           c.fx(max(bar_w * v / 100, 0.004)), 0.20 / c.h,
                                           facecolor=color, edgecolor="none",
                                           transform=c.fig.transFigure, zorder=3))
                c.text(bar_x0 + bar_w * v / 100 + 0.06, ytop + 0.03, f"{v:.1f}", size=8.4,
                       color=st.INK_SOFT)
                c.text(bar_x0 - 0.08, ytop + 0.03, row["province"], size=8.0, color=color,
                       ha="right", weight="bold")

        # 面板底部注记
        ny = row0 + 3 * 0.98 - 0.02
        if gid == "A":
            notes = ["读法：浙江 D2 91.1、D3 100.0，北京 D1 100.0、D3 94.9；",
                     "两省综合分只差 2.11，但强项维度不同。"]
        else:
            notes = ["广东 D2＝0 是归一化相对最低，不等于没有宽带（原始 39.51 户/百人）；",
                     "宁夏 D3＝7.1 是标准化分，原始分 57.50；两省综合分只差 1.65。"]
        for k, line in enumerate(notes):
            c.text(left + 0.02, ny + k * 0.20, line, size=7.4, color=st.ACCENT if gid == "B" else st.INK_SOFT)

    # 图例
    lx, ly = 0.55, 6.72
    c.fig.add_artist(Rectangle((c.fx(lx), c.fy(ly + 0.15)), c.fx(0.16), 0.11 / c.h, facecolor=A_COLOR,
                               edgecolor="none", transform=c.fig.transFigure, zorder=4))
    c.text(lx + 0.22, ly + 0.02, "每组前一个省（甲）", size=8.0, color=st.INK_SOFT)
    c.fig.add_artist(Rectangle((c.fx(lx + 1.95), c.fy(ly + 0.15)), c.fx(0.16), 0.11 / c.h, facecolor=B_COLOR,
                               edgecolor="none", transform=c.fig.transFigure, zorder=4))
    c.text(lx + 2.17, ly + 0.02, "每组后一个省（乙）", size=8.0, color=st.INK_SOFT)
    c.text(lx + 4.20, ly + 0.02, "条形长度＝该维在31省中的相对位置；三条合起来才是结构。", size=8.0, color=st.MUTED)

    c.footer(
        [
            "数据：D1/D2 为2024年国家统计数据；D3 为清华团队数字政府发展指数（载《数字生态指数2025》，评价窗口未明确）。",
            "标准分＝各维在31省内 Min–Max 到0—100；综合分＝三维等权平均。本图为结构说明，不是官方排名。",
            "两组三维差异的技术度量（L1 距离）：A 组122.3、B 组151.3，仅列于附录，正文不使用该数值作现实单位。",
        ],
        left=0.55, bottom=0.12, width=c.w - 1.10,
    )
    return save(c.fig, "structure_contrast_pairs")


# ------------------------------------------------------------------ 分类敏感性
def sensitivity_by_type() -> list[Path]:
    df = read("sensitivity_by_type.csv")
    order = ["浙江", "北京", "上海", "海南", "江苏", "重庆", "广东", "青海", "宁夏", "新疆"]
    df = df.set_index("short_name").loc[order].reset_index()

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header("主图 7 ｜ 稳健性",
                    "名次对什么敏感：权重调整 与 改变指标维度分开看",
                    "两组场景性质不同，不能合并成一个区间 ｜ 横轴为名次（1＝最前）｜ 竖线＝基准名次",
                    left=0.55, top=0.32, title_size=20)

    top = head + 0.78
    row_h = 0.42
    panels = [("weight", 1.72, 5.55, "权重网格（36个点，同一指标体系内的权重扰动）", "#2E6373"),
              ("drop", 7.55, 5.55, "剔除维度（改变指标体系，不是权重微调）", "#A97845")]

    for key, x0, w, title, color in panels:
        c.text(x0, top - 0.34, title, size=8.8, color=color, weight="bold")
        for v in [1, 5, 10, 15, 20, 25]:
            x = x0 + w * (v - 1) / 30
            c.fig.add_artist(matplotlib.lines.Line2D(
                [c.fx(x), c.fx(x)], [c.fy(top - 0.14), c.fy(top + len(df) * row_h)],
                color=st.GRID, lw=0.7, transform=c.fig.transFigure, zorder=1))
            c.text(x, top - 0.09, str(v), size=7.2, color=st.MUTED, ha="center")
        for i, r in df.iterrows():
            y = top + i * row_h
            lo, hi = (r["weight_min"], r["weight_max"]) if key == "weight" else (r["drop_min"], r["drop_max"])
            xa = x0 + w * (lo - 1) / 30
            xb = x0 + w * (hi - 1) / 30
            c.fig.add_artist(matplotlib.lines.Line2D(
                [c.fx(xa), c.fx(xb)], [c.fy(y + 0.14), c.fy(y + 0.14)], color=color, lw=7.0, alpha=0.85,
                solid_capstyle="round", transform=c.fig.transFigure, zorder=3))
            bx = x0 + w * (int(r["base_rank"]) - 1) / 30
            c.fig.add_artist(matplotlib.lines.Line2D(
                [c.fx(bx), c.fx(bx)], [c.fy(y - 0.02), c.fy(y + 0.30)], color=st.INK, lw=1.4,
                transform=c.fig.transFigure, zorder=4))

    # 左侧省名（两栏共用）
    for i, r in df.iterrows():
        y = top + i * row_h
        key_prov = r["short_name"] in {"广东", "宁夏", "浙江", "北京", "江苏"}
        c.text(1.60, y + 0.06, r["short_name"], size=9.4, ha="right",
               color=st.ACCENT if key_prov else st.INK, weight="bold" if key_prov else "normal")
        c.text(0.55, y + 0.06, f"基准 {int(r['base_rank'])}", size=7.4, color=st.MUTED)

    # 图例
    lx, ly = 1.72, top + len(df) * row_h + 0.30
    c.fig.add_artist(matplotlib.lines.Line2D([c.fx(lx), c.fx(lx + 0.45)], [c.fy(ly)] * 2,
                                             color="#2E6373", lw=7.0, solid_capstyle="round",
                                             transform=c.fig.transFigure, zorder=4))
    c.text(lx + 0.52, ly - 0.06, "权重网格区间", size=7.8, color=st.INK_SOFT)
    c.fig.add_artist(matplotlib.lines.Line2D([c.fx(lx + 2.35), c.fx(lx + 2.80)], [c.fy(ly)] * 2,
                                             color="#A97845", lw=7.0, solid_capstyle="round",
                                             transform=c.fig.transFigure, zorder=4))
    c.text(lx + 2.87, ly - 0.06, "剔除维度区间", size=7.8, color=st.INK_SOFT)
    c.fig.add_artist(matplotlib.lines.Line2D([c.fx(lx + 4.55), c.fx(lx + 4.55)], [c.fy(ly - 0.07), c.fy(ly + 0.07)],
                                             color=st.INK, lw=1.4, transform=c.fig.transFigure, zorder=4))
    c.text(lx + 4.63, ly - 0.06, "基准名次", size=7.8, color=st.INK_SOFT)
    c.text(lx + 5.55, ly - 0.06, "线段越短越稳；两组性质不同，不可合并解读", size=7.8, color=st.MUTED)

    c.footer(
        [
            "示例：广东权重网格 11—24，剔除 D2 升至第6、剔除 D3 降至第27；宁夏权重网格 12—26，剔除 D3 后第9；浙江权重网格始终 1—2。",
            "基准前五为浙江、北京、上海、海南、江苏；五省在各场景中总体靠前，但相互名次与前五成员并非完全固定（江苏 top5 出现率约81%）。",
            "底表 data/processed/stage8/sensitivity_by_type.csv、sensitivity_scenarios_deduplicated.csv（42个唯一场景）。",
        ],
        left=0.55, bottom=0.12, width=c.w - 1.10,
    )
    return save(c.fig, "rank_sensitivity_by_type")


FIGURES = {"contrast": structure_contrast, "sensitivity": sensitivity_by_type}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", default=None)
    for name in parser.parse_args().names or list(FIGURES):
        paths = FIGURES[name]()
        print(name, "->", ", ".join(str(p.relative_to(ROOT)) for p in paths))


if __name__ == "__main__":
    main()
