"""第七阶段图表：双栏编号地图、三维画像热力矩阵、排名图、综合分地图。"""

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
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage4_style as base  # noqa: E402
import stage5_geo as geo  # noqa: E402
import stage5_style as st  # noqa: E402
import stage6_figures as s6  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/stage7"
FIG = ROOT / "reports/figures_stage7"
FIG.mkdir(parents=True, exist_ok=True)

REGION_ORDER = st.REGION_ORDER
HEAT = LinearSegmentedColormap.from_list("heat", ["#EDF3F2", "#B9CFCB", "#7BA3A3", "#3F7079", "#1F4E5C"])


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, encoding="utf-8-sig")


def save(fig, name: str) -> list[Path]:
    png, pdf = FIG / f"{name}.png", FIG / f"{name}.pdf"
    fig.savefig(png, dpi=300, facecolor=st.PAPER)
    fig.savefig(pdf, facecolor=st.PAPER)
    plt.close(fig)
    return [png, pdf]


def heat_color(v: float) -> tuple:
    return HEAT(np.clip(v / 100.0, 0, 1))


# ------------------------------------------------------------------ 地图底图
def draw_base_map(c, box, values, breaks, numbering, key_provs, *, chip_scale=1.25):
    ax, rect = s5draw(c, box, values, breaks)
    for _, r in numbering.iterrows():
        name = r["short_name"]
        f = s6.s5.CMAP.by_short()[name]
        dx, dy = s6.CHIP.get(name, (0.0, 0.0))
        tx = f.center[0] + dx * 72 * chip_scale
        ty = f.center[1] - dy * 72 * chip_scale
        is_key = name in key_provs
        if abs(dx) + abs(dy) > 0.12:
            ax.annotate("", xy=(f.center[0], f.center[1]), xytext=(tx, ty), textcoords="data",
                        arrowprops=dict(arrowstyle="-", color=st.MUTED, lw=0.5, alpha=0.8,
                                        shrinkA=0, shrinkB=4), zorder=8)
        ax.scatter([tx], [ty], s=86, facecolor=(st.ACCENT if is_key else "white"),
                   edgecolor=(st.ACCENT if is_key else st.INK_SOFT), linewidth=0.75, zorder=9)
        ax.text(tx, ty - 0.005, f"{int(r['map_no']):02d}", ha="center", va="center", fontsize=6.2,
                color=("white" if is_key else st.INK), zorder=10, fontweight="bold")
    tw = s6.s5.CMAP.by_short()["台湾"]
    ax.annotate("", xy=(tw.center[0], tw.center[1] + 55),
                xytext=(tw.center[0] - 10, tw.center[1] + 250), textcoords="data",
                arrowprops=dict(arrowstyle="-", color=st.INK_SOFT, lw=0.6, alpha=0.95, shrinkB=1), zorder=9)
    ax.text(tw.center[0] - 12, tw.center[1] + 285, "中国台湾省", fontsize=7.4, color=st.INK,
            ha="left", va="bottom", zorder=10, path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])
    ax.text(tw.center[0] - 12, tw.center[1] + 205, "（未纳入样本）", fontsize=6.0, color=st.MUTED,
            ha="left", va="bottom", zorder=10, path_effects=[pe.withStroke(linewidth=1.6, foreground="white")])
    return ax, rect


def s5draw(c, box, values, breaks):
    import stage5_figures as f5

    return f5.draw_map_panel(c, box, values, breaks, labels=False)


# ------------------------------------------------------------------ 地图（双栏表）
def map_double(metric: str) -> list[Path]:
    s5data = ROOT / "data/processed/stage5"
    panel = pd.read_csv(s5data / f"map_panel_{metric}.csv", encoding="utf-8-sig")
    cls = pd.read_csv(s5data / f"map_classes_{metric}.csv", encoding="utf-8-sig")
    breaks = [float(b) for b in cls["break_value"].tolist() if str(b) not in ("", "nan")]
    values = dict(zip(panel["short_name"], panel["value"]))
    numbering = read("composite_scores_31provinces.csv")[["short_name", "province_name", "region_4"]]
    num_map = pd.read_csv(ROOT / "data/processed/stage6/province_numbering.csv", encoding="utf-8-sig")
    numbering = num_map[["map_no", "short_name", "province_name", "region_4"]].sort_values("map_no")
    key_provs = {"北京", "河北", "广东", "宁夏", "重庆"}
    fmt = "{:.2f}"
    unit = "%" if metric == "d1" else "户/百人"

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    title = ("企业数字交易应用：北京最高，东部并非整体高位" if metric == "d1"
             else "固定宽带接入配置：海南最高，广东最低")
    subtitle = (f"2024年{'全年' if metric=='d1' else '末'} ｜ 中国内地31个省级行政区 ｜ 单位：{unit} ｜ "
                "五分位分级 ｜ 编号仅作标识，按区域分组排列，不代表名次")
    head = c.header(f"主图 {1 if metric == 'd1' else 2} ｜ 全国空间格局", title, subtitle,
                    left=0.50, top=0.32, title_size=19)

    map_box = (0.32, head + 0.10, 6.95, 4.86)
    ax, rect = draw_base_map(c, map_box, values, breaks, numbering, key_provs)
    import stage5_figures as f5

    f5.draw_inset(c, (rect[0] + 0.12, rect[1] + rect[3] - 1.22, 0.90, 1.08), values, breaks)
    f5.legend_horizontal(c, 0.50, rect[1] + rect[3] + 0.10, breaks, fmt="{:.1f}", unit=unit, pitch=0.60)
    c.text(4.85, rect[1] + rect[3] + 0.15, "灰色：港澳台（未纳入统计样本）", size=7.2, color=st.MUTED)

    # ---------------- 双栏对照表 ----------------
    px0, px1 = 7.55, 12.95
    col_w = (px1 - px0 - 0.35) / 2
    c.text(px0, head + 0.14, "省份编号对照（01—16 ｜ 17—31）", size=9.6, color=st.INK, weight="bold")
    top = panel.nlargest(1, "value").iloc[0]
    bot = panel.nsmallest(1, "value").iloc[0]
    c.text(px0, head + 0.40,
           f"最高 {top['short_name']} {fmt.format(top['value'])} ｜ 最低 {bot['short_name']} "
           f"{fmt.format(bot['value'])} ｜ 极差 {float(top['value']) - float(bot['value']):.2f}",
           size=8.0, color=st.MUTED)

    row_h = 0.288
    head_y = head + 0.72
    for ci, (lo, hi) in enumerate([(1, 16), (17, 31)]):
        x = px0 + ci * (col_w + 0.35)
        c.text(x, head_y - 0.02, "编号", size=8.2, color=st.MUTED, weight="bold")
        c.text(x + 0.52, head_y - 0.02, "省份", size=8.2, color=st.MUTED, weight="bold")
        c.text(x + col_w - 0.05, head_y - 0.02, "数值", size=8.2, color=st.MUTED, weight="bold", ha="right")
        c.rule(x, x + col_w, head_y + 0.14, color=st.HAIRLINE, lw=0.9)
        y = head_y + 0.24
        sub = numbering[(numbering["map_no"] >= lo) & (numbering["map_no"] <= hi)]
        prev_region = None
        for _, r in sub.iterrows():
            name = r["short_name"]
            if prev_region is not None and r["region_4"] != prev_region:
                c.rule(x, x + col_w, y - 0.06, color=st.GRID, lw=0.7)
            prev_region = r["region_4"]
            is_key = name in key_provs
            color = st.ACCENT if is_key else st.INK
            # 行头区域色条
            c.fig.add_artist(Rectangle((c.fx(x), c.fy(y + 0.20)), c.fx(0.055), 0.19 / c.h,
                                       facecolor=st.REGION_COLORS[r["region_4"]], edgecolor="none",
                                       transform=c.fig.transFigure, zorder=4))
            c.text(x + 0.14, y + 0.02, f"{int(r['map_no']):02d}", size=8.6,
                   color=(color if is_key else st.MUTED), weight=("bold" if is_key else "normal"))
            c.text(x + 0.48, y + 0.02, name, size=9.4, color=color, weight=("bold" if is_key else "normal"))
            c.text(x + col_w - 0.05, y + 0.02, fmt.format(values[name]), size=9.4,
                   color=(color if is_key else st.INK_SOFT), ha="right",
                   weight=("bold" if is_key else "normal"))
            y += row_h

    c.text(px0, 6.98, "红色为关键省份（北京、河北、广东、宁夏、重庆）；行首色条：东部/中部/西部/东北。",
           size=7.6, color=st.MUTED)
    c.footer(
        [
            ("数据：国家统计局《中国统计年鉴2025》表16-39（E02）；统计期2024年全年。"
             if metric == "d1" else
             "数据：国家统计局《中国统计年鉴2025》表16-36、表2-5（I203/A01）；统计期2024年末。"),
            ("指标定义：有电子商务交易活动企业数 ÷ 同表调查企业数 × 100；调查范围为规模以上工业等一套表企业，不是全部企业或居民。"
             if metric == "d1" else
             "指标定义：固定宽带账户（万户）÷ 年末常住人口（万人）× 100；分子含家庭与机构账户，不测速率、覆盖或使用体验。"),
            "说明：统计对象为中国内地31个省级行政区；港澳台未纳入样本统计；地图保留中国台湾省及完整版图要素。色阶只表示本图单项指标，不是综合排名。",
        ],
        left=0.50, bottom=0.16, width=c.w - 1.00,
    )
    return save(c.fig, f"map_{metric}_double_column_v1")


# ------------------------------------------------------------------ 画像热力矩阵
def _heat_row(c, x, y, w, h, value):
    c.fig.add_artist(Rectangle((c.fx(x), c.fy(y + h)), c.fx(w), h / c.h, facecolor=heat_color(value),
                               edgecolor="white", linewidth=1.0, transform=c.fig.transFigure, zorder=3))


def profile_heatmap(ppt: bool = True) -> list[Path]:
    df = read("profile_31provinces.csv").sort_values("rank")
    st.use_style()
    if ppt:
        c = st.Canvas(13.333, 7.5)
        head = c.header("主图 3 ｜ 综合画像",
                        "31省数字化发展：三个维度，一张综合画像",
                        "企业交易数字应用 × 固定宽带接入配置 × 数字政府发展 ｜ 本研究探索性综合评价",
                        left=0.50, top=0.30, title_size=19)
        label_fs, score_fs, row_h = 9.0, 8.6, 0.292
        panels = [(1, 16), (17, 31)]
        lefts = [0.55, 5.92]
        top = 1.60
    else:
        c = st.Canvas(8.9, 13.4)
        head = c.header("主图 3（报告版）｜ 综合画像",
                        "31省数字化发展：三个维度，一张综合画像",
                        "企业交易数字应用 × 固定宽带接入配置 × 数字政府发展 ｜ 本研究探索性综合评价",
                        left=0.55, top=0.40, title_size=20)
        label_fs, score_fs, row_h = 10.2, 9.8, 0.335
        panels = [(1, 31)]
        lefts = [0.55]
        top = 1.85

    for (lo, hi), left in zip(panels, lefts):
        sub = df[(df["rank"] >= lo) & (df["rank"] <= hi)]
        cols = [("名次", left + 0.02), ("省份", left + 0.40), ("D1", left + 1.22),
                ("D2", left + 1.68), ("D3", left + 2.14)]
        for label, x in cols:
            c.text(x, top - 0.20, label, size=7.8, color=st.MUTED, weight="bold")
        c.text(left + 4.42, top - 0.20, "综合得分", size=7.8, color=st.MUTED, weight="bold", ha="right")
        c.rule(left + 0.02, left + 4.48, top - 0.06, color=st.HAIRLINE, lw=0.9)
        y = top
        for _, r in sub.iterrows():
            is_key = r["short_name"] in {"北京", "河北", "广东", "宁夏", "重庆"}
            c.text(left + 0.02, y + 0.06, f"{int(r['rank'])}", size=label_fs, color=st.MUTED)
            c.fig.add_artist(Rectangle((c.fx(left + 0.30), c.fy(y + row_h - 0.05)), c.fx(0.055),
                                       (row_h - 0.10) / c.h, facecolor=st.REGION_COLORS[r["region_4"]],
                                       edgecolor="none", transform=c.fig.transFigure, zorder=4))
            c.text(left + 0.40, y + 0.06, r["short_name"], size=label_fs,
                   color=(st.ACCENT if is_key else st.INK), weight=("bold" if is_key else "normal"))
            for i, d in enumerate(["D1", "D2", "D3"]):
                _heat_row(c, left + 1.18 + i * 0.46, y + 0.04, 0.42, row_h - 0.08,
                          float(r[f"{d}_minmax"]))
            bw = 1.55 * float(r["composite"]) / 100.0
            c.fig.add_artist(Rectangle((c.fx(left + 2.64), c.fy(y + row_h - 0.09)), c.fx(max(bw, 0.004)),
                                       (row_h - 0.16) / c.h, facecolor="#4F7A82", edgecolor="none",
                                       transform=c.fig.transFigure, zorder=3))
            c.text(left + 4.42, y + 0.06, f"{r['composite']:.1f}", size=score_fs,
                   color=st.INK, ha="right")
            y += row_h

    if not ppt:
        rx = 5.75
        c.text(rx, 1.95, "热力色阶", size=9.0, color=st.MUTED, weight="bold")
        c.text(rx, 2.18, "每维在31省内 Min–Max 到 0—100", size=7.8, color=st.MUTED)
        for i in range(5):
            v = i * 25
            c.fig.add_artist(Rectangle((c.fx(rx), c.fy(2.52 + i * 0.28)), c.fx(0.30), 0.24 / c.h,
                                       facecolor=heat_color(v), edgecolor="white", linewidth=0.8,
                                       transform=c.fig.transFigure, zorder=4))
            c.text(rx + 0.38, 2.57 + i * 0.28, str(v), size=8.0, color=st.MUTED)
        c.text(rx, 4.20, "综合得分", size=9.0, color=st.MUTED, weight="bold")
        c.fig.add_artist(Rectangle((c.fx(rx), c.fy(4.56)), c.fx(0.70), 0.12 / c.h,
                                   facecolor="#4F7A82", edgecolor="none", transform=c.fig.transFigure, zorder=4))
        c.text(rx, 4.74, "三维等权平均（0—100）", size=7.8, color=st.MUTED)
        c.text(rx, 5.20, "区域色条", size=9.0, color=st.MUTED, weight="bold")
        for i, reg in enumerate(REGION_ORDER):
            c.fig.add_artist(Rectangle((c.fx(rx), c.fy(5.46 + i * 0.26)), c.fx(0.06), 0.15 / c.h,
                                       facecolor=st.REGION_COLORS[reg], edgecolor="none",
                                       transform=c.fig.transFigure, zorder=4))
            c.text(rx + 0.14, 5.40 + i * 0.26, reg, size=8.2, color=st.INK_SOFT)
        c.text(rx, 6.72, "红色省名为关键案例：\n北京、河北、广东、宁夏、重庆。", size=8.0, color=st.ACCENT)
        c.text(rx, 7.42, "读法", size=9.0, color=st.MUTED, weight="bold")
        c.text(rx, 7.66, "同行三个色块分别是该省在\nD1/D2/D3 中的相对位置；\n综合分条为三者等权平均。\n"
                         "深色表示在该指标中相对更高，\n不代表原始业务量。", size=7.8, color=st.INK_SOFT,
               linespacing=1.5)

    if ppt:
        # 右侧图例与读法
        rx = 10.95
        c.text(rx, 1.62, "热力色阶", size=8.2, color=st.MUTED, weight="bold")
        c.text(rx, 1.80, "每维在31省内 Min–Max 到 0—100", size=7.4, color=st.MUTED)
        for i in range(5):
            v = i * 25
            c.fig.add_artist(Rectangle((c.fx(rx), c.fy(2.12 + i * 0.24)), c.fx(0.26), 0.22 / c.h,
                                       facecolor=heat_color(v), edgecolor="white", linewidth=0.8,
                                       transform=c.fig.transFigure, zorder=4))
            c.text(rx + 0.34, 2.16 + i * 0.24, str(v), size=7.4, color=st.MUTED)
        c.text(rx, 3.48, "深色＝在该指标中相对更高", size=7.4, color=st.MUTED)
        c.text(rx, 3.86, "综合得分", size=8.2, color=st.MUTED, weight="bold")
        c.fig.add_artist(Rectangle((c.fx(rx), c.fy(4.28)), c.fx(0.62), 0.10 / c.h,
                                   facecolor="#4F7A82", edgecolor="none", transform=c.fig.transFigure, zorder=4))
        c.text(rx, 4.44, "三维等权平均（0—100）", size=7.4, color=st.MUTED)
        c.text(rx, 4.86, "区域色条", size=8.2, color=st.MUTED, weight="bold")
        for i, reg in enumerate(REGION_ORDER):
            c.fig.add_artist(Rectangle((c.fx(rx), c.fy(5.10 + i * 0.22)), c.fx(0.055), 0.13 / c.h,
                                       facecolor=st.REGION_COLORS[reg], edgecolor="none",
                                       transform=c.fig.transFigure, zorder=4))
            c.text(rx + 0.12, 5.04 + i * 0.22, reg, size=7.6, color=st.INK_SOFT)
        c.text(rx, 6.12, "红色省名为关键案例：\n北京、河北、广东、宁夏、重庆。", size=7.4, color=st.ACCENT)

    c.footer(
        [
            "数据：D1/D2 为2024年国家统计数据（统计年鉴2025表16-39、表16-36/表2-5）；D3 为清华团队数字政府发展指数（载《数字生态指数2025》，具体评价窗口未明确）。",
            "方法：三项分别在31省内 Min–Max 标准化到0—100，基准权重等权（各1/3）合成；同分同名次。本图为研究探索性评价，不是国家数据局官方排名。",
            "分项热力表示“在各自指标31省中的相对位置”，不是可直接比较的原始业务量或实际绩效；详细口径见 reports/stage7_scoring_method.md。",
        ],
        left=0.55, bottom=0.14, width=c.w - 1.10,
    )
    return save(c.fig, "profile_31provinces_heatmap_ranked_v1" if ppt else "profile_31provinces_heatmap_report_v1")


# ------------------------------------------------------------------ 排名图
def rank_chart() -> list[Path]:
    df = read("profile_31provinces.csv").sort_values("rank")
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header("主图 4 ｜ 探索性综合评价",
                    "31省数字化发展探索性综合评价（本研究测算）",
                    "等权合成 ｜ 分项标准分0—100 ｜ 名次为基准方案结果，稳健性见敏感性分析",
                    left=0.50, top=0.32, title_size=19)
    left, top = 0.65, 1.62
    row_h = 0.156
    bar_x0, bar_w = 3.35, 3.05
    for _, r in df.iterrows():
        y = top + (int(r["rank"]) - 1) * row_h
        is_key = r["short_name"] in {"北京", "河北", "广东", "宁夏", "重庆"}
        c.text(left, y + 0.02, f"{int(r['rank'])}", size=8.6, color=st.MUTED, ha="right")
        c.fig.add_artist(Rectangle((c.fx(left + 0.09), c.fy(y + row_h - 0.03)), c.fx(0.045),
                                   (row_h - 0.06) / c.h, facecolor=st.REGION_COLORS[r["region_4"]],
                                   edgecolor="none", transform=c.fig.transFigure, zorder=4))
        c.text(left + 0.19, y + 0.02, r["short_name"], size=8.8,
               color=(st.ACCENT if is_key else st.INK), weight=("bold" if is_key else "normal"))
        # 综合分条
        bw = bar_w * float(r["composite"]) / 100.0
        c.fig.add_artist(Rectangle((c.fx(bar_x0), c.fy(y + row_h - 0.075)), c.fx(max(bw, 0.004)),
                                   0.062 / c.h, facecolor="#4F7A82", edgecolor="none",
                                   transform=c.fig.transFigure, zorder=3))
        c.text(bar_x0 + bw + 0.06, y + 0.01, f"{r['composite']:.1f}", size=8.0, color=st.INK_SOFT)
        # 三个分项小横条
        for i, d in enumerate(["D1", "D2", "D3"]):
            x0 = 7.30 + i * 1.55
            v = float(r[f"{d}_minmax"])
            c.fig.add_artist(Rectangle((c.fx(x0), c.fy(y + row_h - 0.075)), c.fx(0.92),
                                       0.062 / c.h, facecolor=st.GRID, edgecolor="none",
                                       transform=c.fig.transFigure, zorder=2))
            c.fig.add_artist(Rectangle((c.fx(x0), c.fy(y + row_h - 0.075)),
                                       c.fx(max(0.92 * v / 100.0, 0.004)), 0.062 / c.h,
                                       facecolor=st.REGION_COLORS[r["region_4"]], edgecolor="none",
                                       transform=c.fig.transFigure, zorder=3))
    # 列头
    c.text(left, top - 0.20, "名次", size=8.2, color=st.MUTED, weight="bold", ha="right")
    c.text(left + 0.19, top - 0.20, "省份", size=8.2, color=st.MUTED, weight="bold")
    c.text(bar_x0, top - 0.20, "综合得分（0—100）", size=8.2, color=st.MUTED, weight="bold")
    for i, d in enumerate(["D1", "D2", "D3"]):
        c.text(7.30 + i * 1.55, top - 0.20, {"D1": "D1 企业应用", "D2": "D2 宽带配置", "D3": "D3 政府发展"}[d],
               size=8.2, color=st.MUTED, weight="bold")
    # 网格线
    for v in [0, 25, 50, 75, 100]:
        x = bar_x0 + bar_w * v / 100
        c.fig.add_artist(plt.Line2D([c.fx(x), c.fx(x)], [c.fy(top - 0.06), c.fy(top + 31 * row_h)],
                                    color=st.GRID, lw=0.7, transform=c.fig.transFigure, zorder=1))
        c.text(x, top + 31 * row_h + 0.04, str(v), size=7.2, color=st.MUTED, ha="center")

    rx = 11.55
    c.text(rx, 1.66, "区域", size=8.4, color=st.MUTED, weight="bold")
    for i, reg in enumerate(REGION_ORDER):
        c.fig.add_artist(Rectangle((c.fx(rx), c.fy(1.90 + i * 0.24)), c.fx(0.055), 0.13 / c.h,
                                   facecolor=st.REGION_COLORS[reg], edgecolor="none",
                                   transform=c.fig.transFigure, zorder=4))
        c.text(rx + 0.12, 1.84 + i * 0.24, reg, size=8.0, color=st.INK_SOFT)
    c.text(rx, 3.02, "红色省名为关键案例", size=7.8, color=st.ACCENT)
    c.text(rx, 3.44, "名次区间提示", size=8.4, color=st.MUTED, weight="bold")
    c.text(rx, 3.66, "广东 6—27\n宁夏 9—28\n青海 12—26\n新疆 18—31", size=7.8, color=st.INK_SOFT,
           linespacing=1.5)

    c.footer(
        [
            "数据：D1/D2 为2024年国家统计数据；D3 为清华团队数字政府发展指数（载《数字生态指数2025》，评价窗口未明确）。",
            "综合分＝三维 Min–Max 标准分等权平均；右侧三条为该省三个分项标准分，仅用于解释排名来源。本图为本研究探索性评价，不是官方排名。",
            "底表 data/processed/stage7/composite_scores_31provinces.csv；名次稳健性见 ranking_stability_summary.csv。",
        ],
        left=0.50, bottom=0.16, width=c.w - 1.00,
    )
    return save(c.fig, "exploratory_rank_31provinces_v1")


# ------------------------------------------------------------------ 综合分地图（可选）
def composite_map() -> list[Path]:
    df = read("profile_31provinces.csv").sort_values("rank")
    values = dict(zip(df["short_name"], df["composite"]))
    breaks = [round(float(np.quantile(list(values.values()), q)), 2) for q in [0.2, 0.4, 0.6, 0.8]]
    num_map = pd.read_csv(ROOT / "data/processed/stage6/province_numbering.csv", encoding="utf-8-sig")

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header("主图 5 ｜ 综合得分空间分布",
                    "31省数字化发展探索性综合评价：空间格局",
                    "本研究测算 ｜ 0—100 ｜ 五等分设色 ｜ 港澳台灰色、不参与评分",
                    left=0.55, top=0.32, title_size=19)
    ax, rect = s5draw(c, (0.45, head + 0.10, 7.95, 4.82), values, breaks)
    for _, r in num_map.iterrows():
        f = s6.s5.CMAP.by_short()[r["short_name"]]
        cls = st.assign_class(values[r["short_name"]], breaks)
        color = st.MAP_TEXT_ON[cls]
        halo = "white" if color != "#FFFFFF" else "#12333D"
        dx, dy = s6.CHIP.get(r["short_name"], (0.0, 0.0))
        ax.annotate(r["short_name"], xy=(f.center[0], f.center[1]),
                    xytext=(dx * 72 * 1.15, dy * 72 * 1.15), textcoords="offset points",
                    ha="center", va="center", fontsize=6.6, color=color, zorder=9,
                    path_effects=[pe.withStroke(linewidth=1.6, foreground=halo)])
    tw = s6.s5.CMAP.by_short()["台湾"]
    ax.text(tw.center[0] - 12, tw.center[1] + 240, "中国台湾省", fontsize=7.0, color=st.INK,
            ha="left", va="bottom", zorder=10,
            path_effects=[pe.withStroke(linewidth=1.6, foreground="white")])
    import stage5_figures as f5

    f5.draw_inset(c, (rect[0] + 0.12, rect[1] + rect[3] - 1.22, 0.90, 1.08), values, breaks)
    f5.legend_horizontal(c, 0.55, rect[1] + rect[3] + 0.12, breaks, fmt="{:.1f}", unit="分", pitch=0.66)

    rx = 8.75
    c.text(rx, head + 0.34, "这张图说什么", size=9.6, color=st.INK, weight="bold")
    items = [
        ("格局", "最高为浙江（77.7）、北京（75.6）、上海（68.2）；最低为吉林（4.9）、西藏（14.2）。"),
        ("区域", "东部均值最高（56.7），内部极差也最大（河北28.0—浙江77.7）。"),
        ("边界", "色阶为本研究探索性评分，不是官方排名；单项地图见主图1、主图2。"),
    ]
    y = head + 0.68
    for tag, text in items:
        c.text(rx, y, tag, size=8.6, color=st.ACCENT, weight="bold")
        lines = base.wrap_display(text, (13.333 - rx - 0.45) * 72 / 8.6 * 1.02)
        for i, line in enumerate(lines):
            c.text(rx + 0.58, y + i * 0.21, line, size=8.6, color=st.INK_SOFT)
        y += 0.26 + 0.21 * len(lines) + 0.20

    c.footer(
        [
            "数据：D1/D2 为2024年国家统计数据；D3 为清华团队数字政府发展指数（载《数字生态指数2025》，评价窗口未明确）。",
            "综合分＝三项 Min–Max 标准分等权平均；分级为31省五等分断点。本图为本研究探索性评价，不是国家数据局官方排名。",
            "底表 data/processed/stage7/profile_31provinces.csv。",
        ],
        left=0.55, bottom=0.14, width=c.w - 1.10,
    )
    return save(c.fig, "exploratory_composite_map_v1")


FIGURES = {
    "map_d1": lambda: map_double("d1"),
    "map_d2": lambda: map_double("d2"),
    "profile": lambda: profile_heatmap(ppt=True),
    "profile_report": lambda: profile_heatmap(ppt=False),
    "rank": rank_chart,
    "composite_map": composite_map,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", default=None)
    for name in parser.parse_args().names or list(FIGURES):
        paths = FIGURES[name]()
        print(name, "->", ", ".join(str(p.relative_to(ROOT)) for p in paths))


if __name__ == "__main__":
    main()
