"""第七阶段：31省三维探索性综合评分与敏感性分析。

输入（全部为既有已审核数据，不新增检索）：
    D1 NBS_ECOM_SHARE（2024）  <- data/processed/stage3/indicator_review_panel_2024.csv
    D2 BB_ACCOUNTS_PER100（2024年末） <- 同上
    D3 THU_GOV_G202_SCORE（清华团队，载《数字生态指数2025》，评价窗口未明确）
        <- data/processed/stage2/government_scores_report2025_window_unconfirmed.csv

方法：各维在31省内 Min–Max 标准化到 0—100，基准等权合成；再做权重、标准化、剔除维度三类敏感性。
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed/stage7"
OUT.mkdir(parents=True, exist_ok=True)

REGION_ORDER = ["东部", "中部", "西部", "东北"]
DIMS = ["D1", "D2", "D3"]


def minmax(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi == lo:
        raise ValueError("某一维在31省内无区分度，不能 Min–Max")
    return (s - lo) / (hi - lo) * 100.0


def percentile(s: pd.Series) -> pd.Series:
    """百分位得分：最小值 0、最大值 100（(rank-1)/(n-1)*100，降序）。"""
    r = s.rank(ascending=False, method="average")
    return (1 - (r - 1) / (len(s) - 1)) * 100.0


def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)


def weighted_score(df: pd.DataFrame, weights: dict[str, float], cols: dict[str, str]) -> pd.Series:
    total = sum(weights.values())
    assert abs(total - 1) < 1e-9, total
    return sum(df[cols[d]] * w for d, w in weights.items())


def rank_scores(scores: pd.Series) -> pd.Series:
    return scores.round(6).rank(ascending=False, method="min").astype(int)


def main() -> None:
    panel = pd.read_csv(ROOT / "data/processed/stage3/indicator_review_panel_2024.csv", encoding="utf-8-sig")
    gov = pd.read_csv(
        ROOT / "data/processed/stage2/government_scores_report2025_window_unconfirmed.csv",
        encoding="utf-8-sig",
    )
    gov = gov[["province_code", "numeric_value", "source_id", "source_page_or_table", "period_type"]].rename(
        columns={"numeric_value": "D3_raw"}
    )
    df = panel[["province_code", "province_name", "short_name", "region_4", "display_order",
                "ecommerce", "accounts"]].rename(columns={"ecommerce": "D1_raw", "accounts": "D2_raw"})
    df = df.merge(gov, on="province_code", how="left")
    df = df.sort_values("province_code").reset_index(drop=True)

    assert len(df) == 31, len(df)
    assert df[["D1_raw", "D2_raw", "D3_raw"]].notna().all().all(), "存在缺失，停止计算"
    assert df["province_code"].nunique() == 31

    # ---------- 标准化 ----------
    for d in DIMS:
        df[f"{d}_minmax"] = minmax(df[f"{d}_raw"]).round(6)
        df[f"{d}_pct"] = percentile(df[f"{d}_raw"]).round(6)
        df[f"{d}_z"] = zscore(df[f"{d}_raw"]).round(6)

    # ---------- 基准合成 ----------
    base_w = {"D1": 1 / 3, "D2": 1 / 3, "D3": 1 / 3}
    cols = {d: f"{d}_minmax" for d in DIMS}
    df["composite"] = weighted_score(df, base_w, cols).round(6)
    df["rank"] = rank_scores(df["composite"])
    df = df.sort_values("rank").reset_index(drop=True)
    df["tier"] = pd.cut(df["rank"], bins=[0, 6, 12, 18, 24, 31], labels=[1, 2, 3, 4, 5]).astype(int)

    # 结构特征（基于标准化值的相对高低，不凭印象）
    label = {"D1": "企业应用", "D2": "宽带配置", "D3": "政府发展"}
    feats, shorts = [], []
    for _, r in df.iterrows():
        z = {d: float(r[f"{d}_minmax"]) for d in DIMS}
        hi, lo = max(z, key=z.get), min(z, key=z.get)
        spread = z[hi] - z[lo]
        if spread < 10:
            feats.append("三维较均衡")
            shorts.append(f"{hi}略高")
        else:
            feats.append(f"{label[hi]}相对较强、{label[lo]}相对较弱")
            shorts.append(f"{hi}↑{lo}↓")
    df["structure"] = feats
    df["structure_short"] = shorts

    # ---------- 输入表 ----------
    inp = df[["province_code", "province_name", "short_name", "region_4", "D1_raw", "D2_raw", "D3_raw"]].copy()
    inp["D1_period"] = "2024年全年（表16-39，E02）"
    inp["D2_period"] = "2024年末（表16-36、表2-5，I203/A01）"
    inp["D3_period"] = "清华团队数字政府发展指数（载《数字生态指数2025》；具体评价窗口未明确）"
    inp.to_csv(OUT / "composite_input_31provinces.csv", index=False, encoding="utf-8-sig")

    scores = df[["rank", "tier", "short_name", "province_name", "region_4",
                 "D1_raw", "D2_raw", "D3_raw", "D1_minmax", "D2_minmax", "D3_minmax",
                 "composite", "structure"]].copy()
    scores.to_csv(OUT / "composite_scores_31provinces.csv", index=False, encoding="utf-8-sig")

    profile = df[["rank", "tier", "short_name", "province_name", "region_4",
                  "D1_minmax", "D2_minmax", "D3_minmax", "composite", "structure_short",
                  "D1_raw", "D2_raw", "D3_raw"]].copy()
    profile.to_csv(OUT / "profile_31provinces.csv", index=False, encoding="utf-8-sig")

    # ---------- 敏感性：场景集合 ----------
    scenarios = []

    def add(sid, stype, params, weights, std_cols, note=""):
        scores_s = weighted_score(df, weights, std_cols)
        ranks = rank_scores(scores_s)
        tmp = pd.DataFrame({
            "scenario_id": sid, "scenario_type": stype, "params": params,
            "short_name": df["short_name"], "score": scores_s.round(6), "rank": ranks,
        })
        scenarios.append(tmp)

    # A1 权重敏感性（四个事先明确的方案）
    add("base_equal", "基准", "等权(1/3,1/3,1/3)", base_w, cols)
    for name, w in [("w_D1_50", {"D1": .5, "D2": .25, "D3": .25}),
                    ("w_D2_50", {"D1": .25, "D2": .5, "D3": .25}),
                    ("w_D3_50", {"D1": .25, "D2": .25, "D3": .5})]:
        add(name, "权重", f"({w['D1']:.2f},{w['D2']:.2f},{w['D3']:.2f})", w, cols)

    # A2 权重网格：每个权重 0.20–0.50、步长 0.05、和为 1
    grid = [v / 100 for v in range(20, 51, 5)]
    n_grid = 0
    for a, b, c in itertools.product(grid, repeat=3):
        if abs(a + b + c - 1) > 1e-9:
            continue
        n_grid += 1
        add(f"grid_{n_grid:02d}", "权重网格", f"({a:.2f},{b:.2f},{c:.2f})",
            {"D1": a, "D2": b, "D3": c}, cols)

    # B 标准化敏感性
    add("std_pct", "标准化", "百分位等权", base_w, {d: f"{d}_pct" for d in DIMS})
    zcols = {d: f"{d}_z" for d in DIMS}
    add("std_z", "标准化", "Z分数等权（仅比名次）", base_w, zcols)

    # C 剔除维度（仅诊断）
    for drop in DIMS:
        keep = [d for d in DIMS if d != drop]
        w = {d: (1 / 2 if d in keep else 0.0) for d in DIMS}
        add(f"drop_{drop}", "剔除维度", f"剔除{drop}，其余两维等权", w, cols)

    scen = pd.concat(scenarios, ignore_index=True)
    scen.to_csv(OUT / "ranking_sensitivity_scenarios.csv", index=False, encoding="utf-8-sig")

    # ---------- 稳定性汇总 ----------
    base_rank = dict(zip(df["short_name"], df["rank"]))
    rows = []
    for name, g in scen.groupby("short_name"):
        ranks = g["rank"].values
        rows.append({
            "short_name": name,
            "base_rank": int(base_rank[name]),
            "min_rank": int(ranks.min()),
            "max_rank": int(ranks.max()),
            "median_rank": float(np.median(ranks)),
            "rank_range": int(ranks.max() - ranks.min()),
            "top5_freq": float((ranks <= 5).mean()),
            "top10_freq": float((ranks <= 10).mean()),
            "n_scenarios": int(len(ranks)),
        })
    stab = pd.DataFrame(rows).sort_values("base_rank")
    stab.to_csv(OUT / "ranking_stability_summary.csv", index=False, encoding="utf-8-sig")

    # 场景级别：与基准的 Spearman、最大名次变化、前三/前五/前十集合
    base_scores = dict(zip(df["short_name"], df["composite"]))
    scen_stats = []
    for sid, g in scen.groupby("scenario_id"):
        merged = g.set_index("short_name").join(stab.set_index("short_name")["base_rank"])
        rho = merged["rank"].corr(merged["base_rank"], method="spearman")
        max_shift = (merged["rank"] - merged["base_rank"]).abs().max()
        top5 = set(merged.nsmallest(5, "rank").index)
        base_top5 = set(merged.nsmallest(5, "base_rank").index)
        scen_stats.append({
            "scenario_id": sid,
            "scenario_type": g["scenario_type"].iloc[0],
            "params": g["params"].iloc[0],
            "spearman_vs_base": round(float(rho), 4),
            "max_rank_shift": int(max_shift),
            "top5_overlap": len(top5 & base_top5),
        })
    stats = pd.DataFrame(scen_stats)
    stats.to_csv(OUT / "scenario_stats.csv", index=False, encoding="utf-8-sig")

    # 区域统计（综合分与分项）
    reg_rows = []
    for region in REGION_ORDER:
        sub = df[df["region_4"] == region]
        for metric, series in [("composite", sub["composite"]), ("D1_minmax", sub["D1_minmax"]),
                               ("D2_minmax", sub["D2_minmax"]), ("D3_minmax", sub["D3_minmax"])]:
            reg_rows.append({
                "region": region, "metric": metric, "n": len(sub),
                "mean": round(float(series.mean()), 4), "median": round(float(series.median()), 4),
                "min": round(float(series.min()), 4), "max": round(float(series.max()), 4),
                "range": round(float(series.max() - series.min()), 4),
                "cv_pct": round(float(series.std(ddof=0) / series.mean() * 100), 4),
            })
    # 区域内名次跨度
    for region in REGION_ORDER:
        sub = df[df["region_4"] == region]
        reg_rows.append({"region": region, "metric": "rank_span", "n": len(sub),
                         "mean": round(float(sub["rank"].mean()), 4), "median": float(sub["rank"].median()),
                         "min": int(sub["rank"].min()), "max": int(sub["rank"].max()),
                         "range": int(sub["rank"].max() - sub["rank"].min()), "cv_pct": None})
    regions = pd.DataFrame(reg_rows)
    regions.to_csv(OUT / "regional_composite_stats.csv", index=False, encoding="utf-8-sig")

    # ---------- 关键数字 JSON ----------
    def prov(name):
        r = df[df["short_name"] == name].iloc[0]
        return {"rank": int(r["rank"]), "tier": int(r["tier"]), "score": round(float(r["composite"]), 2),
                "z": {d: round(float(r[f"{d}_minmax"]), 2) for d in DIMS},
                "raw": {d: round(float(r[f"{d}_raw"]), 4) for d in DIMS},
                "structure": r["structure"]}

    # 综合接近但结构不同：|Δscore|<3 且 z 向量 L1 距离 > 40
    pairs = []
    for i in range(len(df)):
        for j in range(i + 1, len(df)):
            a, b = df.iloc[i], df.iloc[j]
            if abs(a["composite"] - b["composite"]) < 3:
                l1 = sum(abs(a[f"{d}_minmax"] - b[f"{d}_minmax"]) for d in DIMS)
                if l1 > 40:
                    pairs.append({"a": a["short_name"], "b": b["short_name"],
                                  "score_gap": round(abs(a["composite"] - b["composite"]), 2),
                                  "l1": round(float(l1), 1),
                                  "a_rank": int(a["rank"]), "b_rank": int(b["rank"]),
                                  "a_struct": a["structure"], "b_struct": b["structure"]})
    pairs = sorted(pairs, key=lambda x: -x["l1"])[:8]

    key = {
        "method": {
            "standardization": "Min–Max per dimension across 31 provinces -> 0–100",
            "weights_base": {"D1": round(1/3, 6), "D2": round(1/3, 6), "D3": round(1/3, 6)},
            "tie_rule": "同分同名次（方法 min），后续名次跳号；同分判断用6位小数",
            "tiers": "按基准名次五等分：1–6/7–12/13–18/19–24/25–31",
        },
        "sources": {
            "D1": "NBS_ECOM_SHARE，2024年全年，《中国统计年鉴2025》表16-39（E02）",
            "D2": "BB_ACCOUNTS_PER100，2024年末，表16-36、表2-5（I203/A01）",
            "D3": "THU_GOV_G202_SCORE，清华团队数字政府发展指数，载《数字生态指数2025》；具体评价窗口未明确",
        },
        "top5": [{"name": r["short_name"], "score": round(float(r["composite"]), 2), "rank": int(r["rank"])}
                 for _, r in df.nsmallest(5, "rank").iterrows()],
        "bottom5": [{"name": r["short_name"], "score": round(float(r["composite"]), 2), "rank": int(r["rank"])}
                    for _, r in df.nlargest(5, "rank").iterrows()],
        "cases": {n: prov(n) for n in ["北京", "河北", "广东", "宁夏", "重庆", "浙江", "西藏"]},
        "most_unstable": stab.nlargest(6, "rank_range")[["short_name", "base_rank", "min_rank", "max_rank", "rank_range"]].to_dict("records"),
        "most_stable_top": stab[stab["base_rank"] <= 10].nsmallest(5, "rank_range")[["short_name", "base_rank", "min_rank", "max_rank", "rank_range"]].to_dict("records"),
        "structure_pairs": pairs,
        "region_stats": regions.to_dict("records"),
        "scenario_stats": {
            "n_scenarios": int(scen["scenario_id"].nunique()),
            "min_spearman": round(float(stats["spearman_vs_base"].min()), 4),
            "mean_spearman": round(float(stats["spearman_vs_base"].mean()), 4),
            "max_rank_shift": int(stats["max_rank_shift"].max()),
            "top5_overlap_min": int(stats["top5_overlap"].min()),
        },
        "d3_note": "D3来源报告为2025年版，原报告未明确该分指数评价窗口；本合成不得称为2024年度官方排名。",
    }
    (OUT / "stage7_key_numbers.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------- 控制台核对 ----------
    pd.set_option("display.width", 200)
    print(df[["rank", "tier", "short_name", "region_4", "D1_minmax", "D2_minmax", "D3_minmax",
              "composite", "structure"]].to_string(index=False))
    print("\n场景数:", scen["scenario_id"].nunique(), "| 权重网格:", n_grid)
    print("Spearman范围:", round(stats['spearman_vs_base'].min(), 4), "-", round(stats['spearman_vs_base'].max(), 4))
    print("最大名次变化:", int(stats['max_rank_shift'].max()))
    print("\n最不稳定:", stab.nlargest(5, 'rank_range')[['short_name', 'base_rank', 'min_rank', 'max_rank', 'rank_range']].to_dict('records'))
    print("\n结构差异对:", pairs[:4])
    print("\n文件:", sorted(p.name for p in OUT.glob('*')))


if __name__ == "__main__":
    main()
