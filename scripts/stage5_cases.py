"""第五阶段案例卡：北京—河北对照、宁夏、广东（备用）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

import stage4_style as base  # noqa: E402
import stage5_style as st  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def card_panel(c, x, y, w, h, accent):
    c.fig.add_artist(
        Rectangle((c.fx(x), c.fy(y + h)), c.fx(w), h / c.h, facecolor=st.PAPER,
                  edgecolor=st.HAIRLINE, linewidth=0.9, transform=c.fig.transFigure, zorder=2)
    )
    c.fig.add_artist(
        Rectangle((c.fx(x), c.fy(y + 0.045)), c.fx(w), 0.045 / c.h, facecolor=accent,
                  edgecolor="none", transform=c.fig.transFigure, zorder=3)
    )


def stat_block(c, x, y, value, unit, label, rank):
    c.text(x, y, value, size=27, color=st.INK, weight="bold")
    c.text(x, y + 0.34, unit, size=8.6, color=st.MUTED)
    c.text(x, y + 0.52, label, size=8.6, color=st.INK_SOFT)
    c.text(x, y + 0.70, rank, size=8.6, color=st.ACCENT, weight="bold")


def section(c, x, y, w, title, lines, color=st.INK_SOFT, size=8.6, title_color=st.MUTED):
    c.text(x, y, title, size=7.6, color=title_color, weight="bold")
    yy = y + 0.19
    for line in lines:
        c.text(x, yy, line, size=size, color=color)
        yy += 0.185
    c.rule(x, x + w, y - 0.08, color=st.GRID, lw=0.7)
    return yy


def case_two() -> list[Path]:
    keys = __import__("json").loads((ROOT / "data/processed/stage5/stage5_key_numbers.json").read_text(encoding="utf-8"))
    bj, hb = keys["cases"]["beijing"], keys["cases"]["hebei"]
    gap1 = keys["cases"]["beijing_hebei_d1_gap_pp"]
    gap2 = keys["cases"]["beijing_hebei_d2_gap"]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header(
        "图 F1 ｜ 案例对照",
        "北京—河北：同为东部，差在应用不在配置",
        "2024年全年企业调查 × 2024年末固定宽带账户 ｜ 两省对照 ｜ 数据、实施证据与解释边界分栏呈现",
        left=0.55,
        top=0.36,
        title_size=20,
    )

    top = head + 0.18
    h = 4.92
    card_panel(c, 0.55, top, 4.55, h, st.REGION_COLORS["东部"])
    card_panel(c, 8.25, top, 4.53, h, st.REGION_COLORS["东部"])

    for x, name, d in [(0.55, "北京", bj), (8.25, "河北", hb)]:
        c.text(x + 0.28, top + 0.16, name, size=26, color=st.INK, weight="bold")
        c.text(x + 0.28, top + 0.62, f"{d['region']} · 2024年网上政府档级：{d['tier']}", size=8.8,
               color=st.MUTED)
        c.rule(x + 0.28, x + 4.27, top + 0.82, color=st.GRID, lw=0.7)
        stat_block(c, x + 0.28, top + 1.00, f"{d['d1']:.2f}", "%", "企业数字交易应用", f"第 {d['d1_rank']} / 31")
        stat_block(c, x + 2.45, top + 0.95, f"{d['d2']:.2f}", "户/百人", "固定宽带接入配置", f"第 {d['d2_rank']} / 31")
        c.rule(x + 0.28, x + 4.27, top + 1.90, color=st.GRID, lw=0.7)

    evid_bj = ["京津冀“一网通办”专区上线 417 项事项", "三地自贸试验区 230 项同事同标"]
    evid_hb = ["京津冀 1053 个事项“跨省通办”", "社保卡“一卡通”覆盖 5 个场景"]
    src_bj = "北京市政务服务和数据管理局 2024 年工作总结（2025-03-20）"
    src_hb = "河北省 2025 年政府工作报告·2024 年回顾（2025-01-24）"

    y0 = top + 2.05
    for x, evid, src in [(0.55, evid_bj, src_bj), (8.25, evid_hb, src_hb)]:
        c.text(x + 0.28, y0, "实施证据", size=7.6, color=st.MUTED, weight="bold")
        yy = y0 + 0.20
        for line in evid:
            c.text(x + 0.28, yy, line, size=8.8, color=st.INK_SOFT)
            yy += 0.20
        c.text(x + 0.28, yy + 0.02, src, size=6.9, color=st.MUTED)
        c.rule(x + 0.28, x + 4.27, yy + 0.20, color=st.GRID, lw=0.7)

    y1 = top + 3.10
    ins_bj = ["同一区域内部，应用高位与配置中位可以并存；", "协作应落在事项标准互认与跨域受理。"]
    ins_hb = ["较低的电商参与代理，", "不等于数字化功能缺失或整体落后。"]
    c.text(0.55 + 0.28, y1, "研究含义", size=7.6, color=st.ACCENT, weight="bold")
    for i, line in enumerate(ins_bj):
        c.text(0.55 + 0.28, y1 + 0.20 + i * 0.19, line, size=8.8, color=st.ACCENT)
    c.text(8.25 + 0.28, y1, "研究含义", size=7.6, color=st.ACCENT, weight="bold")
    for i, line in enumerate(ins_hb):
        c.text(8.25 + 0.28, y1 + 0.20 + i * 0.19, line, size=8.8, color=st.ACCENT)
    c.rule(0.83, 4.82, y1 + 0.66, color=st.GRID, lw=0.7)
    c.rule(8.53, 12.50, y1 + 0.66, color=st.GRID, lw=0.7)

    y2 = top + 3.96
    c.text(0.55 + 0.28, y2, "不能推出", size=7.6, color=st.MUTED, weight="bold")
    c.text(0.55 + 0.28, y2 + 0.20, "事项数不等于办理量、满意度或企业受益；", size=8.2, color=st.MUTED)
    c.text(0.55 + 0.28, y2 + 0.38, "不能据此推断电商参与比例的变化。", size=8.2, color=st.MUTED)
    c.text(8.25 + 0.28, y2, "不能推出", size=7.6, color=st.MUTED, weight="bold")
    c.text(8.25 + 0.28, y2 + 0.20, "1053 与 417 口径不同，不能相加；", size=8.2, color=st.MUTED)
    c.text(8.25 + 0.28, y2 + 0.38, "报告引用的第三方指数不并入本研究。", size=8.2, color=st.MUTED)

    # 中间差距带
    mx, mw = 5.28, 2.78
    c.fig.add_artist(
        FancyBboxPatch((c.fx(mx), c.fy(top + h)), c.fx(mw), h / c.h,
                       boxstyle="round,pad=0,rounding_size=0.02", transform=c.fig.transFigure,
                       facecolor=st.PANEL, edgecolor="none", zorder=3)
    )
    c.text(mx + 0.20, top + 0.22, "两省差距", size=8.4, color=st.MUTED, weight="bold")
    c.text(mx + 0.20, top + 0.62, f"{gap1:.2f}", size=34, color=st.ACCENT, weight="bold")
    c.text(mx + 0.22, top + 1.22, "个百分点（D1）", size=8.2, color=st.ACCENT)
    c.rule(mx + 0.20, mx + mw - 0.20, top + 1.48, color=st.HAIRLINE, lw=0.8)
    c.text(mx + 0.20, top + 1.62, f"{gap2:.2f}", size=34, color=st.INK_SOFT, weight="bold")
    c.text(mx + 0.22, top + 2.22, "户/百人（D2）", size=8.2, color=st.MUTED)
    c.text(mx + 0.20, top + 2.68, "配置几乎相同，\n应用相差近 15 个百分点。", size=8.6, color=st.INK_SOFT)
    c.text(mx + 0.20, top + 3.30, "→ 区域内部差异\n不能由大区均值代表", size=8.6, color=st.ACCENT, weight="bold")
    c.text(mx + 0.20, top + 3.94, "注：D1 差＝北京−河北；\nD2 差为绝对值。", size=6.9, color=st.MUTED)

    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39（2024年全年）、表16-36与表2-5（2024年末）；档级为2024年网上政府调查（S27）。",
            "政策事实为主管部门公开文件，属“实施事实”，不等于效果评估；两卡对照不构成因果推断。底表 data/processed/stage5/fig6_case_card_table.csv。",
        ],
        left=0.55,
        bottom=0.22,
        width=c.w - 1.10,
    )
    return st.save(c.fig, "case_card_beijing_hebei")


def case_single(name: str) -> list[Path]:
    import json

    keys = json.loads((ROOT / "data/processed/stage5/stage5_key_numbers.json").read_text(encoding="utf-8"))
    spec = {
        "ningxia": dict(
            kicker="图 F2 ｜ 案例",
            title="宁夏：西部的另一种路径",
            subtitle="2024年末接入配置第 5、企业应用第 21 ｜ 算力布局与算电协同 ｜ 数据、证据与边界分栏",
            region="西部", d=keys["cases"]["ningxia"],
            evid=["中卫 7 个算力项目建成投运，标准机架累计 12.1 万架",
                  "2024 年国家数据局在宁夏等枢纽部署算电协同先行先试"],
            src="中卫市数据局 2024 年总结（2025-02-10）；国家发展改革委答复（2025-08-11）",
            insight=["西部可以走“设施—算力—能源”的功能路径，", "不必在所有应用指标上同序竞争。"],
            boundary=["中卫不等于全宁夏；机架数不等于利用率；", "不证明项目提高了全省两个代理值。"],
            file="case_card_ningxia",
        ),
        "guangdong": dict(
            kicker="图 F3 ｜ 备用案例 · 指标边界",
            title="广东：一个账户密度，不能代表设施强弱",
            subtitle="2024年末接入配置第 31、企业应用第 9 ｜ 千兆占比 29.78%（单省同段） ｜ 方法警示用",
            region="东部", d=keys["cases"]["guangdong"],
            evid=["固定宽带 5049.5 万户，其中千兆以上 1503.5 万户",
                  "同段相除：千兆以上占比 29.78%（2024 年 12 月）"],
            src="广东省通信管理局 2024 年 12 月运行情况（2025-01-26）",
            insight=["账户密度与接入质量结构是两个不同的测量；", "单项位置低，不能推出设施总体薄弱。"],
            boundary=["只有一个省的千兆结构，不能外推 31 省；", "不能用基站绝对量证明人均或覆盖优势。"],
            file="case_card_guangdong",
        ),
    }[name]

    st.use_style()
    c = st.Canvas(13.333, 7.5)
    head = c.header(spec["kicker"], spec["title"], spec["subtitle"], left=0.55, top=0.36, title_size=20)

    top = head + 0.18
    h = 4.92
    card_panel(c, 0.55, top, 12.23, h, st.REGION_COLORS[spec["region"]])

    # 左：省名与两项数据
    d = spec["d"]
    c.text(0.85, top + 0.26, spec["title"].split("：")[0], size=28, color=st.INK, weight="bold")
    c.text(0.85, top + 0.76, f"{d['region']} · 2024年网上政府档级：{d['tier']}", size=9.4, color=st.MUTED)
    c.rule(0.85, 4.55, top + 1.00, color=st.GRID, lw=0.7)
    stat_block(c, 0.85, top + 1.18, f"{d['d1']:.2f}", "%", "企业数字交易应用", f"第 {d['d1_rank']} / 31")
    stat_block(c, 0.85, top + 2.50, f"{d['d2']:.2f}", "户/百人", "固定宽带接入配置", f"第 {d['d2_rank']} / 31")
    c.rule(0.85, 4.55, top + 3.62, color=st.GRID, lw=0.7)
    c.text(0.85, top + 3.78, "读法", size=7.6, color=st.MUTED, weight="bold")
    read = {
        "ningxia": ["配置靠前、应用居中，", "不代表整体更强或更弱。"],
        "guangdong": ["应用居中偏上、配置最后，", "两项测的不是同一件事。"],
    }[name]
    for i, line in enumerate(read):
        c.text(0.85, top + 4.02 + i * 0.24, line, size=9.0, color=st.INK_SOFT)

    # 右：证据 / 含义 / 边界
    x = 5.05
    w = 7.45
    c.text(x, top + 0.30, "实施证据", size=7.6, color=st.MUTED, weight="bold")
    yy = top + 0.56
    for line in spec["evid"]:
        c.text(x, yy, line, size=10.0, color=st.INK_SOFT)
        yy += 0.28
    c.text(x, yy + 0.06, spec["src"], size=7.6, color=st.MUTED)
    c.rule(x, x + w, yy + 0.30, color=st.GRID, lw=0.7)

    y1 = top + 1.85
    c.text(x, y1, "研究含义", size=7.6, color=st.ACCENT, weight="bold")
    for i, line in enumerate(spec["insight"]):
        c.text(x, y1 + 0.28 + i * 0.28, line, size=10.6, color=st.ACCENT)
    c.rule(x, x + w, y1 + 0.96, color=st.GRID, lw=0.7)

    y2 = top + 2.95
    c.text(x, y2, "不能推出", size=7.6, color=st.MUTED, weight="bold")
    for i, line in enumerate(spec["boundary"]):
        c.text(x, y2 + 0.28 + i * 0.28, line, size=9.8, color=st.MUTED)

    y3 = top + 3.95
    c.text(x, y3, "口径", size=7.6, color=st.MUTED, weight="bold")
    c.text(x, y3 + 0.24, "D1＝有电商交易企业数÷同表调查企业数；D2＝固定宽带账户÷常住人口×100；", size=8.0,
           color=st.MUTED)
    c.text(x, y3 + 0.44, "档级为2024年网上政府调查（9月上旬—10月上旬），不转分数。", size=8.0, color=st.MUTED)

    c.footer(
        [
            "数据：国家统计局《中国统计年鉴2025》表16-39（2024年全年）、表16-36与表2-5（2024年末）；档级为2024年网上政府调查（S27）。",
            "政策事实为主管部门公开文件，属“实施事实”，不等于效果评估；单省材料不外推为全国结论。底表 data/processed/stage5/fig6_case_card_table.csv。",
        ],
        left=0.55,
        bottom=0.22,
        width=c.w - 1.10,
    )
    return st.save(c.fig, spec["file"])


def case_ningxia() -> list[Path]:
    return case_single("ningxia")


def case_guangdong() -> list[Path]:
    return case_single("guangdong")


if __name__ == "__main__":
    for fn in (case_two, case_ningxia, case_guangdong):
        print(fn.__name__, "->", [str(p.relative_to(ROOT)) for p in fn()])
