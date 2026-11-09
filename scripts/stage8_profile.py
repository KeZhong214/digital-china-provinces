"""第八阶段：画像图精修版（高亮集合与对照标记按审核意见调整）。"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import pandas as pd  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage5_style as st  # noqa: E402
import stage7_figures as s7  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/stage7"
FIG = ROOT / "reports/figures_stage8"
FIG.mkdir(parents=True, exist_ok=True)

KEY = {"浙江", "北京", "广东", "宁夏", "重庆"}
PAIR = {"浙江": "A", "北京": "A", "广东": "B", "宁夏": "B"}


def main() -> None:
    df = pd.read_csv(DATA / "profile_31provinces.csv", encoding="utf-8-sig").sort_values("rank")
    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header("主图 3 ｜ 综合画像（精修版）",
                    "31省数字化发展：三个维度，一张综合画像",
                    "D1 企业数字交易应用 × D2 固定宽带接入配置 × D3 数字政府发展指数 ｜ 标准化分0—100 ｜ 本研究探索性综合评价",
                    left=0.50, top=0.30, title_size=19)

    for (lo, hi), left in zip([(1, 16), (17, 31)], [0.55, 5.92]):
        sub = df[(df["rank"] >= lo) & (df["rank"] <= hi)]
        for label, x in [("名次", left + 0.02), ("省份", left + 0.40), ("D1", left + 1.22),
                         ("D2", left + 1.68), ("D3", left + 2.14)]:
            c.text(x, 1.40, label, size=7.8, color=st.MUTED, weight="bold")
        c.text(left + 4.42, 1.40, "综合得分", size=7.8, color=st.MUTED, weight="bold", ha="right")
        c.rule(left + 0.02, left + 4.48, 1.54, color=st.HAIRLINE, lw=0.9)
        y = 1.60
        for _, r in sub.iterrows():
            is_key = r["short_name"] in KEY
            c.text(left + 0.02, y + 0.06, f"{int(r['rank'])}", size=9.0, color=st.MUTED)
            c.fig.add_artist(Rectangle((c.fx(left + 0.30), c.fy(y + 0.24)), c.fx(0.055),
                                       0.19 / c.h, facecolor=st.REGION_COLORS[r["region_4"]],
                                       edgecolor="none", transform=c.fig.transFigure, zorder=4))
            c.text(left + 0.40, y + 0.06, r["short_name"], size=9.0,
                   color=st.ACCENT if is_key else st.INK, weight="bold" if is_key else "normal")
            if r["short_name"] in PAIR:
                c.text(left + 0.98, y + 0.07, PAIR[r["short_name"]], size=6.6, color=st.ACCENT)
            for i, d in enumerate(["D1", "D2", "D3"]):
                c.fig.add_artist(Rectangle((c.fx(left + 1.18 + i * 0.46), c.fy(y + 0.26)),
                                           c.fx(0.42), 0.20 / c.h,
                                           facecolor=s7.heat_color(float(r[f"{d}_minmax"])),
                                           edgecolor="white", linewidth=1.0,
                                           transform=c.fig.transFigure, zorder=3))
            bw = 1.55 * float(r["composite"]) / 100.0
            c.fig.add_artist(Rectangle((c.fx(left + 2.64), c.fy(y + 0.22)), c.fx(max(bw, 0.004)),
                                       0.16 / c.h, facecolor="#4F7A82", edgecolor="none",
                                       transform=c.fig.transFigure, zorder=3))
            c.text(left + 4.42, y + 0.06, f"{r['composite']:.1f}", size=8.6, color=st.INK, ha="right")
            y += 0.292

    # 右栏
    rx = 10.95
    c.text(rx, 1.62, "热力色阶", size=8.2, color=st.MUTED, weight="bold")
    c.text(rx, 1.80, "每维在31省内 Min–Max 到 0—100", size=7.2, color=st.MUTED)
    for i in range(5):
        v = i * 25
        c.fig.add_artist(Rectangle((c.fx(rx), c.fy(2.10 + i * 0.23)), c.fx(0.26), 0.21 / c.h,
                                   facecolor=s7.heat_color(v), edgecolor="white", linewidth=0.8,
                                   transform=c.fig.transFigure, zorder=4))
        c.text(rx + 0.34, 2.14 + i * 0.23, str(v), size=7.2, color=st.MUTED)
    c.text(rx, 3.42, "深色＝在该指标中相对更高", size=7.2, color=st.MUTED)
    c.text(rx, 3.78, "综合得分", size=8.2, color=st.MUTED, weight="bold")
    c.fig.add_artist(Rectangle((c.fx(rx), c.fy(4.16)), c.fx(0.62), 0.09 / c.h, facecolor="#4F7A82",
                               edgecolor="none", transform=c.fig.transFigure, zorder=4))
    c.text(rx, 4.32, "三维等权平均（0—100）", size=7.2, color=st.MUTED)
    c.text(rx, 4.72, "对照标记", size=8.2, color=st.MUTED, weight="bold")
    c.text(rx, 4.92, "A：浙江—北京\nB：广东—宁夏", size=7.6, color=st.ACCENT, linespacing=1.5)
    c.text(rx, 5.62, "区域色条", size=8.2, color=st.MUTED, weight="bold")
    for i, reg in enumerate(st.REGION_ORDER):
        c.fig.add_artist(Rectangle((c.fx(rx), c.fy(5.86 + i * 0.21)), c.fx(0.055), 0.12 / c.h,
                                   facecolor=st.REGION_COLORS[reg], edgecolor="none",
                                   transform=c.fig.transFigure, zorder=4))
        c.text(rx + 0.12, 5.80 + i * 0.21, reg, size=7.4, color=st.INK_SOFT)

    c.footer(
        [
            "D1＝企业有电子商务交易活动占比（2024全年）；D2＝每百人固定宽带账户数（2024年末）；D3＝清华团队数字政府发展指数（载《数字生态指数2025》，评价窗口未明确）。",
            "热力与色阶为各维在31省内的 Min–Max 相对分（0—100），不是原始业务量，也不代表“强/弱”；综合分＝三维等权平均，同分同名次。",
            "本图为研究探索性评价，不是国家数据局官方排名；两组对照见 structure_contrast_pairs；稳妥性见 rank_sensitivity_by_type。",
        ],
        left=0.55, bottom=0.14, width=c.w - 1.10,
    )
    png = FIG / "profile_31provinces_refined.png"
    pdf = FIG / "profile_31provinces_refined.pdf"
    c.fig.savefig(png, dpi=300, facecolor=st.PAPER)
    c.fig.savefig(pdf, facecolor=st.PAPER)
    print("->", png, pdf)


if __name__ == "__main__":
    main()
