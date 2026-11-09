"""第四阶段完整性核对。

独立重算（不依赖阶段4中间结果）并校验：
1. 阶段4面板与原审核面板逐值一致；
2. 描述统计、区域统计、名次差、相关系数、档级计数可复算；
3. 图表文件齐备且画布尺寸符合规范；
4. 报告文件齐备。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
S4 = ROOT / "data/processed/stage4"
FIG = ROOT / "reports/figures_stage4"
REPORTS = ROOT / "reports"

checks: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    checks.append((bool(ok), name, detail))


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def main() -> int:
    # ---------- 输入 ----------
    src = read(ROOT / "data/processed/stage3/indicator_review_panel_2024.csv")
    single = read(ROOT / "data/processed/stage2/single_indicator_panel.csv")
    panel = read(S4 / "stage4_province_panel.csv")
    keys = json.loads((S4 / "stage4_key_numbers.json").read_text(encoding="utf-8"))

    # ---------- 1. 面板一致性 ----------
    check(len(panel) == 31 and panel["province_code"].nunique() == 31, "面板31省唯一", str(len(panel)))
    merged = panel.merge(src[["province_code", "ecommerce", "accounts"]], on="province_code", how="left")
    check(
        np.allclose(merged["d1_ecommerce_pct"], merged["ecommerce"], atol=1e-6),
        "D1与原审核面板逐值一致",
        f"max diff {np.abs(merged['d1_ecommerce_pct'] - merged['ecommerce']).max():.2e}",
    )
    check(
        np.allclose(merged["d2_accounts_per100"], merged["accounts"], atol=1e-6),
        "D2与原审核面板逐值一致",
        f"max diff {np.abs(merged['d2_accounts_per100'] - merged['accounts']).max():.2e}",
    )

    # ---------- 2. 名次 ----------
    d1_rank = panel["d1_ecommerce_pct"].rank(ascending=False, method="min").astype(int)
    d2_rank = panel["d2_accounts_per100"].rank(ascending=False, method="min").astype(int)
    check((d1_rank.values == panel["d1_rank"].values).all(), "D1名次可复算")
    check((d2_rank.values == panel["d2_rank"].values).all(), "D2名次可复算")
    check(
        (panel["rank_gap_d1_minus_d2"] == panel["d1_rank"] - panel["d2_rank"]).all(),
        "名次差= D1名次−D2名次",
    )

    # ---------- 3. 描述统计 ----------
    desc = read(S4 / "stage4_descriptive_statistics.csv").set_index("metric")
    for metric, col in [("d1", "d1_ecommerce_pct"), ("d2", "d2_accounts_per100")]:
        s = panel[col]
        row = desc.loc[metric]
        ok = (
            abs(row["mean"] - s.mean()) < 1e-3
            and abs(row["median"] - s.median()) < 1e-3
            and abs(row["minimum"] - s.min()) < 1e-3
            and abs(row["maximum"] - s.max()) < 1e-3
            and abs(row["range"] - (s.max() - s.min())) < 1e-3
            and abs(row["cv_pct"] - s.std(ddof=0) / s.mean() * 100) < 1e-2
        )
        check(ok, f"{metric.upper()}描述统计可复算", f"mean={s.mean():.4f} median={s.median():.4f}")

    # ---------- 4. 区域统计 ----------
    reg = read(S4 / "fig3_regional_center_dispersion.csv")
    ok_all = True
    detail = []
    for metric, col in [("d1", "d1_ecommerce_pct"), ("d2", "d2_accounts_per100")]:
        for region in ["东部", "中部", "西部", "东北"]:
            s = panel.loc[panel["region_4"] == region, col]
            row = reg[(reg["metric"] == metric) & (reg["region"] == region)].iloc[0]
            if not (
                abs(row["mean"] - s.mean()) < 1e-3
                and abs(row["median"] - s.median()) < 1e-3
                and abs(row["range"] - (s.max() - s.min())) < 1e-3
                and abs(row["cv_pct"] - s.std(ddof=0) / s.mean() * 100) < 1e-2
                and row["n"] == len(s)
            ):
                ok_all = False
                detail.append(f"{metric}-{region}")
    check(ok_all, "四大区域统计可复算", ",".join(detail) or "8组全部一致")

    # ---------- 5. 均值/中位数排序 ----------
    d1_mean_order = reg[reg.metric == "d1"].sort_values("mean", ascending=False)["region"].tolist()
    d1_med_order = reg[reg.metric == "d1"].sort_values("median", ascending=False)["region"].tolist()
    d2_mean_order = reg[reg.metric == "d2"].sort_values("mean", ascending=False)["region"].tolist()
    d2_med_order = reg[reg.metric == "d2"].sort_values("median", ascending=False)["region"].tolist()
    check(d1_mean_order != d1_med_order, "D1均值与中位数排序不同", f"{d1_mean_order} vs {d1_med_order}")
    check(d2_mean_order == d2_med_order, "D2均值与中位数排序相同", str(d2_mean_order))
    check(d1_mean_order == keys["region_orders"]["d1_mean_order"], "JSON区域排序与底表一致")

    # ---------- 6. 相关系数 ----------
    corr = read(S4 / "stage4_correlations.csv").iloc[0]
    pearson = np.corrcoef(panel["d1_ecommerce_pct"], panel["d2_accounts_per100"])[0, 1]
    spearman = panel["d1_ecommerce_pct"].corr(panel["d2_accounts_per100"], method="spearman")
    check(abs(corr["pearson"] - pearson) < 1e-4, "Pearson可复算", f"{pearson:.6f}")
    check(abs(corr["spearman"] - spearman) < 1e-4, "Spearman可复算", f"{spearman:.6f}")

    # ---------- 7. 名次差统计 ----------
    gap = read(S4 / "stage4_rank_gap_table.csv")
    check(abs(gap["abs_rank_gap"].mean() - keys["rank_gap"]["mean_abs_gap"]) < 1e-4, "平均绝对名次差一致")
    check(int((gap["abs_rank_gap"] >= 10).sum()) == 15, "名次差≥10位为15省")
    check(int((gap["abs_rank_gap"] >= 15).sum()) == 8, "名次差≥15位为8省")
    check(gap.iloc[0]["short_name"] == "广东" and gap.iloc[0]["abs_rank_gap"] == 22, "最大名次差为广东22位")

    # ---------- 8. 档级 ----------
    tier_region = read(S4 / "fig5_government_tier_by_region.csv")
    nat = tier_region[tier_region["region"] == "全国31省"].iloc[0]
    check((nat["excellent"], nat["good"], nat["medium"]) == (13, 14, 4), "档级总数13/14/4")
    src_tier = single["gov_category_2024"].value_counts()
    check(
        (src_tier.get("优秀", 0), src_tier.get("良好", 0), src_tier.get("中等", 0)) == (13, 14, 4),
        "档级与原单指标面板一致",
    )
    check(
        set(panel[panel["gov_tier_2024"] == "中等"]["short_name"]) == {"辽宁", "黑龙江", "西藏", "新疆"},
        "中等档四省正确",
    )

    # ---------- 9. 关键案例数字 ----------
    c = keys["cases"]
    check(abs(c["beijing"]["d1"] - 23.287) < 1e-3 and c["beijing"]["d1_rank"] == 1, "北京D1/名次")
    check(abs(c["hebei"]["d2"] - 45.347) < 1e-3 and c["hebei"]["d2_rank"] == 21, "河北D2/名次")
    check(abs(c["beijing_hebei_d1_gap_pp"] - 14.754) < 1e-2, "京冀应用差14.75pp", f"{c['beijing_hebei_d1_gap_pp']}")
    check(abs(c["beijing_hebei_d2_gap"] - 0.0996) < 1e-2, "京冀配置差0.10")
    check(c["ningxia"]["d2_rank"] == 5 and c["ningxia"]["d1_rank"] == 21, "宁夏名次5/21")
    check(c["guangdong"]["d2_rank"] == 31, "广东D2第31")
    check(abs(c["guangdong_quality"]["gigabit_share_pct"] - 29.7752) < 1e-3, "广东千兆占比29.78%")
    check(abs(keys["fragility"]["west_mean_d1_without_chongqing"] - 11.3227) < 1e-3, "删重庆后西部均值11.32")
    check(keys["national"]["ecommerce_weighted_rate_pct"] > 12.77 and keys["national"]["ecommerce_weighted_rate_pct"] < 12.78, "全国合计12.77%")

    # ---------- 10. 图表文件 ----------
    expected = {
        "fig1_ecommerce_ranking": (2610, 3300),
        "fig2_broadband_ranking": (2610, 3300),
        "fig3_regional_center_comparison": (3999, 2250),
        "fig4_application_vs_access_scatter": (3999, 2250),
        "fig5_government_tier_distribution": (3999, 2250),
        "fig6_case_evidence_cards": (3999, 2250),
        "fig6b_guangdong_method_warning": (3999, 2250),
    }
    for name, (w, h) in expected.items():
        png, pdf = FIG / f"{name}.png", FIG / f"{name}.pdf"
        exists = png.exists() and pdf.exists()
        size_ok = exists and png.stat().st_size > 80_000 and pdf.stat().st_size > 5_000
        dim_ok = exists and abs(Image.open(png).size[0] - w) <= 1 and abs(Image.open(png).size[1] - h) <= 1
        check(exists and size_ok and dim_ok, f"图 {name} 齐备且画布合规",
              f"{Image.open(png).size if exists else 'missing'}")

    # ---------- 11. 底表行数 ----------
    rows = {
        "stage4_province_panel.csv": 31,
        "stage4_descriptive_statistics.csv": 2,
        "stage4_top_bottom5.csv": 20,
        "fig1_d1_ranking.csv": 31,
        "fig2_d2_ranking.csv": 31,
        "fig3_regional_center_dispersion.csv": 8,
        "fig4_d1_d2_scatter_panel.csv": 31,
        "stage4_rank_gap_table.csv": 31,
        "stage4_correlations.csv": 1,
        "fig5_government_tier_by_region.csv": 5,
        "fig5_government_tier_by_province.csv": 31,
        "fig6_case_card_table.csv": 4,
    }
    for name, n in rows.items():
        df = read(S4 / name)
        check(len(df) == n, f"底表行数 {name}", f"{len(df)} (期望{n})")

    # ---------- 12. 报告文件 ----------
    for name in [
        "stage4_summary.md",
        "stage4_research_draft.md",
        "stage4_storyline_map.md",
        "stage4_presentation_outline.md",
        "stage4_key_findings.md",
        "figure_style_guide.md",
        "figure_index.md",
    ]:
        p = REPORTS / name
        check(p.exists() and p.stat().st_size > 3_000, f"报告 {name}", f"{p.stat().st_size if p.exists() else 0} bytes")

    # ---------- 输出 ----------
    failed = [c for c in checks if not c[0]]
    for ok, name, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    print()
    print(f"共 {len(checks)} 项，通过 {len(checks) - len(failed)} 项，失败 {len(failed)} 项")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
