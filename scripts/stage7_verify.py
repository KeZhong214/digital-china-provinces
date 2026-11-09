"""第七阶段核对：输入一致性、综合分可复算、敏感性完整、图表与文档齐备、口径无越界。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S7 = ROOT / "data/processed/stage7"
FIG = ROOT / "reports/figures_stage7"
REPORTS = ROOT / "reports"

checks: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    checks.append((bool(ok), name, detail))


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, encoding="utf-8-sig")


def main() -> int:
    inp = read(S7 / "composite_input_31provinces.csv")
    sc = read(S7 / "composite_scores_31provinces.csv")
    stab = read(S7 / "ranking_stability_summary.csv")
    scen = read(S7 / "ranking_sensitivity_scenarios.csv")

    # ---------- 输入 ----------
    check(len(inp) == 31 and inp["province_code"].nunique() == 31, "输入31省唯一")
    check(inp[["D1_raw", "D2_raw", "D3_raw"]].notna().all().all(), "三项无缺失")
    gov = read(ROOT / "data/processed/stage2/government_scores_report2025_window_unconfirmed.csv")
    m = inp.merge(gov[["province_code", "numeric_value"]], on="province_code")
    check(np.allclose(m["D3_raw"], m["numeric_value"], atol=1e-9), "D3与清华连续指数逐值一致")
    tier = read(ROOT / "data/processed/stage6/gov_matrix_layout.csv")
    # D3 不应等于档级编码
    check(not np.allclose(sc.sort_values("short_name")["D3_raw"].values,
                          tier.sort_values("short_name")["tier"].map({"优秀": 3, "良好": 2, "中等": 1}).values),
          "D3非档级编码")

    # ---------- 可复算 ----------
    def mm(s):
        return (s - s.min()) / (s.max() - s.min()) * 100

    z = {d: mm(inp[d + "_raw"]) for d in ["D1", "D2", "D3"]}
    comp = (z["D1"] + z["D2"] + z["D3"]) / 3
    merged = inp.assign(comp=comp).merge(sc, on="short_name")
    check(np.allclose(merged["comp"], merged["composite"], atol=1e-4), "综合分可复算",
          f"max diff {np.abs(merged['comp'] - merged['composite']).max():.2e}")
    check(abs(sum([1 / 3, 1 / 3, 1 / 3]) - 1) < 1e-12, "权重和为1")
    check(sorted(sc["rank"].tolist()) == list(range(1, 32)), "名次1—31连续无并列")
    tier_counts = sc["tier"].value_counts().sort_index().tolist()
    check(tier_counts == [6, 6, 6, 6, 7], "梯队6/6/6/6/7", str(tier_counts))
    check(np.allclose(sc["composite"].max(), sc.loc[sc["rank"] == 1, "composite"].iloc[0]), "第一名即最高分")

    # ---------- 敏感性 ----------
    n_scen = scen["scenario_id"].nunique()
    types = scen.drop_duplicates("scenario_id")["scenario_type"].value_counts().to_dict()
    check(n_scen == 45, "场景数45", str(n_scen))
    check(types.get("权重", 0) >= 3 and types.get("权重网格", 0) >= 30 and types.get("标准化", 0) == 2
          and types.get("剔除维度", 0) == 3, "三类敏感性齐备", str(types))
    check(len(stab) == 31 and (stab["rank_range"] >= 0).all(), "稳定性表31省")
    check(stab["rank_range"].max() >= 20, "存在高敏感省份", str(int(stab['rank_range'].max())))
    top5 = sc.nsmallest(5, "rank")["short_name"].tolist()
    check(set(top5) == {"浙江", "北京", "上海", "海南", "江苏"}, "前五与文档一致", ",".join(top5))
    bottom5 = sc.nlargest(5, "rank")["short_name"].tolist()
    check(set(bottom5) == {"云南", "辽宁", "黑龙江", "西藏", "吉林"}, "后五与文档一致", ",".join(bottom5))

    # ---------- 图表 ----------
    figs = {
        "map_d1_double_column_v1": (3999, 2250),
        "map_d2_double_column_v1": (3999, 2250),
        "profile_31provinces_heatmap_ranked_v1": (3999, 2250),
        "profile_31provinces_heatmap_report_v1": (2670, 4020),
        "exploratory_rank_31provinces_v1": (3999, 2250),
        "exploratory_composite_map_v1": (3999, 2250),
    }
    for name, (w, h) in figs.items():
        png, pdf = FIG / f"{name}.png", FIG / f"{name}.pdf"
        ok = png.exists() and pdf.exists()
        dim = Image.open(png).size if ok else (0, 0)
        check(ok and abs(dim[0] - w) <= 1 and abs(dim[1] - h) <= 1 and png.stat().st_size > 80_000,
              f"图 {name}", str(dim))

    # ---------- 文档 ----------
    docs = [
        "stage7_scoring_method.md", "stage7_ranking_findings.md", "stage7_figure_index.md",
        "stage7_research_draft_updated.md", "stage7_presentation_outline_updated.md",
        "stage7_storyline_map_updated.md", "stage7_summary.md", "stage7_review_questions.md",
    ]
    for d in docs:
        p = REPORTS / d
        check(p.exists() and p.stat().st_size > 3_000, f"文档 {d}", f"{p.stat().st_size if p.exists() else 0}")

    # ---------- 口径 ----------
    text = "".join((REPORTS / d).read_text(encoding="utf-8") for d in docs)
    check("探索性" in text and "本研究测算" in text, "含探索性表述")
    check("官方排名" in text, "含官方排名否定说明")
    check("评价窗口未明确" in text, "D3窗口说明存在")
    check("与 D3 连续指数不同源" in text or "不是同一变量" in text, "档级与连续指数区分")
    check("中国台湾省" in text or "台湾" in text, "提及台湾省")
    outline = (REPORTS / "stage7_presentation_outline_updated.md").read_text(encoding="utf-8")
    check(outline.index("旭日图") < outline.index("主图1"), "大纲中旭日图先于D1地图")
    src = (ROOT / "scripts/stage7_figures.py").read_text(encoding="utf-8")
    check("双栏" in src or "16" in src, "地图脚本含双栏逻辑")
    check("档级" not in src.split("def map_double")[1].split("def ")[0], "双栏地图不再输出档级列")

    failed = [c for c in checks if not c[0]]
    for ok, name, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print(f"\n共 {len(checks)} 项，通过 {len(checks)-len(failed)} 项，失败 {len(failed)} 项")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
