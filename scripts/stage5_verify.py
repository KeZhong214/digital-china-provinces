"""第五阶段核对：底表一致性、地图分级、图表与文档齐备性。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S5 = ROOT / "data/processed/stage5"
S3 = ROOT / "data/processed/stage3"
FIG = ROOT / "reports/figures_stage5"
REPORTS = ROOT / "reports"

checks: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    checks.append((bool(ok), name, detail))


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, encoding="utf-8-sig")


def main() -> int:
    src = read(S3 / "indicator_review_panel_2024.csv")
    keys = json.loads((S5 / "stage5_key_numbers.json").read_text(encoding="utf-8"))

    # ---------- 地图面板与分级 ----------
    for metric in ["d1", "d2"]:
        panel = read(S5 / f"map_panel_{metric}.csv")
        cls = read(S5 / f"map_classes_{metric}.csv")
        check(len(panel) == 31 and panel["short_name"].nunique() == 31, f"{metric} 地图面板31省")
        m = panel.merge(src[["short_name", "ecommerce", "accounts"]], on="short_name", how="left")
        col = "ecommerce" if metric == "d1" else "accounts"
        check(np.allclose(m["value"], m[col], atol=1e-6), f"{metric} 地图值与审核面板一致")

        breaks = [float(b) for b in cls["break_value"].tolist() if str(b) not in ("", "nan")]
        check(len(breaks) == 4 and breaks == sorted(breaks), f"{metric} 分级断点4个且升序", str(breaks))

        def klass(v):
            return sum(v >= b for b in breaks)

        computed = panel["value"].apply(klass).tolist()
        check(computed == panel["class_id"].tolist(), f"{metric} 分级可复算")
        counts = panel["class_id"].value_counts().sort_index().tolist()
        check(sum(counts) == 31 and max(counts) - min(counts) <= 1, f"{metric} 五级分布均衡", str(counts))
        check(int(cls["n"].sum()) == 31, f"{metric} 分级表合计31")

    # ---------- 区域统计 ----------
    reg = read(S5 / "regional_mean_median.csv")
    check(len(reg) == 8, "区域统计8行")
    for metric in ["d1", "d2"]:
        for region in ["东部", "中部", "西部", "东北"]:
            s = src.loc[src["region_4"] == region, "ecommerce" if metric == "d1" else "accounts"]
            row = reg[(reg.metric == metric) & (reg.region == region)].iloc[0]
            ok = (abs(row["mean"] - s.mean()) < 1e-3 and abs(row["median"] - s.median()) < 1e-3
                  and int(row["n"]) == len(s))
            check(ok, f"{metric}-{region} 均值/中位数/n 一致")
    d1_mean = reg[reg.metric == "d1"].sort_values("mean", ascending=False)["region"].tolist()
    d1_med = reg[reg.metric == "d1"].sort_values("median", ascending=False)["region"].tolist()
    check(d1_mean != d1_med, "D1 均值与中位数排序不同", f"{d1_mean} vs {d1_med}")

    # ---------- 散点象限 ----------
    sc = read(S5 / "scatter_quadrant_panel.csv")
    qc = read(S5 / "scatter_quadrant_counts.csv")
    check(len(sc) == 31, "散点面板31省")
    check(int(qc["n"].sum()) == 31, "象限计数合计31")
    xm, ym = keys["quadrant"]["x_mean"], keys["quadrant"]["y_mean"]
    recomputed = (
        np.where(sc["accounts_per100"] >= xm, "配置高于均值", "配置低于均值") + "·"
        + np.where(sc["ecommerce_pct"] >= ym, "应用高于均值", "应用低于均值")
    )
    check((recomputed == sc["quadrant"]).all(), "象限归属可复算")

    # ---------- 档级 ----------
    gc = read(S5 / "gov_category_counts.csv")
    nat = gc[gc["region"] == "全国31省"].iloc[0]
    check((nat["excellent"], nat["good"], nat["medium"]) == (13, 14, 4), "档级 13/14/4")

    # ---------- 旭日层级 ----------
    sun = read(S5 / "sunburst_hierarchy.csv")
    check(len(sun) == 31, "旭日层级31省")

    # ---------- 关键数字 ----------
    check(abs(keys["descriptive"]["d1"]["mean"] - 12.0124) < 1e-3, "D1 均值12.01")
    check(abs(keys["descriptive"]["d2"]["median"] - 48.7428) < 1e-3, "D2 中位数48.74")
    check(abs(keys["cases"]["beijing_hebei_d1_gap_pp"] - 14.754) < 1e-2, "京冀差14.75")
    check(abs(keys["fragility"]["west_mean_d1_without_chongqing"] - 11.3227) < 1e-3, "删重庆后11.32")

    # ---------- 图表 ----------
    figs = {
        "map_ecommerce_2024": (3180, 2520),
        "map_ecommerce_2024_combo": (3999, 2250),
        "map_accounts_2024": (3180, 2520),
        "map_accounts_2024_combo": (3999, 2250),
        "regional_mean_median_comparison": (3999, 2250),
        "scatter_ecommerce_accounts_quadrant": (3999, 2250),
        "gov_category_distribution": (3999, 2250),
        "case_card_beijing_hebei": (3999, 2250),
        "case_card_ningxia": (3999, 2250),
        "case_card_guangdong": (3999, 2250),
        "sunburst_region_province_structure": (3999, 2250),
    }
    for name, (w, h) in figs.items():
        png, pdf = FIG / f"{name}.png", FIG / f"{name}.pdf"
        ok = png.exists() and pdf.exists()
        dim = Image.open(png).size if ok else (0, 0)
        check(ok and abs(dim[0] - w) <= 1 and abs(dim[1] - h) <= 1 and png.stat().st_size > 80_000,
              f"图 {name}", str(dim))

    # ---------- 文档 ----------
    docs = [
        "stage5_summary.md",
        "stage5_research_draft_revised.md",
        "stage5_key_findings_revised.md",
        "stage5_presentation_outline_revised.md",
        "stage5_storyline_map_revised.md",
        "figure_style_guide_revised.md",
        "figure_index_revised.md",
        "stage5_chart_notes.md",
        "stage5_ppt_ready_notes.md",
    ]
    for d in docs:
        p = REPORTS / d
        check(p.exists() and p.stat().st_size > 3_000, f"文档 {d}", f"{p.stat().st_size if p.exists() else 0}")

    failed = [c for c in checks if not c[0]]
    for ok, name, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print(f"\n共 {len(checks)} 项，通过 {len(checks)-len(failed)} 项，失败 {len(failed)} 项")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
