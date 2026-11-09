"""第四阶段 V1 图表生成脚本。

用法：
    python scripts/stage4_figures.py            # 全部
    python scripts/stage4_figures.py fig1 fig2  # 指定图

所有数据来自 data/processed/stage4/ 底表；不新增采集、不合成综合分。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage4_style as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/stage4"


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / name, encoding="utf-8-sig")


def key_numbers() -> dict:
    return json.loads((DATA / "stage4_key_numbers.json").read_text(encoding="utf-8"))


def note_card(ax, xy, width, title, lines, accent=st.ACCENT, pad=0.018, line_h=0.030):
    """在坐标轴内画一张浅底注释卡（不用边框，靠底色和左侧色条分区）。"""
    x, y = xy
    height = 0.052 + line_h * (len(lines) + 1)
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0,rounding_size=0.008",
            transform=ax.transAxes,
            facecolor=st.PANEL,
            edgecolor="none",
            zorder=6,
            clip_on=False,
        )
    )
    ax.plot(
        [x + 0.006, x + 0.006],
        [y + 0.012, y + height - 0.012],
        transform=ax.transAxes,
        color=accent,
        lw=2.2,
        solid_capstyle="round",
        zorder=7,
        clip_on=False,
    )
    ax.text(
        x + 0.020,
        y + height - 0.014,
        title,
        transform=ax.transAxes,
        fontsize=9.2,
        color=accent,
        fontweight="bold",
        va="top",
        zorder=7,
        clip_on=False,
    )
    ty = y + height - 0.014 - line_h
    for line in lines:
        ax.text(
            x + 0.020,
            ty,
            line,
            transform=ax.transAxes,
            fontsize=8.2,
            color=st.INK_SOFT,
            va="top",
            zorder=7,
            clip_on=False,
        )
        ty -= line_h


def note_band(c, y_top: float, title: str, text: str, left: float = 0.55, width: float | None = None,
              pad: float = 0.13, text_size: float = 8.5):
    """绘图区下方通栏提示带：浅底 + 左侧色条 + 标题 + 折行说明。返回占用高度。"""
    width = width or (c.w - 2 * left)
    max_units = (width - 0.42) * 72 / text_size * 0.96
    wrapped = st.wrap_display(text, max_units)
    line_h = 0.195
    height = pad * 2 + 0.27 + line_h * len(wrapped)
    c.fig.add_artist(
        FancyBboxPatch(
            (c.fx(left), c.fy(y_top + height)),
            c.fx(width),
            height / c.h,
            boxstyle="round,pad=0,rounding_size=0.006",
            transform=c.fig.transFigure,
            facecolor=st.PANEL,
            edgecolor="none",
            zorder=4,
        )
    )
    c.fig.add_artist(
        plt.Line2D(
            [c.fx(left + 0.055), c.fx(left + 0.055)],
            [c.fy(y_top + 0.075), c.fy(y_top + height - 0.075)],
            color=st.ACCENT,
            lw=2.4,
            solid_capstyle="round",
            transform=c.fig.transFigure,
            zorder=5,
        )
    )
    c.text(left + 0.16, y_top + pad - 0.02, title, size=9.3, color=st.ACCENT, weight="bold", zorder=6)
    y = y_top + pad + 0.245
    for line in wrapped:
        c.text(left + 0.16, y, line, size=text_size, color=st.INK_SOFT, zorder=6)
        y += line_h
    return height


def ranking_panel(
    *,
    fig_name: str,
    kicker: str,
    title: str,
    subtitle: str,
    df: pd.DataFrame,
    value_col: str,
    rank_col: str,
    xlim: float,
    xticks: list[float],
    ref_value: float,
    ref_label: str,
    value_fmt: str,
    tags: dict[str, str],
    band_title: str,
    band_text: str,
    footer_lines: list[str],
    canvas: tuple[float, float] = (8.7, 11.0),
):
    """31省横向排序图（竖版），图1与图2共用同一套版式。"""
    st.use_style()
    c = st.Canvas(*canvas)
    head_bottom = c.header(kicker, title, subtitle, left=0.55, top=0.40)
    c.legend_regions(0.55, head_bottom + 0.04)

    ax_top = head_bottom + 0.76
    band_w = c.w - 1.1
    band_h = 0.26 + 0.27 + 0.195 * len(st.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    footer_top = c.h - 1.18
    band_top = footer_top - band_h - 0.12
    ax = c.axes(left=1.62, top=ax_top, width=c.w - 1.62 - 0.55, height=band_top - 0.32 - ax_top)
    st.style_axes(ax, grid_axis="x")

    df = df.reset_index(drop=True)
    y = np.arange(len(df))
    colors = [st.REGION_COLORS[r] for r in df["region_4"]]
    ax.barh(y, df[value_col], height=0.56, color=colors, zorder=3, linewidth=0)

    ax.set_ylim(len(df) - 0.45, -0.95)
    ax.set_xlim(0, xlim)
    ax.set_xticks(xticks)
    ax.set_yticks(y)
    ax.set_yticklabels(df["short_name"], fontsize=10, color=st.INK)
    ax.tick_params(axis="y", pad=7)
    ax.tick_params(axis="x", labelsize=8.8, colors=st.MUTED, pad=6)

    # 名次列
    for yi, rank in zip(y, df[rank_col]):
        ax.text(
            -0.085,
            yi,
            f"{int(rank):02d}",
            transform=ax.get_yaxis_transform(),
            ha="right",
            va="center",
            fontsize=7.8,
            color=st.MUTED,
        )

    # 数值标签与重点标注
    span = xlim
    for yi, (_, row) in enumerate(df.iterrows()):
        v = float(row[value_col])
        near_ref = v < ref_value < v + span * 0.05
        ax.text(
            v + span * 0.007,
            yi,
            value_fmt.format(v),
            va="center",
            ha="left",
            fontsize=8.6,
            color=st.INK_SOFT,
            zorder=5,
            bbox=dict(boxstyle="square,pad=0.06", fc=st.PAPER, ec="none") if near_ref else None,
        )
        tag = tags.get(row["short_name"])
        if tag:
            ax.annotate(
                tag,
                xy=(v, yi),
                xytext=(27, 0),
                textcoords="offset points",
                va="center",
                ha="left",
                fontsize=8.4,
                color=st.ACCENT,
                fontweight="bold",
                zorder=6,
                bbox=dict(boxstyle="square,pad=0.14", fc=st.PAPER, ec="none", alpha=0.92),
            )

    # 参考线
    ax.axvline(ref_value, color=st.INK_SOFT, lw=1.0, ls=(0, (4.5, 3)), zorder=4, alpha=0.85)
    ax.text(
        ref_value,
        1.008,
        ref_label,
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="bottom",
        fontsize=8.3,
        color=st.INK_SOFT,
    )

    note_band(c, band_top, band_title, band_text)
    c.footer(footer_lines, left=0.55, bottom=0.28, width=c.w - 1.1)
    return st.save(c.fig, fig_name)


# ------------------------------------------------------------------ 图1
def fig1() -> list[Path]:
    df = read("fig1_d1_ranking.csv")
    keys = key_numbers()
    nat = keys["national"]["ecommerce_weighted_rate_pct"]
    beijing = keys["cases"]["beijing"]
    hebei = keys["cases"]["hebei"]
    gap = keys["cases"]["beijing_hebei_d1_gap_pp"]

    footer = [
        "数据：《中国统计年鉴2025》表16-39（E02）。指标：企业电商参与比例＝有电子商务交易活动企业数÷同表调查企业数×100；统计期2024年全年。",
        "口径：分母为一套表调查企业（规模以上工业、有资质建筑、限额以上批零住餐、房地产开发、规模以上服务业法人），不是全部企业、个体户或居民；本图只反映交易型应用的参与面。",
        "不可读作：交易金额、应用深度、效率改善或“数字经济规模”。排序按数值从高到低；图为单项指标排序，不是综合排名。底表：data/processed/stage4/fig1_d1_ranking.csv。",
    ]
    return ranking_panel(
        fig_name="fig1_ecommerce_ranking",
        kicker="图 1 ｜ 分项画像 · D1",
        title="调查企业交易型数字应用的省际排序",
        subtitle="2024年全年 ｜ 31个省级行政区 ｜ 单位：% ｜ 按参与比例从高到低排列",
        df=df,
        value_col="d1_ecommerce_pct",
        rank_col="d1_rank",
        xlim=27,
        xticks=[0, 5, 10, 15, 20, 25],
        ref_value=nat,
        ref_label=f"全国合计 {nat:.2f}%（企业数加权）",
        value_fmt="{:.1f}",
        tags={"北京": "最高", "河北": "东部最低", "吉林": "最低"},
        band_title="同为东部，相差 14.75 个百分点",
        band_text=(
            f"北京 {beijing['d1']:.2f}%（1/31）与河北 {hebei['d1']:.2f}%（28/31）同属东部，"
            f"但两省接入配置几乎相同（{beijing['d2']:.2f} 与 {hebei['d2']:.2f} 户/百人）："
            "东部的平均位置不能代表东部每一个省，这也是本图不主张用单一均值概括区域的原因。"
        ),
        footer_lines=footer,
    )


# ------------------------------------------------------------------ 图2
def fig2() -> list[Path]:
    df = read("fig2_d2_ranking.csv")
    keys = key_numbers()
    mean = keys["descriptive"]["d2"]["mean"]
    gd = keys["cases"]["guangdong"]
    nx = keys["cases"]["ningxia"]

    footer = [
        "数据：《中国统计年鉴2025》表16-36、表2-5（I203/A01）。指标：每百人固定宽带账户数＝固定宽带账户万户÷年末常住人口万人×100；统计期2024年末。",
        "口径：分子含家庭与机构账户，不是去重居民人数；分母为常住人口。该指标只测“接入配置”，不测网速、覆盖质量、资费或实际使用体验。",
        "排序按数值从高到低；参考线为31省等权均值（描述性中心，不是全国合计）。底表：data/processed/stage4/fig2_d2_ranking.csv。",
    ]
    return ranking_panel(
        fig_name="fig2_broadband_ranking",
        kicker="图 2 ｜ 分项画像 · D2",
        title="固定宽带接入配置的省际排序",
        subtitle="2024年末 ｜ 31个省级行政区 ｜ 单位：户/百人 ｜ 按每百人账户数从高到低排列",
        df=df,
        value_col="d2_accounts_per100",
        rank_col="d2_rank",
        xlim=64,
        xticks=[0, 10, 20, 30, 40, 50],
        ref_value=mean,
        ref_label=f"31省等权均值 {mean:.2f}",
        value_fmt="{:.1f}",
        tags={"海南": "最高", "宁夏": "西部最高", "广东": "最低"},
        band_title="配置最低 ≠ 设施最弱：广东 39.51 户/百人（31/31）",
        band_text=(
            "该指标只测固定宽带接入账户配置，不测网速、覆盖质量、资费或使用体验；"
            "同年末广东千兆以上用户占比 29.78%（1503.5/5049.5 万户，单省同段数据），"
            "说明“每百人账户数”与“接入质量结构”不是同一个测量，不能据单项位置推断总体基础设施强弱。"
        ),
        footer_lines=footer,
    )


# ------------------------------------------------------------------ 图3
def fig3() -> list[Path]:
    df = read("fig3_regional_center_dispersion.csv")
    keys = key_numbers()
    frag = keys["fragility"]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 3 ｜ 区域差异",
        "四大区域：均值与中位数给出的答案不完全相同",
        "2024年 ｜ 东部10 · 中部6 · 西部12 · 东北3 ｜ 圆点＝等权均值，菱形＝中位数，横线＝省内最小—最大值 ｜ 左图单位%，右图单位户/百人",
        left=0.62,
        top=0.40,
        title_size=21,
    )
    band_text = (
        f"西部 D1 均值 {frag['west_mean_d1']:.2f}% 高于中部 {frag['central_mean_d1']:.2f}%，"
        f"但中位数 {frag['west_median_d1']:.2f}% 低于中部 {frag['central_median_d1']:.2f}%：两种中心统计量给出相反的中西次序。"
        f"仅删除重庆一省，西部均值即降至 {frag['west_mean_d1_without_chongqing']:.2f}%（低于中部），"
        "说明这一差别对个别省份敏感——只能描述当前样本，不能据此宣布稳定的区域高低。"
    )
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(st.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    footer_top = c.h - 0.92
    band_top = footer_top - band_h - 0.10
    plot_bottom = band_top - 0.30

    panel_w = 5.35
    panels = [
        ("d1", 0.98, "D1 企业数字交易应用（%）", "%", (7.0, 24.2), [8, 12, 16, 20, 24]),
        ("d2", 7.30, "D2 固定宽带接入配置（户/百人）", "户/百人", (38.2, 59.6), [40, 45, 50, 55]),
    ]
    plot_h = plot_bottom - (head_bottom + 0.42)

    for metric, left, xtitle, unit, xlim, xticks in panels:
        ax = c.axes(left=left, top=head_bottom + 0.42, width=panel_w, height=plot_h)
        st.style_axes(ax, grid_axis="x")
        sub = df[df["metric"] == metric].set_index("region")
        regions = st.REGION_ORDER
        ys = np.arange(len(regions))

        # 中/西两行浅底，提示对比对象（左右图同样处理，保持版式对称）
        for region in ["中部", "西部"]:
            yi = regions.index(region)
            ax.axhspan(yi - 0.5, yi + 0.5, color=st.PANEL, zorder=0)

        for yi, region in enumerate(regions):
            row = sub.loc[region]
            color = st.REGION_COLORS[region]
            # 极差线段
            ax.plot([row["minimum"], row["maximum"]], [yi, yi], color=color, lw=1.6, alpha=0.40, zorder=2,
                    solid_capstyle="butt")
            for edge in (row["minimum"], row["maximum"]):
                ax.plot([edge, edge], [yi - 0.12, yi + 0.12], color=color, lw=1.2, alpha=0.55, zorder=2)
            # 均值—中位数连线
            ax.plot([row["mean"], row["median"]], [yi, yi], color=color, lw=1.0, alpha=0.75, zorder=3)
            ax.scatter([row["mean"]], [yi], s=105, color=color, edgecolor="white", linewidth=1.6, zorder=5)
            ax.scatter([row["median"]], [yi], s=64, marker="D", facecolor="white", edgecolor=color,
                       linewidth=1.5, zorder=6)
            ax.text(row["mean"], yi - 0.20, f"{row['mean']:.2f}", ha="center", va="bottom", fontsize=8.0,
                    color=st.INK_SOFT, zorder=7)
            ax.text(row["median"], yi + 0.20, f"{row['median']:.2f}", ha="center", va="top", fontsize=8.0,
                    color=st.MUTED, zorder=7)

        ax.set_xlim(*xlim)
        ax.set_xticks(xticks)
        ax.set_ylim(len(regions) - 0.42, -1.15)
        ax.set_yticks(ys)
        ax.set_yticklabels([f"{r}" for r in regions], fontsize=10.5, color=st.INK)
        ax.tick_params(axis="y", pad=8)
        ax.tick_params(axis="x", labelsize=8.8, colors=st.MUTED, pad=6)
        ax.text(0.0, 1.03, xtitle, transform=ax.transAxes, fontsize=9.6, color=st.INK, fontweight="bold")

        range_txt = " ＞ ".join(
            f"{r} {sub.loc[r, 'range']:.2f}" for r in ["东部", "西部", "中部", "东北"]
        )
        ax.text(
            0.0,
            0.885,
            f"极差：{range_txt}",
            transform=ax.transAxes,
            fontsize=8.2,
            color=st.MUTED,
            va="top",
        )
        if metric == "d1":
            ax.text(
                0.0,
                0.945,
                "均值排序：西部 > 中部　｜　中位数排序：中部 > 西部",
                transform=ax.transAxes,
                fontsize=8.8,
                color=st.ACCENT,
                fontweight="bold",
                va="top",
            )
        else:
            ax.text(
                0.0,
                0.945,
                "两种中心统计量排序一致；东部极差仍最大",
                transform=ax.transAxes,
                fontsize=8.8,
                color=st.MUTED,
                va="top",
            )

    note_band(c, band_top, "均值与中位数可以给出不同排序", band_text, left=0.62, width=band_w)
    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39（E02）、表16-36与表2-5（I203/A01）；区域值为省内各省等权平均，未按人口或企业数加权。",
            "横线为省内最小—最大值（极差），不是置信区间、标准差区间或分位数区间；各区域极差、标准差与变异系数见底表。",
            "区域划分为本研究固定口径，不含港澳台；底表 data/processed/stage4/fig3_regional_center_dispersion.csv。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "fig3_regional_center_comparison")





# ------------------------------------------------------------------ 图4
def fig4() -> list[Path]:
    df = read("fig4_d1_d2_scatter_panel.csv")
    keys = key_numbers()
    corr = keys["correlation"]
    gap = keys["rank_gap"]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 4 ｜ 结构关系",
        "两个维度不能相互替代：企业应用 × 接入配置",
        "2024年全年企业调查 ｜ 2024年末固定宽带账户 ｜ 31个省级行政区 ｜ 每点一省 ｜ 虚线为31省中位数（描述性参考，不是分类边界）",
        left=0.62,
        top=0.40,
        title_size=21,
    )

    band_text = (
        f"两轴相关性很弱（Pearson {corr['pearson']:.2f}、Spearman {corr['spearman']:.2f}，n=31，仅描述性），"
        f"且 {gap['n_abs_ge_10']} 个省份的两个单项名次相差 10 位及以上：北京 D1 第1、D2 第20；广东 D1 第9、D2 第31；"
        "宁夏 D1 第21、D2 第5。同一个省在两个维度上可以处于完全不同的位置，"
        "因此任何单一代理都不能代表“数字化发展水平”，也不宜把两轴相加成一个总分。"
    )
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(st.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    footer_top = c.h - 0.92
    band_top = footer_top - band_h - 0.10

    ax = c.axes(left=1.15, top=head_bottom + 0.55, width=7.85, height=band_top - 0.46 - (head_bottom + 0.55))
    st.style_axes(ax, grid_axis="both")

    x_med, y_med = df["d2_accounts_per100"].median(), df["d1_ecommerce_pct"].median()
    ax.axvline(x_med, color=st.MUTED, lw=0.9, ls=(0, (2.5, 2.5)), alpha=0.65, zorder=1)
    ax.axhline(y_med, color=st.MUTED, lw=0.9, ls=(0, (2.5, 2.5)), alpha=0.65, zorder=1)

    for region in st.REGION_ORDER:
        sub = df[df["region_4"] == region]
        ax.scatter(
            sub["d2_accounts_per100"],
            sub["d1_ecommerce_pct"],
            s=105,
            color=st.REGION_COLORS[region],
            edgecolor="white",
            linewidth=1.5,
            zorder=4,
            label=region,
        )

    labels = {
        "北京": (12, -2, "left"),
        "河北": (-2, -17, "center"),
        "广东": (12, -3, "left"),
        "宁夏": (11, 7, "left"),
        "重庆": (11, 2, "left"),
        "山东": (-12, 5, "right"),
        "海南": (-12, 2, "right"),
        "江苏": (-12, -3, "right"),
    }
    for name, (dx, dy, ha) in labels.items():
        row = df[df["short_name"] == name].iloc[0]
        ax.annotate(
            name,
            xy=(row["d2_accounts_per100"], row["d1_ecommerce_pct"]),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha,
            va="center",
            fontsize=9.2,
            color=st.INK,
            zorder=6,
        )

    ax.set_xlim(38.2, 59.8)
    ax.set_ylim(6.6, 24.9)
    ax.set_xticks([40, 45, 50, 55])
    ax.set_yticks([8, 12, 16, 20, 24])
    ax.tick_params(axis="both", labelsize=8.8, colors=st.MUTED)
    ax.set_xlabel("固定宽带接入配置（户/百人，2024年末）", fontsize=9.6, color=st.INK_SOFT, labelpad=7)
    ax.set_ylabel("企业数字交易应用（%，2024年全年）", fontsize=9.6, color=st.INK_SOFT, labelpad=8)
    ax.text(x_med + 0.25, 24.55, "31省中位数（D2）", fontsize=7.6, color=st.MUTED, ha="left", va="top")
    ax.text(59.55, y_med + 0.30, "31省中位数（D1）", fontsize=7.6, color=st.MUTED, ha="right", va="bottom")
    st.axes_region_legend(ax)

    # ---------------- 右侧名次差栏 ----------------
    rail_x = 9.55
    c.text(rail_x, head_bottom + 0.52, "名次差最大的四省", size=10.5, color=st.INK, weight="bold")
    c.text(rail_x, head_bottom + 0.82, "D1 名次 → D2 名次（1＝最高，31＝最低）", size=8.2, color=st.MUTED)

    rows = gap["top5_gaps"][:4]
    row_y = head_bottom + 1.30
    for i, item in enumerate(rows):
        name = item["short_name"]
        r1, r2 = item["d1_rank"], item["d2_rank"]
        delta = item["rank_gap_d1_minus_d2"]
        if i:
            c.rule(rail_x, rail_x + 3.05, row_y - 0.19, color=st.GRID, lw=0.7)
        c.text(rail_x, row_y, name, size=10.2, color=st.INK, weight="bold")
        c.text(rail_x + 0.95, row_y, f"{r1}", size=9.6, color=st.INK_SOFT, ha="right")
        c.text(rail_x + 1.10, row_y, "→", size=9.2, color=st.MUTED)
        c.text(rail_x + 1.32, row_y, f"{r2}", size=9.6, color=st.INK_SOFT)
        sign = "+" if delta > 0 else "−"
        note = "D2 更靠前" if delta > 0 else "D1 更靠前"
        c.text(rail_x + 1.84, row_y, f"{sign}{abs(delta)}", size=9.6, color=st.ACCENT, weight="bold")
        c.text(rail_x + 2.30, row_y + 0.02, note, size=7.6, color=st.MUTED)
        row_y += 0.44

    c.text(
        rail_x,
        row_y + 0.10,
        f"31省平均绝对名次差 {gap['mean_abs_gap']:.1f} 位；\n"
        f"{gap['n_abs_ge_10']} 个省份的名次差达到 10 位及以上。\n"
        "名次差＝D1名次−D2名次。",
        size=8.2,
        color=st.MUTED,
    )

    note_band(c, band_top, "两个代理的排序几乎不重合", band_text, left=0.62, width=band_w)
    c.footer(
        [
            "数据：2024年全年企业调查（《中国统计年鉴2025》表16-39，E02）× 2024年末固定宽带账户（同书表16-36、表2-5，I203/A01）。",
            "两轴单位不同，点的位置只在各自轴刻度上可比；虚线为31省中位数，仅作描述性参考，不构成象限分类、综合评分或优劣判断。",
            "未做回归、拟合或显著性检验；相关系数只用于说明两个代理不能互换。底表 data/processed/stage4/fig4_d1_d2_scatter_panel.csv。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "fig4_application_vs_access_scatter")


# ------------------------------------------------------------------ 图5
def fig5() -> list[Path]:
    by_region = read("fig5_government_tier_by_region.csv")
    by_prov = read("fig5_government_tier_by_province.csv")
    keys = key_numbers()
    tiers = keys["government_tiers"]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 5 ｜ 数字政府档级",
        "2024年网上政府发展档级的区域分布",
        "调查窗口 2024年9月上旬—10月上旬 ｜ 31个省级行政区 ｜ 档级：优秀 / 良好 / 中等 ｜ 只作分类展示，不转换为分数",
        left=0.62,
        top=0.40,
        title_size=21,
    )

    # 档级图例（右上）
    lx = 9.92
    for i, tier in enumerate(st.TIER_ORDER):
        cx = lx + i * 0.95
        c.fig.add_artist(
            Rectangle(
                (c.fx(cx), c.fy(head_bottom + 0.10)),
                c.fx(0.16),
                0.16 / c.h,
                facecolor=st.TIER_COLORS[tier],
                edgecolor="none",
                transform=c.fig.transFigure,
                zorder=5,
            )
        )
        c.text(cx + 0.22, head_bottom - 0.015, tier, size=9, color=st.INK_SOFT)

    band_text = (
        f"东部 10 省中 7 省为优秀（70.0%），东北 3 省无优秀、2 省为中等；"
        f"但西部 12 省中仍有 5 省为优秀（41.7%），高于中部的 1/6。"
        "档级分布不是一条从东到西的直线：区域内部同时存在高位与中位省份，"
        "因此本图只用于观察结构，不据此给省份排序或计分。"
    )
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(st.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    footer_top = c.h - 0.92
    band_top = footer_top - band_h - 0.10

    # ---------------- 上：分区域堆叠条 ----------------
    ax = c.axes(left=1.55, top=head_bottom + 0.30, width=c.w - 1.55 - 0.62, height=2.10)
    ax.set_xlim(0, 100)
    ax.set_ylim(5.7, -0.65)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0, pad=4)
    ax.set_facecolor(st.PAPER)

    order = ["东部", "中部", "西部", "东北", "全国31省"]
    labels = {"全国31省": "全国 31 省"}
    for i, region in enumerate(order):
        row = by_region[by_region["region"] == region].iloc[0]
        yi = i if region != "全国31省" else 5
        if region == "全国31省":
            ax.axhspan(yi - 0.42, yi + 0.42, color=st.PANEL, zorder=0)
        left = 0.0
        for tier, col, pct_col in [("优秀", "excellent", "excellent_pct"),
                                   ("良好", "good", "good_pct"),
                                   ("中等", "medium", "medium_pct")]:
            width = row[pct_col]
            if width <= 0:
                continue
            ax.barh([yi], [width], left=[left], height=0.62, color=st.TIER_COLORS[tier],
                    edgecolor=st.PAPER, linewidth=1.6, zorder=3)
            txt_color = st.TIER_TEXT[tier]
            ax.text(left + width / 2, yi, f"{int(row[col])}（{width:.1f}%）", ha="center", va="center",
                    fontsize=8.6, color=txt_color, zorder=5)
            left += width
        ax.text(-2.2, yi, labels.get(region, region), ha="right", va="center", fontsize=10, color=st.INK)
        if region != "全国31省":
            ax.text(-2.2, yi + 0.34, f"{int(row['n'])} 省", ha="right", va="center", fontsize=7.8, color=st.MUTED)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8.4, color=st.MUTED)
    ax.grid(axis="x", color=st.GRID, lw=0.8, zorder=0)

    # ---------------- 下：31省条带 ----------------
    strip_top = 4.62
    cell_h = 0.62
    gap = 0.13
    x0, x1 = 1.55, c.w - 0.62
    total_cells = len(by_prov)
    unit = (x1 - x0 - gap * 3) / total_cells
    cursor = x0
    for region in st.REGION_ORDER:
        block = by_prov[by_prov["region_4"] == region]
        c.text(cursor, strip_top - 0.06, region, size=8.4, color=st.MUTED, weight="bold")
        c.text(cursor + 0.46, strip_top - 0.06, f"{len(block)} 省", size=7.6, color=st.MUTED)
        for _, row in block.iterrows():
            tier = row["gov_tier_2024"]
            c.fig.add_artist(
                Rectangle(
                    (c.fx(cursor), c.fy(strip_top + 0.14 + cell_h)),
                    c.fx(unit - 0.02),
                    cell_h / c.h,
                    facecolor=st.TIER_COLORS[tier],
                    edgecolor=st.PAPER,
                    linewidth=1.2,
                    transform=c.fig.transFigure,
                    zorder=3,
                )
            )
            c.text(
                cursor + (unit - 0.02) / 2,
                strip_top + 0.14 + cell_h / 2,
                row["short_name"],
                size=7.4,
                color=st.TIER_TEXT[tier],
                ha="center",
                va="center",
                rotation=90,
                zorder=5,
            )
            cursor += unit
        cursor += gap

    note_band(c, band_top, "档级分布不是一条从东到西的直线", band_text, left=0.62, width=band_w)
    c.footer(
        [
            "数据：2024年网上政府发展档级调查（S27），调查窗口2024年9月上旬—10月上旬，31省全覆盖，档级沿用原报告分类。",
            "档级只作分类与占比展示，不转换为分数、不推定档内名次、不与其他指数拼接；区域划分为本研究固定口径，不含港澳台。",
            "底表 data/processed/stage4/fig5_government_tier_by_region.csv、fig5_government_tier_by_province.csv。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "fig5_government_tier_distribution")


# ------------------------------------------------------------------ 图6
def rank_track(c, x, y, w, rank, color, tag, filled=True):
    """31格名次轨道：横线＋刻度＋标记，左标D1/D2，右标 x/31。"""
    c.rule(x, x + w, y, color=st.GRID, lw=1.1)
    for i in range(31):
        cx = x + i * (w / 30)
        c.fig.add_artist(
            plt.Line2D(
                [c.fx(cx), c.fx(cx)],
                [c.fy(y - 0.018), c.fy(y + 0.018)],
                color=st.GRID,
                lw=0.6,
                transform=c.fig.transFigure,
                zorder=4,
            )
        )
    cx = x + (rank - 1) * (w / 30)
    c.fig.add_artist(
        plt.Line2D(
            [c.fx(cx)],
            [c.fy(y)],
            marker="o",
            markersize=6.2,
            markerfacecolor=color if filled else st.PAPER,
            markeredgecolor=color,
            markeredgewidth=1.4,
            linestyle="none",
            transform=c.fig.transFigure,
            zorder=8,
        )
    )
    c.text(x - 0.06, y + 0.005, tag, size=7.2, color=st.MUTED, ha="right", va="center")
    c.text(x + w + 0.11, y + 0.005, f"{rank}/31", size=7.2, color=st.INK_SOFT, ha="left", va="center")


def case_card(c, x, y_top, w, h, idx, d):
    accent = st.REGION_COLORS[d["region"]]
    # 卡片底与顶部色条
    c.fig.add_artist(
        Rectangle((c.fx(x), c.fy(y_top + h)), c.fx(w), h / c.h, facecolor=st.PAPER,
                  edgecolor=st.HAIRLINE, linewidth=0.9, transform=c.fig.transFigure, zorder=2)
    )
    c.fig.add_artist(
        Rectangle((c.fx(x), c.fy(y_top + 0.035)), c.fx(w), 0.035 / c.h, facecolor=accent,
                  edgecolor="none", transform=c.fig.transFigure, zorder=3)
    )
    c.text(x + w - 0.16, y_top + 0.10, f"0{idx}", size=8.5, color=st.MUTED, ha="right")
    c.text(x + 0.18, y_top + 0.08, d["name"], size=19, color=st.INK, weight="bold")
    c.text(x + 0.18, y_top + 0.38, d["subtitle"], size=8.2, color=st.MUTED)
    c.rule(x + 0.18, x + w - 0.18, y_top + 0.58)

    # 数据事实
    c.text(x + 0.18, y_top + 0.64, "数据事实（2024）", size=7.4, color=st.MUTED, weight="bold")
    col2 = x + 1.92
    for cx, value, label in [
        (x + 0.18, f"{d['d1']:.2f}", f"企业数字交易应用（%）· 第{d['d1_rank']}/31"),
        (col2, f"{d['d2']:.2f}", f"每百人宽带账户（户）· 第{d['d2_rank']}/31"),
    ]:
        c.text(cx, y_top + 0.76, value, size=17, color=st.INK, weight="bold")
        c.text(cx, y_top + 1.04, label, size=7.0, color=st.MUTED)

    rank_track(c, x + 0.44, y_top + 1.30, w - 1.00, int(d["d1_rank"]), accent, "D1")
    rank_track(c, x + 0.44, y_top + 1.52, w - 1.00, int(d["d2_rank"]), accent, "D2", filled=False)

    # 实施事实
    c.rule(x + 0.18, x + w - 0.18, y_top + 1.72)
    c.text(x + 0.18, y_top + 1.78, "实施事实", size=7.4, color=st.MUTED, weight="bold")
    yy = y_top + 1.90
    for line in d["impl"]:
        c.text(x + 0.18, yy, line, size=8.0, color=st.INK_SOFT)
        yy += 0.165
    c.text(x + 0.18, yy + 0.02, d["source"], size=7.0, color=st.MUTED)

    # 研究启示
    c.rule(x + 0.18, x + w - 0.18, y_top + 2.48)
    c.text(x + 0.18, y_top + 2.54, "研究启示", size=7.4, color=st.ACCENT, weight="bold")
    yy = y_top + 2.66
    for line in d["insight"]:
        c.text(x + 0.18, yy, line, size=8.0, color=st.ACCENT)
        yy += 0.165

    # 边界
    c.rule(x + 0.18, x + w - 0.18, y_top + 3.02)
    c.text(x + 0.18, y_top + 3.08, "不能推出", size=7.4, color=st.MUTED, weight="bold")
    yy = y_top + 3.20
    for line in d["boundary"]:
        c.text(x + 0.18, yy, line, size=7.8, color=st.MUTED)
        yy += 0.155


def fig6() -> list[Path]:
    keys = key_numbers()
    bj, hb, nx = keys["cases"]["beijing"], keys["cases"]["hebei"], keys["cases"]["ningxia"]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 6 ｜ 案例证据",
        "三个案例：数据事实、实施证据与解释边界",
        "北京—河北（东部内部差异与京津冀协作）｜ 宁夏（西部功能路径）｜ 卡片内数字与政策事实均可回溯到具体来源",
        left=0.62,
        top=0.40,
        title_size=21,
    )

    cards = [
        dict(
            name="北京",
            subtitle="东部 · 2024年网上政府档级：优秀",
            region="东部",
            d1=bj["d1"], d1_rank=bj["d1_rank"], d2=bj["d2"], d2_rank=bj["d2_rank"],
            impl=[
                "京津冀“一网通办”专区上线 417 项事项",
                "三地自贸试验区 230 项同事同标",
            ],
            source="北京市政务服务和数据管理局 2024 年工作总结（2025-03-20）",
            insight=[
                "同一区域内部，应用高位与配置中位可以并存；",
                "协作应落在事项标准互认与跨域受理。",
            ],
            boundary=[
                "事项数不等于办理量、满意度或企业受益；",
                "不能据此推断电商参与比例的变化。",
            ],
        ),
        dict(
            name="河北",
            subtitle="东部 · 2024年网上政府档级：良好",
            region="东部",
            d1=hb["d1"], d1_rank=hb["d1_rank"], d2=hb["d2"], d2_rank=hb["d2_rank"],
            impl=[
                "京津冀 1053 个事项“跨省通办”",
                "社保卡“一卡通”覆盖交通、旅游等 5 个场景",
            ],
            source="河北省 2025 年政府工作报告·2024年回顾（2025-01-24）",
            insight=[
                "较低的电商参与代理，",
                "不等于数字化功能缺失或整体落后。",
            ],
            boundary=[
                "1053 与北京 417 口径不同，不能相加；",
                "报告引用的第三方指数不并入本研究。",
            ],
        ),
        dict(
            name="宁夏",
            subtitle="西部 · 2024年网上政府档级：良好",
            region="西部",
            d1=nx["d1"], d1_rank=nx["d1_rank"], d2=nx["d2"], d2_rank=nx["d2_rank"],
            impl=[
                "中卫 7 个算力项目投运、标准机架 12.1 万架",
                "2024 年国家数据局在宁夏等枢纽部署算电协同",
            ],
            source="中卫市数据局 2024 年总结（2025-02-10）；国家发展改革委答复（2025-08-11）",
            insight=[
                "西部可走“设施—算力—能源”的功能路径，",
                "不必在所有应用指标上同序竞争。",
            ],
            boundary=[
                "中卫不等于全宁夏；机架数不等于利用率；",
                "不证明项目提高了全省两个代理值。",
            ],
        ),
    ]

    card_w, card_h, gap = 3.88, 3.60, 0.20
    for i, d in enumerate(cards):
        case_card(c, 0.62 + i * (card_w + gap), 1.82, card_w, card_h, i + 1, d)

    band_text = (
        f"北京与河北同属东部、接入配置只差 {keys['cases']['beijing_hebei_d2_gap']:.2f} 户/百人，"
        f"企业应用却相差 {keys['cases']['beijing_hebei_d1_gap_pp']:.2f} 个百分点；"
        "宁夏接入配置第 5、企业应用第 21，同时有中卫算力项目与算电协同部署。"
        "差异更多来自功能分工与路径选择，而不是简单的“先进/落后”。"
    )
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(st.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    band_top = c.h - 0.92 - band_h - 0.10
    note_band(c, band_top, "三张卡片回答同一个问题：差异不等于落后", band_text, left=0.62, width=band_w)

    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39、表16-36、表2-5（2024年全年／2024年末）；档级为2024年网上政府调查（S27）。政策事实为各地各部门公开文件。",
            "三张卡片是解释窗口，不是综合评比的“领先省/落后省”样本；实施事实与统计关联分开陈述，项目存在不等于指标提升，不作因果推断。",
            "原文定位、发布日期与文件快照见 reports/stage3_case_evidence.md 与 data/processed/stage3/source_index.csv；卡片底表 data/processed/stage4/fig6_case_card_table.csv。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "fig6_case_evidence_cards")


# ------------------------------------------------------------------ 图6b（备用）
def fig6b() -> list[Path]:
    keys = key_numbers()
    gd = keys["cases"]["guangdong"]
    q = keys["cases"]["guangdong_quality"]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head_bottom = c.header(
        "图 6B ｜ 备用案例 · 指标边界",
        "广东：一个账户密度，不能代表基础设施强弱",
        "2024年末 ｜ 单省同段数据 ｜ 用于回答“为什么不能只用每百人账户数判断数字基础设施”",
        left=0.62,
        top=0.40,
        title_size=21,
    )

    d = dict(
        name="广东",
        subtitle="东部 · 2024年网上政府档级：优秀",
        region="东部",
        d1=gd["d1"], d1_rank=gd["d1_rank"], d2=gd["d2"], d2_rank=gd["d2_rank"],
        impl=[
            f"固定宽带 {q['fixed_broadband_wan']:.1f} 万户；千兆以上 {q['gigabit_wan']:.1f} 万户",
            f"同段相除：千兆以上占比 {q['gigabit_share_pct']:.2f}%",
        ],
        source="广东省通信管理局 2024年12月运行情况（2025-01-26）",
        insight=[
            "账户密度与接入质量结构是两个不同的测量；",
            "单项位置低，不能推出设施总体薄弱。",
        ],
        boundary=[
            "只有一个省的千兆结构，不能外推31省；",
            "不能用基站绝对量证明人均或覆盖优势。",
        ],
    )
    case_card(c, 0.62, 1.82, 4.55, 3.60, 4, d)

    # 右侧解释
    rx = 5.52
    c.text(rx, 1.86, "为什么不能这样读", size=11.5, color=st.INK, weight="bold")
    items = [
        (
            "指标定义",
            "每百人固定宽带账户数＝全部固定宽带账户÷常住人口。分子含家庭与机构账户，"
            "不是去重居民人数，也不是网络速率或覆盖质量。",
        ),
        (
            "可能机制（未检验）",
            "家庭户规模、机构账户构成、固定与移动接入替代、人口流动都会改变这个比值。"
            "本研究没有同年31省的家庭/机构账户拆分，不能替广东确定原因。",
        ),
        (
            "质量需要另一个测量",
            "同年末广东千兆以上用户占固定宽带 29.78%，说明“接入配置”与“质量结构”不是同一件事；"
            "但本项目没有31省同口径质量表，因此不能给广东排质量名次。",
        ),
    ]
    y = 2.26
    for i, (lead, body) in enumerate(items):
        c.text(rx, y, f"0{i+1}", size=9.5, color=st.ACCENT, weight="bold")
        c.text(rx + 0.42, y, lead, size=9.4, color=st.INK, weight="bold")
        lines = st.wrap_display(body, (7.05 - 0.42) * 72 / 8.3 * 0.97)
        yy = y + 0.24
        for line in lines:
            c.text(rx + 0.42, yy, line, size=8.3, color=st.INK_SOFT)
            yy += 0.165
        y = yy + 0.20

    band_text = (
        "这不是为广东“辩护”，而是说明代理指标的适用范围：账户密度测的是配置，不是速率、覆盖、资费或体验。"
        "在没有31省同口径质量数据时，本研究的正确做法是把指标改名、写清边界，而不是用单项位置给省份下总体判断。"
    )
    band_w = c.w - 1.24
    band_h = 0.26 + 0.27 + 0.195 * len(st.wrap_display(band_text, (band_w - 0.42) * 72 / 8.5 * 0.96))
    band_top = c.h - 0.92 - band_h - 0.10
    note_band(c, band_top, "方法意义：先校准指标，再讨论强弱", band_text, left=0.62, width=band_w)

    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-36、表2-5（2024年末）；千兆结构为广东省通信管理局2024年12月运行情况同段原值相除（C303）。",
            "本卡为方法警示用备用案例，不进入主叙事；单省质量数据不外推为31省结论，也不改变任何省份的D1/D2数值。",
            "底表 data/processed/stage3/guangdong_quality_context.csv、data/processed/stage4/fig6_case_card_table.csv。",
        ],
        left=0.62,
        bottom=0.24,
        width=c.w - 1.24,
    )
    return st.save(c.fig, "fig6b_guangdong_method_warning")


FIGURES = {
    "fig1": fig1,
    "fig2": fig2,
    "fig3": fig3,
    "fig4": fig4,
    "fig5": fig5,
    "fig6": fig6,
    "fig6b": fig6b,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("names", nargs="*", default=None)
    args = parser.parse_args()
    names = args.names or list(FIGURES)
    for name in names:
        paths = FIGURES[name]()
        print(name, "->", ", ".join(str(p.relative_to(ROOT)) for p in paths))


if __name__ == "__main__":
    main()
