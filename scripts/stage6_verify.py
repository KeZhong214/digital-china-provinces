"""第六阶段核对：主图齐备、编号与矩阵底表一致、文档完整、口径无越界。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S6 = ROOT / "data/processed/stage6"
FIG = ROOT / "reports/figures_stage6"
REPORTS = ROOT / "reports"

checks: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    checks.append((bool(ok), name, detail))


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, encoding="utf-8-sig")


def main() -> int:
    num = read(S6 / "province_numbering.csv")
    mat = read(S6 / "gov_matrix_layout.csv")
    keys = json.loads((S6 / "stage6_key_numbers.json").read_text(encoding="utf-8"))

    # ---------- 编号 ----------
    check(len(num) == 31 and num["map_no"].nunique() == 31, "编号31省唯一")
    check(sorted(num["map_no"].tolist()) == list(range(1, 32)), "编号为1—31连续")
    region_order = num.sort_values("map_no")["region_4"].tolist()
    check(region_order[:10].count("东部") == 10 and region_order[10:16].count("中部") == 6
          and region_order[16:28].count("西部") == 12 and region_order[28:].count("东北") == 3,
          "编号按区域分组（10/6/12/3）")
    check(set(keys["numbering"]["key_provinces"]) == {"北京", "河北", "广东", "宁夏", "重庆"}, "关键省份5个")

    # ---------- 矩阵 ----------
    check(len(mat) == 31 and mat["short_name"].nunique() == 31, "矩阵31省唯一")
    tier_counts = mat["tier"].value_counts()
    check((tier_counts.get("优秀", 0), tier_counts.get("良好", 0), tier_counts.get("中等", 0)) == (13, 14, 4),
          "矩阵档级 13/14/4")
    per_region = mat.groupby("region").size().to_dict()
    check(per_region == {"东部": 10, "中部": 6, "西部": 12, "东北": 3}, "矩阵区域省数 10/6/12/3", str(per_region))
    check(bool((mat["col"] >= 1).all()), "矩阵列号从1开始")
    check(int(keys["gov_matrix"]["total"]["优秀"]) == 13, "JSON档级总数一致")

    # ---------- 关键数字（与阶段5一致） ----------
    s5 = json.loads((ROOT / "data/processed/stage5/stage5_key_numbers.json").read_text(encoding="utf-8"))
    for k in ["descriptive", "correlation", "rank_gap", "fragility", "cases"]:
        check(keys[k] == s5[k], f"关键数字 {k} 与阶段5一致")
    check(abs(keys["cases"]["beijing_hebei_d1_gap_pp"] - 14.754) < 1e-2, "京冀差14.75")

    # ---------- 图表 ----------
    figs = {
        "map_d1_ecommerce_final": (3999, 2250),
        "map_d2_accounts_final": (3999, 2250),
        "regional_mean_median_final": (3999, 2250),
        "scatter_d1_d2_final": (3999, 2250),
        "gov_category_matrix_final": (3999, 2250),
        "sunburst_region_province_main": (3999, 2250),
        "case_card_beijing_hebei_final": (3999, 2250),
        "case_card_ningxia_final": (3999, 2250),
        "case_card_guangdong_final": (3999, 2250),
    }
    for name, (w, h) in figs.items():
        png, pdf = FIG / f"{name}.png", FIG / f"{name}.pdf"
        ok = png.exists() and pdf.exists()
        dim = Image.open(png).size if ok else (0, 0)
        check(ok and abs(dim[0] - w) <= 1 and abs(dim[1] - h) <= 1 and png.stat().st_size > 80_000,
              f"图 {name}", str(dim))

    # ---------- 文档 ----------
    docs = [
        "stage6_summary.md",
        "stage6_research_draft_final.md",
        "stage6_presentation_outline_final.md",
        "stage6_key_findings_final.md",
        "stage6_storyline_map_final.md",
        "figure_style_guide_final.md",
        "figure_index_final.md",
        "stage6_chart_notes.md",
        "stage6_ppt_ready_checklist.md",
    ]
    for d in docs:
        p = REPORTS / d
        check(p.exists() and p.stat().st_size > 3_000, f"文档 {d}", f"{p.stat().st_size if p.exists() else 0}")

    # ---------- 口径检查 ----------
    text_all = "".join((REPORTS / d).read_text(encoding="utf-8") for d in docs if (REPORTS / d).exists())
    banned_positive = ["官方综合排名第", "全国综合排名第", "综合得分榜"]
    check(not any(b in text_all for b in banned_positive), "无肯定语气的排名表述")
    check("港澳台" in text_all and "中国台湾省" in text_all, "文本含台湾省与港澳台说明")
    src_map = (ROOT / "scripts/stage6_figures.py").read_text(encoding="utf-8")
    check("中国台湾省" in src_map, "地图代码含中国台湾省标注")
    check("未纳入统计样本" in src_map, "地图代码含未纳入样本说明")

    failed = [c for c in checks if not c[0]]
    for ok, name, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print(f"\n共 {len(checks)} 项，通过 {len(checks)-len(failed)} 项，失败 {len(failed)} 项")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
