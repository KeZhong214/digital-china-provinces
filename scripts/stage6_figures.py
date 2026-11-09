"""第六阶段主图：编号地图 + 信息面板、档级矩阵、旭日主图、区域图、散点图。

用法：python scripts/stage6_figures.py [name ...]
"""

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
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage4_style as base  # noqa: E402
import stage5_figures as s5  # noqa: E402
import stage5_geo as geo  # noqa: E402
import stage5_style as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/stage6"
FIG_DIR = ROOT / "reports/figures_stage6"
FIG_DIR.mkdir(parents=True, exist_ok=True)

REGION_ORDER = st.REGION_ORDER
TIER_ORDER = st.TIER_ORDER
CHIP = {  # 编号圆点的偏移（英寸）
    "北京": (0.04, 0.20), "天津": (0.22, 0.02), "河北": (-0.12, -0.06),
    "上海": (0.26, 0.00), "江苏": (0.05, 0.12), "浙江": (0.10, -0.10),
    "安徽": (-0.10, -0.08), "宁夏": (-0.14, 0.07), "重庆": (-0.11, 0.04),
    "海南": (0.00, -0.14), "广东": (-0.07, -0.13), "陕西": (0.02, 0.10),
    "山西": (-0.04, 0.09), "福建": (0.10, -0.07), "江西": (-0.02, 0.06),
    "湖南": (-0.05, -0.10), "湖北": (-0.06, 0.07), "河南": (-0.04, -0.07),
    "贵州": (-0.08, -0.09), "广西": (-0.09, 0.03), "云南": (-0.10, -0.02),
    "四川": (-0.13, 0.00), "甘肃": (-0.16, 0.05), "青海": (-0.09, 0.03),
    "内蒙古": (-0.06, 0.04), "辽宁": (0.10, 0.03), "吉林": (0.06, 0.07),
    "黑龙江": (0.03, 0.10), "新疆": (-0.03, 0.02), "西藏": (-0.06, 0.04),
    "山东": (0.06, 0.08),
}


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, encoding="utf-8-sig")


def key_numbers() -> dict:
    return json.loads((DATA / "stage6_key_numbers.json").read_text(encoding="utf-8"))


def save(fig, name: str) -> list[Path]:
    png, pdf = FIG_DIR / f"{name}.png", FIG_DIR / f"{name}.pdf"
    fig.savefig(png, dpi=300, facecolor=st.PAPER)
    fig.savefig(pdf, facecolor=st.PAPER)
    import matplotlib.pyplot as plt

    plt.close(fig)
    return [png, pdf]


# ------------------------------------------------------------------ 主图1/2：编号地图
def map_final(metric: str) -> list[Path]:
    keys = key_numbers()
    panel = read(f"map_panel_{metric}.csv") if (DATA / f"map_panel_{metric}.csv").exists() else None
    numbering = read("province_numbering.csv")
    cls_df = s5.read("map_classes_" + metric + ".csv") if False else None
    # 分级与面板沿用阶段5底表（同一口径），编号来自阶段6
    s5data = ROOT / "data/processed/stage5"
    panel = pd.read_csv(s5data / f"map_panel_{metric}.csv", encoding="utf-8-sig")
    cls = pd.read_csv(s5data / f"map_classes_{metric}.csv", encoding="utf-8-sig")
    breaks = [float(b) for b in cls["break_value"].tolist() if str(b) not in ("", "nan")]
    values = dict(zip(panel["short_name"], panel["value"]))
    ranking = dict(zip(panel["short_name"], panel["rank"]))
    tier = dict(zip(numbering["short_name"], numbering["tier"]))
    number = dict(zip(numbering["short_name"], numbering["map_no"]))
    region = dict(zip(numbering["short_name"], numbering["region_4"]))
    key_provs = set(keys["numbering"]["key_provinces"])
    fmt = "{:.2f}"
    unit = "%" if metric == "d1" else "户/百人"

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    if metric == "d1":
        title = "企业数字交易应用：北京最高，东部并非整体高位"
        subtitle = ("2024年全年 ｜ 中国内地31个省级行政区 ｜ 单位：% ｜ 五分位分级 ｜ "
                    "编号仅作标识，按区域分组排列，不代表名次")
    else:
        title = "固定宽带接入配置：海南最高，广东最低"
        subtitle = ("2024年末 ｜ 中国内地31个省级行政区 ｜ 单位：户/百人 ｜ 五分位分级 ｜ "
                    "编号仅作标识，按区域分组排列，不代表名次")
    head = c.header(f"主图 {1 if metric == 'd1' else 2} ｜ 全国空间格局",
                    title, subtitle, left=0.55, top=0.34, title_size=19)

    # 地图
    map_box = (0.42, head + 0.10, 7.55, 4.78)
    ax, rect = s5.draw_map_panel(c, map_box, values, breaks, labels=False)
    # 编号圆点
    for name, no in number.items():
        f = s5.CMAP.by_short()[name]
        dx, dy = CHIP.get(name, (0.0, 0.0))
        tx = f.center[0] + dx * 72 * 1.25
        ty = f.center[1] - dy * 72 * 1.25
        is_key = name in key_provs
        if abs(dx) + abs(dy) > 0.12:
            ax.annotate("", xy=(f.center[0], f.center[1]), xytext=(tx, ty), textcoords="data",
                        arrowprops=dict(arrowstyle="-", color=st.MUTED, lw=0.5, alpha=0.8,
                                        shrinkA=0, shrinkB=4), zorder=8)
        ax.scatter([tx], [ty], s=78, facecolor=(st.ACCENT if is_key else "white"),
                   edgecolor=(st.ACCENT if is_key else st.INK_SOFT), linewidth=0.7, zorder=9)
        ax.text(tx, ty - 0.005, str(int(no)), ha="center", va="center", fontsize=5.9,
                color=("white" if is_key else st.INK), zorder=10, fontweight="bold")
    # 中国台湾省标注：置于岛屿正北方，双行（省名 + 未纳入样本），确保完整可见
    tw = s5.CMAP.by_short()["台湾"]
    ax.annotate("", xy=(tw.center[0], tw.center[1] + 55),
                xytext=(tw.center[0] - 10, tw.center[1] + 250), textcoords="data",
                arrowprops=dict(arrowstyle="-", color=st.INK_SOFT, lw=0.6, alpha=0.95, shrinkB=1),
                zorder=9)
    ax.text(tw.center[0] - 12, tw.center[1] + 285, "中国台湾省", fontsize=7.4, color=st.INK,
            ha="left", va="bottom", zorder=10,
            path_effects=[pe.withStroke(linewidth=1.8, foreground="white")])
    ax.text(tw.center[0] - 12, tw.center[1] + 205, "（未纳入样本）", fontsize=6.0, color=st.MUTED,
            ha="left", va="bottom", zorder=10,
            path_effects=[pe.withStroke(linewidth=1.6, foreground="white")])
    # 南海诸岛小图：移到地图西南角空白海面，避免遮挡台湾
    s5.draw_inset(c, (rect[0] + 0.14, rect[1] + rect[3] - 1.26, 0.92, 1.10), values, breaks)
    # 图例（图框下方，横向五级）
    s5.legend_horizontal(c, 0.55, rect[1] + rect[3] + 0.12, breaks, fmt="{:.1f}", unit=unit, pitch=0.62)
    c.text(5.05, rect[1] + rect[3] + 0.16, "灰色：港澳台（未纳入统计样本）", size=6.8, color=st.MUTED)

    # ---------------- 右侧信息面板 ----------------
    px = 8.10
    pw = 4.68
    c.text(px, head + 0.12, "省份编号对照", size=9.2, color=st.INK, weight="bold")
    top = panel.nlargest(1, "value").iloc[0]
    bot = panel.nsmallest(1, "value").iloc[0]
    c.text(px, head + 0.36,
           f"最高 {top['short_name']} {fmt.format(top['value'])} ｜ 最低 {bot['short_name']} "
           f"{fmt.format(bot['value'])} ｜ 极差 {float(top['value']) - float(bot['value']):.2f}",
           size=7.2, color=st.MUTED)

    # 表头
    hy = head + 0.62
    cols = [("编号", px + 0.02, "left"), ("省份", px + 0.52, "left"), ("区域", px + 1.42, "left"),
            ("数值", px + 1.92, "right"), ("档级", px + 2.30, "left")]
    for label, cx, ha in cols:
        c.text(cx, hy, label, size=7.0, color=st.MUTED, weight="bold", ha=ha)
    c.rule(px, px + pw - 0.15, hy + 0.16, color=st.HAIRLINE, lw=0.8)

    y = hy + 0.24
    row_h = 0.146
    prev_region = None
    for _, r in numbering.iterrows():
        name = r["short_name"]
        if prev_region is not None and r["region_4"] != prev_region:
            c.rule(px, px + pw - 0.15, y - 0.04, color=st.GRID, lw=0.6)
        prev_region = r["region_4"]
        is_key = name in key_provs
        color = st.ACCENT if is_key else st.INK
        c.text(px + 0.02, y, f"{int(r['map_no']):02d}", size=7.0, color=(color if is_key else st.MUTED),
               weight=("bold" if is_key else "normal"))
        c.text(px + 0.52, y, name, size=7.4, color=color, weight=("bold" if is_key else "normal"))
        c.text(px + 1.42, y, r["region_4"], size=6.8, color=st.MUTED)
        c.text(px + 1.92, y, fmt.format(values[name]), size=7.2, color=(color if is_key else st.INK_SOFT),
               ha="right", weight=("bold" if is_key else "normal"))
        c.text(px + 2.30, y, tier[name], size=6.8, color=st.MUTED)
        y += row_h

    # 表下注释
    c.text(px, y + 0.10, "红色为关键省份（北京、河北、广东、宁夏、重庆）。", size=6.8, color=st.MUTED)
    c.text(px, y + 0.26, "编号按区域分组：东部1—10、中部11—16、西部17—28、东北29—31。", size=6.8,
           color=st.MUTED)

    note = ("指标定义：有电子商务交易活动企业数 ÷ 同表调查企业数 × 100；调查范围为规模以上工业等一套表企业，不是全部企业或居民。"
            if metric == "d1" else
            "指标定义：固定宽带账户（万户）÷ 年末常住人口（万人）× 100；分子含家庭与机构账户，不测速率、覆盖或使用体验。")
    src = ("数据：国家统计局《中国统计年鉴2025》表16-39（E02）；统计期2024年全年。"
           if metric == "d1" else
           "数据：国家统计局《中国统计年鉴2025》表16-36、表2-5（I203/A01）；统计期2024年末。")
    c.footer(
        [
            src,
            note,
            "说明：本研究统计对象为中国内地31个省级行政区；港澳台未纳入样本统计。地图中保留中国台湾省及相关版图要素，"
            "仅用于完整展示中国版图。底图为阿里云 DataV 省级边界，仅作示意。",
        ],
        left=0.50,
        bottom=0.20,
        width=c.w - 1.00,
    )
    return save(c.fig, f"map_{metric}_ecommerce_final" if metric == "d1" else "map_d2_accounts_final")


# ------------------------------------------------------------------ 主图5：档级矩阵
def gov_matrix() -> list[Path]:
    df = read("gov_matrix_layout.csv")
    keys = key_numbers()
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header(
        "主图 5 ｜ 数字政府档级",
        "2024年网上政府档级：区域分组下的31省分布",
        "调查窗口 2024年9月上旬—10月上旬 ｜ 31个省级行政区 ｜ 每格一省，颜色表示档级 ｜ 分类展示，不构成连续分数排序",
        left=0.55,
        top=0.34,
        title_size=20,
    )

    tile_w, tile_h, gap_x = 0.52, 0.52, 0.085
    row_y0 = head + 0.58
    row_pitch = 1.06
    left0 = 1.62
    for i, region in enumerate(REGION_ORDER):
        sub = df[df["region"] == region].reset_index(drop=True)
        y = row_y0 + i * row_pitch
        c.text(0.55, y + 0.10, region, size=11.5, color=st.REGION_COLORS[region], weight="bold")
        c.text(0.55, y + 0.34, f"{len(sub)} 省", size=7.6, color=st.MUTED)
        for _, r in sub.iterrows():
            x = left0 + (int(r["col"]) - 1) * (tile_w + gap_x)
            c.fig.add_artist(
                Rectangle((c.fx(x), c.fy(y + tile_h)), c.fx(tile_w), tile_h / c.h,
                          transform=c.fig.transFigure, facecolor=st.TIER_COLORS[r["tier"]],
                          edgecolor=st.PAPER, linewidth=1.4, zorder=3)
            )
            c.text(x + tile_w / 2, y + tile_h / 2 + 0.02, r["short_name"], size=8.6,
                   color=st.TIER_TEXT[r["tier"]], ha="center", va="center", zorder=5,
                   weight="bold" if r["tier"] == "优秀" else "normal")

    # 右侧统计
    rx = 9.12
    c.text(rx, head + 0.50, "档级分布", size=9.2, color=st.INK, weight="bold")
    y = head + 0.78
    for tier in TIER_ORDER:
        n = int(keys["gov_matrix"]["total"][tier])
        c.fig.add_artist(Rectangle((c.fx(rx), c.fy(y + 0.18)), c.fx(0.22), 0.18 / c.h,
                                   facecolor=st.TIER_COLORS[tier], edgecolor="none",
                                   transform=c.fig.transFigure, zorder=4))
        c.text(rx + 0.30, y + 0.04, tier, size=8.4, color=st.INK_SOFT)
        c.text(rx + 2.55, y + 0.04, f"{n} 省", size=8.4, color=st.INK, ha="right")
        y += 0.30

    c.rule(rx, rx + 2.55, y + 0.02, color=st.GRID, lw=0.7)
    y += 0.18
    c.text(rx, y, "各区域优秀率", size=8.2, color=st.MUTED, weight="bold")
    y += 0.26
    for region in REGION_ORDER:
        d = keys["gov_matrix"]["by_region"][region]
        pct = d["优秀"] / d["n"] * 100
        c.text(rx, y, region, size=8.0, color=st.INK_SOFT)
        c.text(rx + 1.30, y, f"{pct:.0f}%", size=8.4, color=st.REGION_COLORS[region], weight="bold", ha="right")
        # 细条
        bar_w = 1.05 * pct / 100
        c.fig.add_artist(Rectangle((c.fx(rx + 1.45), c.fy(y + 0.10)), c.fx(max(bar_w, 0.01)), 0.055 / c.h,
                                   facecolor=st.REGION_COLORS[region], edgecolor="none",
                                   transform=c.fig.transFigure, zorder=4, alpha=0.85))
        y += 0.27

    band_text = (
        "东部 10 省中 7 省优秀（70%），中部 6 省中仅 1 省（17%），西部 12 省中 5 省（42%），东北 3 省无优秀。"
        "若档级是一条从东到西的直线，西部不应高于中部——政府数字化与经济发展水平并不同步。"
    )
    band_w = c.w - 1.10
    band_h = 0.26 + 0.27 + 0.195 * len(base.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    band_top = c.h - 0.90 - band_h - 0.06
    s5.draw_note_band(c, band_top, "档级分布与“东中西”梯度不一致", band_text, left=0.55, width=band_w)

    c.footer(
        [
            "数据：2024年网上政府发展档级调查（S27），调查窗口2024年9月上旬—10月上旬，31省全覆盖，档级沿用原报告分类。",
            "本图为档级分布展示，不构成连续分数排序：档级不转数值、不推定档内名次、不与其他指数拼接；东北仅3省，比例解读需谨慎。",
            "底表 data/processed/stage6/gov_matrix_layout.csv。",
        ],
        left=0.55,
        bottom=0.20,
        width=c.w - 1.10,
    )
    return save(c.fig, "gov_category_matrix_final")


# ------------------------------------------------------------------ 主图6：旭日
def sunburst_main() -> list[Path]:
    df = read("province_numbering.csv").sort_values("map_no")
    keys = key_numbers()
    breaks = [float(c["break_value"]) for c in keys["map_classes"][0]["classes"] if c["break_value"] != ""]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header(
        "主图 6 ｜ 结构总览",
        "四大区域与31省：数字化发展的层级结构",
        "内环＝四大区域（弧长按省份数）；外环＝31省（每省等角）；颜色＝D1五分位 ｜ 结构示意，不用于精确排序",
        left=0.55,
        top=0.34,
        title_size=20,
    )
    ax = c.fig.add_axes([0.02, 0.10, 0.46, 0.76])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.16, 1.16)
    ax.set_ylim(-1.16, 1.16)
    R0, R1, R2, R3 = 0.40, 0.66, 0.68, 1.02
    total = len(df)
    angle = 90.0
    for region in REGION_ORDER:
        sub = df[df["region_4"] == region]
        span = 360.0 * len(sub) / total
        a0, a1 = angle - span, angle
        ax.add_patch(__import__("matplotlib.patches", fromlist=["Wedge"]).Wedge(
            (0, 0), R1, a0, a1, width=R1 - R0, facecolor=st.REGION_COLORS[region],
            edgecolor="white", linewidth=1.2))
        mid = np.deg2rad((a0 + a1) / 2)
        ang = (a0 + a1) / 2
        rot = ang if -90 <= ang <= 90 else ang + 180
        ax.text(0.53 * np.cos(mid), 0.53 * np.sin(mid), f"{region}\n{len(sub)}省", ha="center",
                va="center", fontsize=8.0, color="white", fontweight="bold", rotation=rot,
                rotation_mode="anchor")
        n = len(sub)
        for i, (_, row) in enumerate(sub.reset_index(drop=True).iterrows()):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            cls_id = sum(row["d1"] >= b for b in breaks)
            ax.add_patch(__import__("matplotlib.patches", fromlist=["Wedge"]).Wedge(
                (0, 0), R3, b0, b1, width=R3 - R2, facecolor=st.MAP_RAMP[cls_id],
                edgecolor="white", linewidth=0.9))
            mb = np.deg2rad((b0 + b1) / 2)
            angb = (b0 + b1) / 2
            if -90 <= angb <= 90:
                rot_b, ha = angb, "left"
            else:
                rot_b, ha = angb + 180, "right"
            ax.text(1.035 * np.cos(mb), 1.035 * np.sin(mb), row["short_name"], ha=ha, va="center",
                    fontsize=6.4, color=st.INK, rotation=rot_b, rotation_mode="anchor")
        angle = a0
    ax.text(0, 0.06, "31 省 · 4 大区域", ha="center", va="center", fontsize=11.5, color=st.INK,
            weight="bold")
    ax.text(0, -0.10, "D1 五分位着色", ha="center", va="center", fontsize=7.2, color=st.MUTED)

    rx = 7.30
    c.text(rx, head + 0.30, "这张图承担什么", size=9.4, color=st.INK, weight="bold")
    items = [
        ("层级", "内环是四大区域，外环是31省；弧长只表示省份数量，颜色表示 D1 五分位。"),
        ("作用", "让听众先建立“区域—省份”的整体结构感，再进入具体数值比较。"),
        ("边界", "角度不编码数值，不能按面积比较省份；精确比较请看主图1、主图3。"),
    ]
    y = head + 0.62
    for tag, text in items:
        c.text(rx, y, tag, size=8.2, color=st.ACCENT, weight="bold")
        lines = base.wrap_display(text, (13.333 - rx - 0.55) * 72 / 8.2 * 0.96)
        for i, line in enumerate(lines):
            c.text(rx + 0.58, y + i * 0.20, line, size=8.2, color=st.INK_SOFT)
        y += 0.22 + 0.20 * len(lines) + 0.22

    c.text(rx, y + 0.06, "区域省数", size=8.2, color=st.MUTED, weight="bold")
    y += 0.34
    for region in REGION_ORDER:
        n = int((df["region_4"] == region).sum())
        c.text(rx, y, region, size=8.0, color=st.INK_SOFT)
        c.text(rx + 1.30, y, f"{n} 省", size=8.0, color=st.INK, ha="right")
        c.fig.add_artist(Rectangle((c.fx(rx + 1.45), c.fy(y + 0.09)), c.fx(0.02 * n), 0.05 / c.h,
                                   facecolor=st.REGION_COLORS[region], edgecolor="none",
                                   transform=c.fig.transFigure, zorder=4, alpha=0.9))
        y += 0.26

    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39（E02），2024年全年；区域与省份口径同正文。",
            "说明：本图主要用于展示东中西东北与各省份的层级结构关系及相对分布，不用于精确排序判断。"
            "更具体的数值比较以地图、区域比较图和排序图为准。",
            "底表 data/processed/stage6/province_numbering.csv；分级断点见主图1。",
        ],
        left=0.55,
        bottom=0.20,
        width=c.w - 1.10,
    )
    return save(c.fig, "sunburst_region_province_main")


# ------------------------------------------------------------------ 主图3：区域
def regional_final() -> list[Path]:
    import stage5_figures as f5

    df = pd.read_csv(ROOT / "data/processed/stage5/regional_mean_median.csv", encoding="utf-8-sig")
    keys = key_numbers()
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header(
        "主图 3 ｜ 区域差异",
        "四大区域：均值与中位数给出的答案不完全相同",
        "2024年 ｜ 东部10 · 中部6 · 西部12 · 东北3 ｜ 实心圆＝等权均值，空心菱形＝中位数 ｜ 左图单位%，右图单位户/百人",
        left=0.62,
        top=0.40,
        title_size=21,
    )
    specs = [("d1", 1.05, (7.6, 14.3), [8, 10, 12, 14], "%"),
             ("d2", 7.55, (40.6, 53.6), [42, 45, 48, 51], "户/百人")]
    for metric, left, xlim, xticks, unit in specs:
        ax = c.axes(left=left, top=head + 0.55, width=4.85, height=3.15)
        st.style_axes(ax, grid_axis="x")
        sub = df[df["metric"] == metric].set_index("region")
        ys = np.arange(4)
        for yi, region in enumerate(REGION_ORDER):
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
        ax.set_yticklabels([f"{r}（n={int(sub.loc[r,'n'])}）" for r in REGION_ORDER], fontsize=9.4,
                           color=st.INK)
        ax.tick_params(axis="y", pad=8)
        ax.tick_params(axis="x", labelsize=8.6, colors=st.MUTED)
        ax.text(0.0, 1.02, f"{'D1 企业数字交易应用' if metric=='d1' else 'D2 固定宽带接入配置'}（{unit}）",
                transform=ax.transAxes, fontsize=9.6, color=st.INK, fontweight="bold")
        for yi, region in enumerate(REGION_ORDER):
            row = sub.loc[region]
            flip = int(row["mean_rank"]) != int(row["median_rank"])
            ax.text(1.035, yi, f"{int(row['mean_rank'])} → {int(row['median_rank'])}",
                    transform=ax.get_yaxis_transform(), fontsize=8.6,
                    color=st.ACCENT if flip else st.MUTED, va="center",
                    fontweight="bold" if flip else "normal")
        ax.text(1.035, -0.72, "均值→中位\n名次", transform=ax.get_yaxis_transform(),
                fontsize=6.8, color=st.MUTED, va="bottom")

    c.text(1.05, head + 4.06, "D1：西部均值 11.80 高于中部 11.36，但中位数 11.40 低于中部 12.23——次序对调",
           size=8.8, color=st.ACCENT, weight="bold")
    c.text(7.55, head + 4.06, "D2：均值与中位数排序一致；两区域差距很小（均值差 0.22）",
           size=8.8, color=st.MUTED)

    band_text = ("中西部在 D1 上整体接近：按省份等权均值西部略高，按中位数中部略高，且西部均值受重庆一省拉动"
                 "（删重庆后西部 11.32）。因此本研究的结论是“接近、排序不稳健”，而不是“谁更高”。")
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(base.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    band_top = c.h - 0.92 - band_h - 0.08
    s5.draw_note_band(c, band_top, "排序依赖口径，这本身是研究发现", band_text, left=0.62, width=band_w)
    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39（E02）、表16-36与表2-5（I203/A01）；区域值为省内各省等权平均，未按人口或企业数加权。",
            "右列为该区域在“均值口径”与“中位数口径”下的名次（1＝最高）；红色表示两种口径名次不一致。区域名后括号为省数。",
            "底表 data/processed/stage5/regional_mean_median.csv。",
        ],
        left=0.62, bottom=0.24, width=c.w - 1.24,
    )
    return save(c.fig, "regional_mean_median_final")


# ------------------------------------------------------------------ 主图4：散点
def scatter_final() -> list[Path]:
    df = pd.read_csv(ROOT / "data/processed/stage5/scatter_quadrant_panel.csv", encoding="utf-8-sig")
    counts = pd.read_csv(ROOT / "data/processed/stage5/scatter_quadrant_counts.csv", encoding="utf-8-sig")
    keys = key_numbers()
    xm, ym = keys["quadrant"]["x_mean"], keys["quadrant"]["y_mean"]
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header(
        "主图 4 ｜ 结构关系",
        "企业应用与接入配置：两个维度几乎不重合",
        "2024年全年企业调查 × 2024年末固定宽带账户 ｜ 31个省级行政区 ｜ 虚线为31省均值（描述性参考，不是优劣分界）",
        left=0.62, top=0.40, title_size=21,
    )
    ax = c.axes(left=1.05, top=head + 0.50, width=8.30, height=4.10)
    st.style_axes(ax, grid_axis="both")
    ax.axvline(xm, color=st.MUTED, lw=0.9, ls=(0, (2.5, 2.5)), alpha=0.7, zorder=1)
    ax.axhline(ym, color=st.MUTED, lw=0.9, ls=(0, (2.5, 2.5)), alpha=0.7, zorder=1)
    for region in REGION_ORDER:
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

    rx = 9.85
    c.text(rx, head + 0.55, "按均值线划分的四组", size=9.2, color=st.INK, weight="bold")
    y = head + 0.85
    mapping = {r["quadrant"]: int(r["n"]) for _, r in counts.iterrows()}
    for label, key in [("配置高 · 应用高", "配置高于均值·应用高于均值"), ("配置低 · 应用高", "配置低于均值·应用高于均值"),
                       ("配置高 · 应用低", "配置高于均值·应用低于均值"), ("配置低 · 应用低", "配置低于均值·应用低于均值")]:
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
        left=0.62, bottom=0.24, width=c.w - 1.24,
    )
    return save(c.fig, "scatter_d1_d2_final")


FIGURES = {
    "map_d1": lambda: map_final("d1"),
    "map_d2": lambda: map_final("d2"),
    "gov_matrix": gov_matrix,
    "sunburst": sunburst_main,
    "regional": regional_final,
    "scatter": scatter_final,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", default=None)
    for name in parser.parse_args().names or list(FIGURES):
        paths = FIGURES[name]()
        print(name, "->", ", ".join(str(p.relative_to(ROOT)) for p in paths))


if __name__ == "__main__":
    main()
