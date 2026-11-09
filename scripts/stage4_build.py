"""第四阶段分析底表构建。

仅使用阶段2/3已审核的31省面板与2024网上政府档级，不新增检索、不合成综合总分。
输出：data/processed/stage4/ 下的图表底表、摘要统计与关键数字JSON。
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/processed"
OUT = SRC / "stage4"
OUT.mkdir(parents=True, exist_ok=True)

TIER_ORDER = {"优秀": 1, "良好": 2, "中等": 3}
REGION_ORDER = ["东部", "中部", "西部", "东北"]
NATIONAL_ENT = 1605346.0
NATIONAL_ECOM_ENT = 205026.0


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def write_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, encoding="utf-8-sig")


def main() -> None:
    panel = read_csv(SRC / "stage3/indicator_review_panel_2024.csv")
    single = read_csv(SRC / "stage2/single_indicator_panel.csv")

    df = panel.merge(
        single[["province_code", "gov_category_2024"]],
        on="province_code",
        how="left",
        validate="one_to_one",
    )
    assert df["gov_category_2024"].notna().all(), "档级缺失"
    assert len(df) == 31

    df["d1"] = df["ecommerce"].astype(float)
    df["d2"] = df["accounts"].astype(float)
    df["d1_rank"] = df["d1"].rank(ascending=False, method="min").astype(int)
    df["d2_rank"] = df["d2"].rank(ascending=False, method="min").astype(int)
    assert df["d1"].nunique() == 31 and df["d2"].nunique() == 31, "存在并列值，需改口径"

    # 名次差：D1名次 − D2名次。正值表示该省在D2上相对更靠前。
    df["rank_gap_d1_minus_d2"] = df["d1_rank"] - df["d2_rank"]
    df["gov_tier_2024"] = df["gov_category_2024"]
    df["gov_tier_order"] = df["gov_tier_2024"].map(TIER_ORDER)

    national_rate = NATIONAL_ECOM_ENT / NATIONAL_ENT * 100.0

    # ---------------- 省际面板底表 ----------------
    province_panel = df[
        [
            "province_code",
            "province_name",
            "short_name",
            "region_4",
            "display_order",
            "d1",
            "d2",
            "d1_rank",
            "d2_rank",
            "rank_gap_d1_minus_d2",
            "gov_tier_2024",
        ]
    ].copy()
    province_panel = province_panel.rename(
        columns={
            "d1": "d1_ecommerce_pct",
            "d2": "d2_accounts_per100",
            "gov_tier_2024": "gov_tier_2024",
        }
    )
    province_panel["d1_delta_vs_national_pp"] = (df["d1"] - national_rate).round(4)
    province_panel["d2_delta_vs_31_mean"] = (df["d2"] - df["d2"].mean()).round(4)
    province_panel = province_panel.sort_values("d1_rank").reset_index(drop=True)
    write_csv(province_panel, "stage4_province_panel.csv")

    # ---------------- 图1底表：D1排序 ----------------
    fig1 = df.sort_values("d1", ascending=False).reset_index(drop=True)
    fig1_out = pd.DataFrame(
        {
            "d1_rank": fig1["d1_rank"],
            "short_name": fig1["short_name"],
            "province_name": fig1["province_name"],
            "region_4": fig1["region_4"],
            "d1_ecommerce_pct": fig1["d1"].round(4),
            "delta_vs_national_pp": (fig1["d1"] - national_rate).round(4),
            "gov_tier_2024": fig1["gov_tier_2024"],
        }
    )
    write_csv(fig1_out, "fig1_d1_ranking.csv")

    # ---------------- 图2底表：D2排序 ----------------
    fig2 = df.sort_values("d2", ascending=False).reset_index(drop=True)
    d2_mean = df["d2"].mean()
    fig2_out = pd.DataFrame(
        {
            "d2_rank": fig2["d2_rank"],
            "short_name": fig2["short_name"],
            "province_name": fig2["province_name"],
            "region_4": fig2["region_4"],
            "d2_accounts_per100": fig2["d2"].round(4),
            "delta_vs_31_mean": (fig2["d2"] - d2_mean).round(4),
            "gov_tier_2024": fig2["gov_tier_2024"],
        }
    )
    write_csv(fig2_out, "fig2_d2_ranking.csv")

    # ---------------- 描述统计 ----------------
    desc_rows = []
    for metric, label, unit in [
        ("d1", "D1 调查企业交易型数字应用（企业电商参与比例）", "%"),
        ("d2", "D2 固定宽带接入配置（每百人固定宽带账户数）", "户/百人"),
    ]:
        s = df[metric]
        desc_rows.append(
            {
                "metric": metric,
                "metric_label": label,
                "unit": unit,
                "n": int(s.count()),
                "mean": round(s.mean(), 4),
                "median": round(s.median(), 4),
                "sd_population": round(s.std(ddof=0), 4),
                "cv_pct": round(s.std(ddof=0) / s.mean() * 100, 4),
                "minimum": round(s.min(), 4),
                "maximum": round(s.max(), 4),
                "range": round(s.max() - s.min(), 4),
                "p25": round(s.quantile(0.25), 4),
                "p75": round(s.quantile(0.75), 4),
                "iqr": round(s.quantile(0.75) - s.quantile(0.25), 4),
            }
        )
    desc = pd.DataFrame(desc_rows)
    write_csv(desc, "stage4_descriptive_statistics.csv")

    # 前五/后五清单
    head_tail_rows = []
    for metric, label in [("d1", "D1"), ("d2", "D2")]:
        ordered = df.sort_values(metric, ascending=False)
        for pos, (_, r) in enumerate(ordered.head(5).iterrows(), start=1):
            head_tail_rows.append(
                {
                    "metric": metric,
                    "group": "前5",
                    "position": pos,
                    "short_name": r["short_name"],
                    "region_4": r["region_4"],
                    "value": round(r[metric], 4),
                }
            )
        for pos, (_, r) in enumerate(ordered.tail(5).iterrows(), start=1):
            head_tail_rows.append(
                {
                    "metric": metric,
                    "group": "后5",
                    "position": pos,
                    "short_name": r["short_name"],
                    "region_4": r["region_4"],
                    "value": round(r[metric], 4),
                }
            )
    write_csv(pd.DataFrame(head_tail_rows), "stage4_top_bottom5.csv")

    # ---------------- 图3底表：四大区域中心与离散 ----------------
    reg_rows = []
    for metric in ["d1", "d2"]:
        for region in REGION_ORDER:
            s = df.loc[df["region_4"] == region, metric]
            reg_rows.append(
                {
                    "metric": metric,
                    "region": region,
                    "n": int(s.count()),
                    "mean": round(s.mean(), 4),
                    "median": round(s.median(), 4),
                    "mean_minus_median": round(s.mean() - s.median(), 4),
                    "minimum": round(s.min(), 4),
                    "maximum": round(s.max(), 4),
                    "range": round(s.max() - s.min(), 4),
                    "sd_population": round(s.std(ddof=0), 4),
                    "cv_pct": round(s.std(ddof=0) / s.mean() * 100, 4),
                }
            )
    reg = pd.DataFrame(reg_rows)
    for metric in ["d1", "d2"]:
        mask = reg["metric"] == metric
        reg.loc[mask, "mean_rank"] = reg.loc[mask, "mean"].rank(ascending=False, method="min").astype(int)
        reg.loc[mask, "median_rank"] = (
            reg.loc[mask, "median"].rank(ascending=False, method="min").astype(int)
        )
    write_csv(reg, "fig3_regional_center_dispersion.csv")

    # ---------------- 图4底表：散点 ----------------
    fig4 = df[
        [
            "short_name",
            "province_name",
            "region_4",
            "d1",
            "d2",
            "d1_rank",
            "d2_rank",
            "rank_gap_d1_minus_d2",
            "gov_tier_2024",
        ]
    ].copy()
    fig4 = fig4.rename(columns={"d1": "d1_ecommerce_pct", "d2": "d2_accounts_per100"})
    fig4["d1_ecommerce_pct"] = fig4["d1_ecommerce_pct"].round(4)
    fig4["d2_accounts_per100"] = fig4["d2_accounts_per100"].round(4)
    fig4["abs_rank_gap"] = fig4["rank_gap_d1_minus_d2"].abs()
    write_csv(fig4.sort_values("abs_rank_gap", ascending=False), "fig4_d1_d2_scatter_panel.csv")

    # ---------------- 图5底表：网上政府档级 ----------------
    tier_counts = (
        df.groupby(["region_4", "gov_tier_2024"]).size().unstack(fill_value=0).reindex(REGION_ORDER)
    )
    for c in TIER_ORDER:
        if c not in tier_counts:
            tier_counts[c] = 0
    tier_counts = tier_counts[list(TIER_ORDER)]
    tier_rows = []
    for region, row in tier_counts.iterrows():
        total = int(row.sum())
        tier_rows.append(
            {
                "region": region,
                "n": total,
                "excellent": int(row["优秀"]),
                "good": int(row["良好"]),
                "medium": int(row["中等"]),
                "excellent_pct": round(row["优秀"] / total * 100, 4),
                "good_pct": round(row["良好"] / total * 100, 4),
                "medium_pct": round(row["中等"] / total * 100, 4),
            }
        )
    total_row = {
        "region": "全国31省",
        "n": int(tier_counts.values.sum()),
        "excellent": int(tier_counts["优秀"].sum()),
        "good": int(tier_counts["良好"].sum()),
        "medium": int(tier_counts["中等"].sum()),
    }
    total_row["excellent_pct"] = round(total_row["excellent"] / total_row["n"] * 100, 4)
    total_row["good_pct"] = round(total_row["good"] / total_row["n"] * 100, 4)
    total_row["medium_pct"] = round(total_row["medium"] / total_row["n"] * 100, 4)
    tier_by_region = pd.DataFrame(tier_rows + [total_row])
    write_csv(tier_by_region, "fig5_government_tier_by_region.csv")

    tier_prov = df[["short_name", "province_name", "region_4", "gov_tier_2024", "d1", "d1_rank", "d2", "d2_rank"]].copy()
    tier_prov["tier_order"] = tier_prov["gov_tier_2024"].map(TIER_ORDER)
    tier_prov["d1_ecommerce_pct"] = tier_prov["d1"].round(4)
    tier_prov["d2_accounts_per100"] = tier_prov["d2"].round(4)
    tier_prov["region_order"] = pd.Categorical(tier_prov["region_4"], REGION_ORDER, ordered=True)
    tier_prov = tier_prov.sort_values(["region_order", "tier_order", "d2"], ascending=[True, True, False])
    write_csv(
        tier_prov[
            [
                "short_name",
                "province_name",
                "region_4",
                "gov_tier_2024",
                "tier_order",
                "d1_ecommerce_pct",
                "d1_rank",
                "d2_accounts_per100",
                "d2_rank",
            ]
        ],
        "fig5_government_tier_by_province.csv",
    )

    # ---------------- 名次差与相关系数 ----------------
    gaps = df[["short_name", "region_4", "d1_rank", "d2_rank", "rank_gap_d1_minus_d2"]].copy()
    gaps["abs_rank_gap"] = gaps["rank_gap_d1_minus_d2"].abs()
    gaps = gaps.sort_values("abs_rank_gap", ascending=False)
    write_csv(gaps, "stage4_rank_gap_table.csv")

    pearson = float(np.corrcoef(df["d1"], df["d2"])[0, 1])
    spearman = float(df["d1"].corr(df["d2"], method="spearman"))
    corr = pd.DataFrame(
        [
            {
                "x": "d1_ecommerce_pct",
                "y": "d2_accounts_per100",
                "n": 31,
                "pearson": round(pearson, 6),
                "spearman": round(spearman, 6),
                "note": "2024全年企业调查/2024年末固定宽带账户；仅描述性，不作因果或综合加权依据",
            }
        ]
    )
    write_csv(corr, "stage4_correlations.csv")

    # ---------------- 图6底表：案例卡 ----------------
    cases = read_csv(SRC / "stage3/case_evidence_figure_data.csv")
    gd_ctx = read_csv(SRC / "stage3/guangdong_quality_context.csv").set_index("indicator_id")
    gd_quality = {
        "fixed_broadband_wan": float(gd_ctx.loc["GD_BB_TOTAL_C303", "numeric_value"]),
        "gigabit_wan": float(gd_ctx.loc["GD_GIGABIT_USERS_C303", "numeric_value"]),
        "gigabit_share_pct": round(float(gd_ctx.loc["GD_GIGABIT_SHARE_C303", "numeric_value"]), 6),
        "source": "C303 广东省通信管理局2024年12月运行情况（同段原值）",
        "note": "仅单省同段派生，不能用于31省质量排名",
    }
    keep = df[df["short_name"].isin(["北京", "河北", "宁夏", "广东"])][
        ["short_name", "region_4", "d1", "d1_rank", "d2", "d2_rank", "gov_tier_2024"]
    ].copy()
    keep["d1_ecommerce_pct"] = keep["d1"].round(4)
    keep["d2_accounts_per100"] = keep["d2"].round(4)
    case_table = keep.merge(cases, left_on="short_name", right_on="province", how="left")
    write_csv(
        case_table[
            [
                "short_name",
                "region_4",
                "d1_ecommerce_pct",
                "d1_rank",
                "d2_accounts_per100",
                "d2_rank",
                "gov_tier_2024",
                "implementation",
                "regional_topic",
                "boundary",
            ]
        ],
        "fig6_case_card_table.csv",
    )

    # ---------------- 关键数字JSON ----------------
    def regstat(metric: str, region: str, col: str) -> float:
        row = reg[(reg["metric"] == metric) & (reg["region"] == region)].iloc[0]
        return float(row[col])

    d1_mean_order = (
        reg[reg["metric"] == "d1"].sort_values("mean", ascending=False)["region"].tolist()
    )
    d1_median_order = (
        reg[reg["metric"] == "d1"].sort_values("median", ascending=False)["region"].tolist()
    )
    d2_mean_order = (
        reg[reg["metric"] == "d2"].sort_values("mean", ascending=False)["region"].tolist()
    )
    d2_median_order = (
        reg[reg["metric"] == "d2"].sort_values("median", ascending=False)["region"].tolist()
    )

    def prov(name: str) -> dict:
        r = df[df["short_name"] == name].iloc[0]
        return {
            "d1": round(float(r["d1"]), 4),
            "d1_rank": int(r["d1_rank"]),
            "d2": round(float(r["d2"]), 4),
            "d2_rank": int(r["d2_rank"]),
            "rank_gap": int(r["rank_gap_d1_minus_d2"]),
            "tier": r["gov_tier_2024"],
            "region": r["region_4"],
        }

    bj, hb, nx, gd, cq = prov("北京"), prov("河北"), prov("宁夏"), prov("广东"), prov("重庆")
    sd = prov("山东")

    key = {
        "meta": {
            "stage": "stage4",
            "n_provinces": 31,
            "route": "方案B：31省分项画像 + 2024网上政府档级展示 + 典型地区案例；不合成三维综合总分",
            "source_panel": "data/processed/stage3/indicator_review_panel_2024.csv + data/processed/stage2/single_indicator_panel.csv",
            "d1_definition": "NBS_ECOM_SHARE = 有电子商务交易活动企业数 / 同表调查企业数 × 100，单位%",
            "d1_period": "2024年全年（《中国统计年鉴2025》表16-39，来源E02）",
            "d2_definition": "BB_ACCOUNTS_PER100 = 固定宽带账户万户 / 年末常住人口万人 × 100，单位户/百人",
            "d2_period": "2024年末（《中国统计年鉴2025》表16-36、表2-5，来源I203/A01）",
            "d3_definition": "2024年网上政府发展档级（优秀/良好/中等），调查窗口2024年9月上旬—10月上旬，来源S27；不转数值",
        },
        "national": {
            "ecommerce_weighted_rate_pct": round(national_rate, 4),
            "ecommerce_ent_national": NATIONAL_ECOM_ENT,
            "survey_ent_national": NATIONAL_ENT,
            "note": "全国合计=205026/1605346，为调查企业数加权口径，不是31省等权均值",
        },
        "descriptive": {
            "d1": desc[desc["metric"] == "d1"].iloc[0].to_dict(),
            "d2": desc[desc["metric"] == "d2"].iloc[0].to_dict(),
        },
        "region_orders": {
            "d1_mean_order": d1_mean_order,
            "d1_median_order": d1_median_order,
            "d2_mean_order": d2_mean_order,
            "d2_median_order": d2_median_order,
            "d1_order_identical": d1_mean_order == d1_median_order,
            "d2_order_identical": d2_mean_order == d2_median_order,
        },
        "cases": {
            "beijing": bj,
            "hebei": hb,
            "ningxia": nx,
            "guangdong": gd,
            "chongqing": cq,
            "shandong": sd,
            "beijing_hebei_d1_gap_pp": round(bj["d1"] - hb["d1"], 4),
            "beijing_hebei_d2_gap": round(bj["d2"] - hb["d2"], 4),
            "guangdong_quality": gd_quality,
        },
        "rank_gap": {
            "mean_abs_gap": round(gaps["abs_rank_gap"].mean(), 4),
            "median_abs_gap": round(gaps["abs_rank_gap"].median(), 4),
            "max_abs_gap": int(gaps["abs_rank_gap"].max()),
            "n_abs_ge_10": int((gaps["abs_rank_gap"] >= 10).sum()),
            "n_abs_ge_15": int((gaps["abs_rank_gap"] >= 15).sum()),
            "top5_gaps": gaps.head(5)[
                ["short_name", "region_4", "d1_rank", "d2_rank", "rank_gap_d1_minus_d2"]
            ].to_dict("records"),
        },
        "correlation": {
            "pearson": round(pearson, 6),
            "spearman": round(spearman, 6),
            "n": 31,
        },
        "government_tiers": {
            "national": {k: total_row[k] for k in ["excellent", "good", "medium", "n"]},
            "by_region": tier_by_region.to_dict("records"),
            "medium_provinces": df[df["gov_tier_2024"] == "中等"]["short_name"].tolist(),
            "excellent_provinces": df[df["gov_tier_2024"] == "优秀"]["short_name"].tolist(),
        },
        "fragility": {
            "west_mean_d1": regstat("d1", "西部", "mean"),
            "central_mean_d1": regstat("d1", "中部", "mean"),
            "west_median_d1": regstat("d1", "西部", "median"),
            "central_median_d1": regstat("d1", "中部", "median"),
            "west_mean_d1_without_chongqing": None,
            "note": "删重庆后西部D1均值低于中部（见stage3 leave_one_province_out），仅作单省影响诊断",
        },
    }
    loo = read_csv(SRC / "stage3/leave_one_province_out.csv")
    try:
        mask = (
            (loo["metric"] == "ecommerce")
            & (loo["region"] == "西部")
            & (loo["deleted_province"] == "重庆")
        )
        key["fragility"]["west_mean_d1_without_chongqing"] = round(
            float(loo.loc[mask, "mean_after_delete"].iloc[0]), 4
        )
    except Exception as exc:  # pragma: no cover - 兜底，不阻断主流程
        print("fragility lookup failed:", exc)

    (OUT / "stage4_key_numbers.json").write_text(
        json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ---------------- 控制台核对 ----------------
    print("national weighted ecommerce rate %:", round(national_rate, 4))
    print(desc[["metric", "mean", "median", "minimum", "maximum", "range", "cv_pct"]].to_string(index=False))
    print()
    print(reg[["metric", "region", "mean", "median", "range", "cv_pct", "mean_rank", "median_rank"]].to_string(index=False))
    print()
    print("D1 mean order:", d1_mean_order, "| median order:", d1_median_order)
    print("D2 mean order:", d2_mean_order, "| median order:", d2_median_order)
    print()
    print("pearson", round(pearson, 4), "spearman", round(spearman, 4))
    print("mean abs rank gap", round(gaps["abs_rank_gap"].mean(), 4), "n>=10:", int((gaps["abs_rank_gap"] >= 10).sum()))
    print()
    print(tier_by_region.to_string(index=False))
    print()
    print("BJ", bj, "\nHB", hb, "\nNX", nx, "\nGD", gd, "\nCQ", cq)
    print("BJ-HB d1 gap", round(bj["d1"] - hb["d1"], 4), "d2 gap", round(bj["d2"] - hb["d2"], 4))
    print()
    print("files:", sorted(p.name for p in OUT.glob("*")))


if __name__ == "__main__":
    main()
