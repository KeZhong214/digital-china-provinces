"""附录图：区域—省份层级旭日图（只展示结构，不承担精确比较）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from matplotlib.patches import Wedge  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))

import stage5_style as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed/stage5"


def main() -> None:
    df = __import__("pandas").read_csv(DATA / "sunburst_hierarchy.csv", encoding="utf-8-sig")
    keys = json.loads((DATA / "stage5_key_numbers.json").read_text(encoding="utf-8"))
    breaks = [c for c in keys["map_classes"][0]["classes"] if c["break_value"] != ""]
    break_vals = [float(c["break_value"]) for c in breaks]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header(
        "图 G ｜ 附录 · 层级结构",
        "区域—省份层级：31省如何分布在四大区域",
        "内环＝四大区域（角度按省份数）；外环＝31省（每省等角）；颜色＝D1 五分位 ｜ 角度不表示数值，仅展示结构",
        left=0.55,
        top=0.38,
        title_size=20,
    )

    R0, R1 = 0.40, 0.66   # 内环
    R2, R3 = 0.68, 1.02   # 外环
    cx, cy = 0.0, 0.0

    ax = c.fig.add_axes([0.02, 0.13, 0.44, 0.70])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-1.16, 1.16)
    ax.set_ylim(-1.16, 1.16)

    total = len(df)
    angle = 90.0
    for region in st.REGION_ORDER:
        sub = df[df["region_4"] == region]
        span = 360.0 * len(sub) / total
        a0, a1 = angle - span, angle
        ax.add_patch(Wedge((cx, cy), R1, a0, a1, width=R1 - R0,
                           facecolor=st.REGION_COLORS[region], edgecolor="white", linewidth=1.2))
        mid = np.deg2rad((a0 + a1) / 2)
        ang = (a0 + a1) / 2
        if -90 <= ang <= 90:
            rot = ang
        else:
            rot = ang + 180
        ax.text(0.53 * np.cos(mid), 0.53 * np.sin(mid), f"{region}\n{len(sub)}省",
                ha="center", va="center", fontsize=8.0, color="white", fontweight="bold",
                rotation=rot, rotation_mode="anchor")
        n = len(sub)
        for i, (_, row) in enumerate(sub.iterrows()):
            b0 = a0 + (a1 - a0) * i / n
            b1 = a0 + (a1 - a0) * (i + 1) / n
            cls = sum(row["d1"] >= b for b in break_vals)
            ax.add_patch(Wedge((cx, cy), R3, b0, b1, width=R3 - R2,
                               facecolor=st.MAP_RAMP[cls], edgecolor="white", linewidth=0.9))
            mb = np.deg2rad((b0 + b1) / 2)
            ang = (b0 + b1) / 2
            if -90 <= ang <= 90:
                rot, ha = ang, "left"
            else:
                rot, ha = ang + 180, "right"
            ax.text(1.035 * np.cos(mb), 1.035 * np.sin(mb), row["short_name"],
                    ha=ha, va="center", fontsize=6.4, color=st.INK, rotation=rot,
                    rotation_mode="anchor")
        angle = a0

    ax.text(0, 0.06, "31 省", ha="center", va="center", fontsize=13, color=st.INK, weight="bold")
    ax.text(0, -0.10, "D1 五分位", ha="center", va="center", fontsize=7.2, color=st.MUTED)

    # 右侧：说明 + 色阶
    rx = 7.05
    c.text(rx, head + 0.16, "怎么看这张图", size=10.0, color=st.INK, weight="bold")
    notes = [
        ("内环", "四个区域，弧长按省份数量分配（东部10、中部6、西部12、东北3）。"),
        ("外环", "每个省占相等弧长，位置按区域与省名排序，不代表数值高低。"),
        ("颜色", "与地图一致的五分位色阶：越深表示 D1 越高。"),
        ("限制", "角度不编码数值，因此不能用面积比较省份；精确比较请用图A与图C。"),
    ]
    y = head + 0.50
    for tag, text in notes:
        c.text(rx, y, tag, size=8.4, color=st.ACCENT, weight="bold")
        lines = __import__("stage4_style").wrap_display(text, (13.333 - rx - 0.55) * 72 / 8.4 * 0.96)
        for i, line in enumerate(lines):
            c.text(rx + 0.62, y + i * 0.20, line, size=8.4, color=st.INK_SOFT)
        y += 0.22 + 0.20 * len(lines) + 0.18

    c.text(rx, y + 0.10, "D1 分级（与地图同）", size=8.4, color=st.MUTED, weight="bold")
    y += 0.34
    for i in range(4, -1, -1):
        c.fig.add_artist(
            __import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle(
                (c.fx(rx), c.fy(y + 0.14)), c.fx(0.22), 0.14 / c.h,
                facecolor=st.MAP_RAMP[i], edgecolor=st.HAIRLINE, linewidth=0.6,
                transform=c.fig.transFigure, zorder=5)
        )
        c.text(rx + 0.30, y + 0.01, st.class_label(i, break_vals, "{:.1f}"), size=7.4, color=st.INK_SOFT)
        y += 0.21

    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39（E02），2024年全年；区域与省份口径同正文。",
            "本图为层级结构展示，角度只表示省份数量与排序，不表示任何数值；不替代地图与排序图，也不用于精确比较。",
            "底表 data/processed/stage5/sunburst_hierarchy.csv、map_classes_d1.csv。",
        ],
        left=0.55,
        bottom=0.22,
        width=c.w - 1.10,
    )
    paths = st.save(c.fig, "sunburst_region_province_structure")
    print("->", [str(p.relative_to(ROOT)) for p in paths])


if __name__ == "__main__":
    main()
