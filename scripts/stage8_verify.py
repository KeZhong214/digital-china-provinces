"""第八阶段核对：审核问题是否真正修正、图表与文档是否齐备、口径是否统一。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S8 = ROOT / "data/processed/stage8"
FIG = ROOT / "reports/figures_stage8"
REP = ROOT / "reports"

checks: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    checks.append((bool(ok), name, detail))


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, encoding="utf-8-sig")


def main() -> int:
    scen = read(S8 / "sensitivity_scenarios_deduplicated.csv")
    by_type = read(S8 / "sensitivity_by_type.csv")
    cp = read(S8 / "contrast_pairs.csv")
    key = json.loads((S8 / "stage8_key_numbers.json").read_text(encoding="utf-8"))

    # ---------- 场景去重与分类 ----------
    check(len(scen) == 42, "唯一场景42个", str(len(scen)))
    check(scen["scenario_type"].value_counts().to_dict() ==
          {"权重网格": 36, "剔除维度": 3, "标准化": 2, "基准": 1}, "场景类型1/36/2/3",
          str(scen["scenario_type"].value_counts().to_dict()))
    w = scen[scen.scenario_type == "权重网格"][["w_D1", "w_D2", "w_D3"]]
    check(len(w.drop_duplicates()) == 36, "权重三元组无重复")
    check(np.allclose(w.sum(axis=1), 1.0), "网格权重和为1")

    # ---------- 广东名次 ----------
    gd = by_type[by_type.short_name == "广东"].iloc[0]
    check((int(gd["weight_min"]), int(gd["weight_max"])) == (11, 24), "广东权重区间11—24",
          f"{int(gd['weight_min'])}—{int(gd['weight_max'])}")
    check((int(gd["drop_min"]), int(gd["drop_max"])) == (6, 27), "广东剔除区间6—27")
    special = key["special_weight_schemes"]
    check(special["D1_50"] == 16 and special["D3_50"] == 11 and special["D2_50"] == 24,
          "广东单列权重方案18/16/24/11", str(special))
    check(key["guangdong_drop"]["D2"] == 6, "剔除D2广东第6")

    # ---------- 前五范围 ----------
    b5 = {r["short_name"]: (int(r["all_min"]), int(r["all_max"])) for _, r in
          by_type[by_type.short_name.isin(["浙江", "北京", "上海", "海南", "江苏"])].iterrows()}
    check(b5["浙江"] == (1, 2) and b5["北京"] == (1, 7) and b5["江苏"] == (2, 10), "前五区间正确", str(b5))
    js = by_type[by_type.short_name == "江苏"].iloc[0]
    check(0.75 <= float(js["all_top5_freq"]) <= 0.9, "江苏top5频率约81%", f"{js['all_top5_freq']}")

    # ---------- 区域 CV ----------
    cv = {r["region"]: r["cv_pct"] for r in key["region"]}
    rng = {r["region"]: r["range"] for r in key["region"]}
    check(cv["东北"] == max(cv.values()), "东北CV最高", str(cv))
    check(rng["东部"] == max(rng.values()), "东部极差最大", str(rng))

    # ---------- 对照底表 ----------
    check(len(cp) == 4 and set(cp.group) == {"A", "B"}, "对照两组四行")
    a = cp[cp.group == "A"]
    check(abs(a.composite_gap.iloc[0] - 2.11) < 0.01 and abs(cp[cp.group == "B"].composite_gap.iloc[0] - 1.65) < 0.01,
          "两组分差2.11/1.65")
    gd_row = cp[(cp.group == "B") & (cp.province == "广东")].iloc[0]
    nx = cp[(cp.group == "B") & (cp.province == "宁夏")].iloc[0]
    check(gd_row["D2_z"] == 0 and abs(gd_row["D2_raw"] - 39.51) < 0.01, "广东D2标准化0、原始39.51")
    check(abs(nx["D3_z"] - 7.13) < 0.01 and abs(nx["D3_raw"] - 57.5) < 0.01, "宁夏D3标准化7.1、原始57.50")

    # ---------- 图表 ----------
    figs = {
        "structure_contrast_pairs": (3999, 2250),
        "rank_sensitivity_by_type": (3999, 2250),
        "profile_31provinces_refined": (3999, 2250),
    }
    for name, (w_, h_) in figs.items():
        png, pdf = FIG / f"{name}.png", FIG / f"{name}.pdf"
        dim = Image.open(png).size if png.exists() else (0, 0)
        check(png.exists() and pdf.exists() and abs(dim[0] - w_) <= 1 and abs(dim[1] - h_) <= 1
              and png.stat().st_size > 80_000, f"图 {name}", str(dim))

    # ---------- 文档 ----------
    docs = ["stage8_audit_fix_summary.md", "stage8_ranking_findings_revised.md",
            "stage8_scoring_method_revised.md", "stage8_research_draft_revised.md",
            "stage8_presentation_outline.md", "stage8_figure_index.md"]
    for d in docs:
        p = REP / d
        check(p.exists() and p.stat().st_size > 4_000, f"文档 {d}", f"{p.stat().st_size if p.exists() else 0}")

    # ---------- 旧错误表述不得出现（修正对照表按设计引用旧措辞，故只在正文类文档中检查） ----------
    content_docs = [d for d in docs if d != "stage8_audit_fix_summary.md"]
    text = "".join((REP / d).read_text(encoding="utf-8") for d in content_docs)
    banned = {
        "六个梯队": "梯队数量错误",
        "西部 CV 33.36% 为四区域最高": "CV 排序错误（原文式）",
        "只要提高 D1 或 D3 权重，广东就进入前10": "广东论断错误",
        "只要提高D1或D3权重": "广东论断错误",
    }
    for phrase, why in banned.items():
        check(phrase not in text, f"未出现错误表述：{why}", phrase)
    # 「西部CV最高/最不均衡」类近似表述
    check("西部CV最高" not in text and "西部最不均衡" not in text and "西部变异系数为四区域最高" not in text,
          "无“西部CV最高”类表述")
    check("五个展示分组" in text, "使用“五个展示分组”")
    check("归一化" in text and "原始" in text, "标准化与原始值区分")
    check("42个" in text, "文档标明42个唯一场景")
    check("评价窗口" in text, "D3窗口说明存在")
    check("中国台湾省" in text or "台湾" in text, "提及台湾省")

    failed = [c for c in checks if not c[0]]
    for ok, name, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print(f"\n共 {len(checks)} 项，通过 {len(checks)-len(failed)} 项，失败 {len(failed)} 项")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
