"""第八阶段：敏感性去重分组、结构对照底表。

输出 data/processed/stage8/：
    sensitivity_scenarios_deduplicated.csv  唯一参数场景清单（42个）
    sensitivity_by_type.csv                 31省 × 类别 的名次区间
    contrast_pairs.csv                      两组结构对照（原值/标准分/总分/分差）
    stage8_key_numbers.json
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S7 = ROOT / "data/processed/stage7"
OUT = ROOT / "data/processed/stage8"
OUT.mkdir(parents=True, exist_ok=True)


def mm(s: pd.Series) -> pd.Series:
    return (s - s.min()) / (s.max() - s.min()) * 100.0


def ranks(score: pd.Series) -> pd.Series:
    return score.round(6).rank(ascending=False, method="min").astype(int)


def main() -> None:
    inp = pd.read_csv(S7 / "composite_input_31provinces.csv", encoding="utf-8-sig")
    sc = pd.read_csv(S7 / "composite_scores_31provinces.csv", encoding="utf-8-sig")
    df = inp[["short_name", "region_4", "D1_raw", "D2_raw", "D3_raw"]].copy()
    df["D1_z"] = mm(df["D1_raw"]).round(6)
    df["D2_z"] = mm(df["D2_raw"]).round(6)
    df["D3_z"] = mm(df["D3_raw"]).round(6)
    df["composite"] = ((df["D1_z"] + df["D2_z"] + df["D3_z"]) / 3).round(6)
    df["base_rank"] = ranks(df["composite"])
    base = dict(zip(df["short_name"], df["base_rank"]))

    # ---------------- 场景集合（去重） ----------------
    rows = []

    def add(sid, stype, detail, w, std, drop):
        s = sum(df[f"{d}_{'z' if std == 'minmax' else 'pctz' if std == 'pct' else 'zstd'}"] * w[d]
                for d in ["D1", "D2", "D3"])
        r = ranks(s)
        rows.append({
            "scenario_id": sid, "scenario_type": stype, "detail": detail,
            "w_D1": round(w["D1"], 4), "w_D2": round(w["D2"], 4), "w_D3": round(w["D3"], 4),
            "standardization": std, "dropped_dim": drop,
            "rank": r.values, "score": s.round(6).values,
        })

    # minmax 列
    for d in ["D1", "D2", "D3"]:
        df[f"{d}_pctz"] = ((1 - (df[f"{d}_raw"].rank(ascending=False, method="average") - 1) / 30) * 100).round(6)
        df[f"{d}_zstd"] = ((df[f"{d}_raw"] - df[f"{d}_raw"].mean()) / df[f"{d}_raw"].std(ddof=0)).round(6)

    add("base", "基准", "等权 Min–Max", {"D1": 1/3, "D2": 1/3, "D3": 1/3}, "minmax", "")

    grid = [v / 100 for v in range(20, 51, 5)]
    k = 0
    for a, b, c in itertools.product(grid, repeat=3):
        if abs(a + b + c - 1) > 1e-9:
            continue
        k += 1
        add(f"W{k:02d}", "权重网格", f"({a:.2f},{b:.2f},{c:.2f})", {"D1": a, "D2": b, "D3": c}, "minmax", "")

    add("S1", "标准化", "百分位等权", {"D1": 1/3, "D2": 1/3, "D3": 1/3}, "pct", "")
    add("S2", "标准化", "Z分数等权（仅比名次）", {"D1": 1/3, "D2": 1/3, "D3": 1/3}, "zstd", "")

    for d in ["D1", "D2", "D3"]:
        w = {x: (0.0 if x == d else 0.5) for x in ["D1", "D2", "D3"]}
        add(f"D{d}", "剔除维度", f"剔除{d}", w, "minmax", d)

    # 把 rank/score 数组展开成省×场景 长表（用于统计）
    long_rows = []
    for row in rows:
        for i, name in enumerate(df["short_name"]):
            long_rows.append({
                "scenario_id": row["scenario_id"], "scenario_type": row["scenario_type"],
                "detail": row["detail"], "w_D1": row["w_D1"], "w_D2": row["w_D2"], "w_D3": row["w_D3"],
                "standardization": row["standardization"], "dropped_dim": row["dropped_dim"],
                "short_name": name, "rank": int(row["rank"][i]), "score": float(row["score"][i]),
            })
    long = pd.DataFrame(long_rows)

    # 场景清单（不含省明细）
    scen = long.drop_duplicates("scenario_id")[
        ["scenario_id", "scenario_type", "detail", "w_D1", "w_D2", "w_D3", "standardization", "dropped_dim"]
    ].copy()
    stats = []
    for sid, g in long.groupby("scenario_id"):
        m = g.set_index("short_name")["rank"]
        rho = m.corr(pd.Series(base).reindex(m.index), method="spearman")
        shift = (m - pd.Series(base).reindex(m.index)).abs().max()
        top5 = set(m.nsmallest(5).index)
        base_top5 = set(pd.Series(base).nsmallest(5).index)
        stats.append({"scenario_id": sid, "spearman_vs_base": round(float(rho), 4),
                      "max_rank_shift": int(shift), "top5_overlap": len(top5 & base_top5),
                      "top5_members": "、".join(sorted(top5))})
    scen = scen.merge(pd.DataFrame(stats), on="scenario_id")
    scen.to_csv(OUT / "sensitivity_scenarios_deduplicated.csv", index=False, encoding="utf-8-sig")

    # ---------------- 按类别的名次区间 ----------------
    rows2 = []
    for name in df["short_name"]:
        sub = long[long["short_name"] == name]
        w = sub[sub["scenario_type"] == "权重网格"]["rank"]
        s = sub[sub["scenario_type"] == "标准化"]["rank"]
        d = sub[sub["scenario_type"] == "剔除维度"]["rank"]
        allr = sub["rank"]
        rows2.append({
            "short_name": name, "base_rank": base[name],
            "n_weight": len(w), "weight_min": int(w.min()), "weight_max": int(w.max()),
            "n_std": len(s), "std_min": int(s.min()), "std_max": int(s.max()),
            "n_drop": len(d), "drop_min": int(d.min()), "drop_max": int(d.max()),
            "n_all": len(allr), "all_min": int(allr.min()), "all_max": int(allr.max()),
            "weight_top5_freq": round(float((w <= 5).mean()), 4),
            "all_top5_freq": round(float((allr <= 5).mean()), 4),
            "all_top10_freq": round(float((allr <= 10).mean()), 4),
        })
    by_type = pd.DataFrame(rows2).sort_values("base_rank")
    by_type.to_csv(OUT / "sensitivity_by_type.csv", index=False, encoding="utf-8-sig")

    # ---------------- 结构对照 ----------------
    pairs = [("A", "浙江", "北京"), ("B", "广东", "宁夏")]
    prows = []
    for gid, a, b in pairs:
        for name in (a, b):
            r = df[df["short_name"] == name].iloc[0]
            prows.append({
                "group": gid, "province": name, "role": "甲" if name == a else "乙",
                "D1_raw": round(float(r["D1_raw"]), 4), "D2_raw": round(float(r["D2_raw"]), 4),
                "D3_raw": round(float(r["D3_raw"]), 4),
                "D1_z": round(float(r["D1_z"]), 2), "D2_z": round(float(r["D2_z"]), 2),
                "D3_z": round(float(r["D3_z"]), 2), "composite": round(float(r["composite"]), 2),
                "base_rank": int(r["base_rank"]),
            })
    cp = pd.DataFrame(prows)
    comp = cp.pivot(index="group", columns="province", values="composite")
    diffs = []
    for gid, a, b in pairs:
        ra = cp[(cp.group == gid) & (cp.province == a)].iloc[0]
        rb = cp[(cp.group == gid) & (cp.province == b)].iloc[0]
        d = {
            "group": gid, "province_a": a, "province_b": b,
            "composite_a": ra["composite"], "composite_b": rb["composite"],
            "composite_gap": round(abs(ra["composite"] - rb["composite"]), 2),
            "D1_z_a": ra["D1_z"], "D1_z_b": rb["D1_z"], "D1_gap": round(ra["D1_z"] - rb["D1_z"], 2),
            "D2_z_a": ra["D2_z"], "D2_z_b": rb["D2_z"], "D2_gap": round(ra["D2_z"] - rb["D2_z"], 2),
            "D3_z_a": ra["D3_z"], "D3_z_b": rb["D3_z"], "D3_gap": round(ra["D3_z"] - rb["D3_z"], 2),
            "L1_technical": round(sum(abs(ra[f"{x}_z"] - rb[f"{x}_z"]) for x in ["D1", "D2", "D3"]), 1),
        }
        diffs.append(d)
    diff_df = pd.DataFrame(diffs)
    cp = cp.merge(diff_df[["group", "composite_gap", "L1_technical"]], on="group")
    cp.to_csv(OUT / "contrast_pairs.csv", index=False, encoding="utf-8-sig")

    # ---------------- 关键数字 ----------------
    def pv(name):
        r = df[df["short_name"] == name].iloc[0]
        b = by_type[by_type["short_name"] == name].iloc[0]
        return {
            "base_rank": int(r["base_rank"]), "composite": round(float(r["composite"]), 2),
            "D1_z": round(float(r["D1_z"]), 2), "D2_z": round(float(r["D2_z"]), 2),
            "D3_z": round(float(r["D3_z"]), 2),
            "D1_raw": round(float(r["D1_raw"]), 2), "D2_raw": round(float(r["D2_raw"]), 2),
            "D3_raw": round(float(r["D3_raw"]), 2),
            "weight_range": [int(b["weight_min"]), int(b["weight_max"])],
            "std_range": [int(b["std_min"]), int(b["std_max"])],
            "drop_range": [int(b["drop_min"]), int(b["drop_max"])],
            "all_range": [int(b["all_min"]), int(b["all_max"])],
            "weight_top5_freq": float(b["weight_top5_freq"]),
            "all_top5_freq": float(b["all_top5_freq"]),
        }

    special = {}
    for sid, label in [("W07", "D1=0.50"), ("W13", "D2=0.50"), ("W31", "D3=0.50")]:
        g = long[long["scenario_id"] == sid]
        if len(g) == 0:
            continue
    # 单列三个 50% 方案（非网格）——直接计算
    for label, w in [("D1_50", {"D1": .5, "D2": .25, "D3": .25}),
                     ("D2_50", {"D1": .25, "D2": .5, "D3": .25}),
                     ("D3_50", {"D1": .25, "D2": .25, "D3": .5})]:
        s = sum(df[f"{d}_z"] * w[d] for d in w)
        r = ranks(s)
        special[label] = int(r[df["short_name"] == "广东"].iloc[0])

    # 剔除维度下广东的名次
    drop_gd = {}
    for d in ["D1", "D2", "D3"]:
        s = sum(df[f"{x}_z"] * (0 if x == d else 0.5) for x in ["D1", "D2", "D3"])
        r = ranks(s)
        drop_gd[d] = int(r[df["short_name"] == "广东"].iloc[0])

    region = []
    for reg in ["东部", "中部", "西部", "东北"]:
        x = df[df["region_4"] == reg]["composite"]
        region.append({"region": reg, "n": int(len(x)), "mean": round(float(x.mean()), 2),
                       "median": round(float(x.median()), 2), "min": round(float(x.min()), 2),
                       "max": round(float(x.max()), 2), "range": round(float(x.max() - x.min()), 2),
                       "cv_pct": round(float(x.std(ddof=0) / x.mean() * 100), 2),
                       "rank_span": f"{int(df[df.region_4==reg]['base_rank'].min())}—{int(df[df.region_4==reg]['base_rank'].max())}"})

    key = {
        "scenario_counts": {"base": 1, "weight_grid": 36, "standardization": 2, "dimension_drop": 3, "total_unique": 42},
        "special_weight_schemes": special,
        "guangdong_drop": drop_gd,
        "provinces": {n: pv(n) for n in ["浙江", "北京", "上海", "海南", "江苏", "重庆", "广东", "宁夏", "青海", "新疆", "河北", "吉林"]},
        "contrast": diff_df.to_dict("records"),
        "region": region,
        "cv_order": sorted(region, key=lambda r: -r["cv_pct"]),
        "scenario_stats": {
            "min_spearman": round(float(scen["spearman_vs_base"].min()), 4),
            "mean_spearman": round(float(scen["spearman_vs_base"].mean()), 4),
            "max_shift_weight": int(scen[scen.scenario_type == "权重网格"]["max_rank_shift"].max()),
            "max_shift_drop": int(scen[scen.scenario_type == "剔除维度"]["max_rank_shift"].max()),
        },
    }
    (OUT / "stage8_key_numbers.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")

    pd.set_option("display.width", 220)
    print(scen[["scenario_id", "scenario_type", "detail", "spearman_vs_base", "max_rank_shift", "top5_overlap"]].head(8).to_string(index=False))
    print("\n场景类型计数:", scen["scenario_type"].value_counts().to_dict())
    print("\n按类型区间（前10 + 敏感省）:")
    print(by_type[by_type.short_name.isin(["浙江", "北京", "上海", "海南", "江苏", "重庆", "广东", "宁夏", "青海", "新疆"])]
          [["short_name", "base_rank", "weight_min", "weight_max", "std_min", "std_max", "drop_min", "drop_max", "all_min", "all_max"]].to_string(index=False))
    print("\n广东单列方案:", special, "剔除维度:", drop_gd)
    print("\n结构对照:")
    print(cp.to_string(index=False))
    print("\n文件:", sorted(p.name for p in OUT.glob("*")))


if __name__ == "__main__":
    main()
