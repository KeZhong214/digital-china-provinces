"""第五阶段底表构建：地图分级、区域均值/中位数、散点象限、档级计数、旭日层级与关键数字。

只使用阶段2/3已审核的31省面板，不新增检索、不合成综合分。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/processed"
OUT = SRC / "stage5"
OUT.mkdir(parents=True, exist_ok=True)

REGION_ORDER = ["东部", "中部", "西部", "东北"]
TIER_ORDER = ["优秀", "良好", "中等"]
MAP_RAMP = ["#EEF2F1", "#CFDEDA", "#9DBAB7", "#648F92", "#2E6373"]


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


def write(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False, encoding="utf-8-sig")


def main() -> None:
    panel = read(SRC / "stage3/indicator_review_panel_2024.csv")
    single = read(SRC / "stage2/single_indicator_panel.csv")
    df = panel.merge(single[["province_code", "gov_category_2024"]], on="province_code", how="left")
    df["d1"] = df["ecommerce"].astype(float)
    df["d2"] = df["accounts"].astype(float)
    df["d1_rank"] = df["d1"].rank(ascending=False, method="min").astype(int)
    df["d2_rank"] = df["d2"].rank(ascending=False, method="min").astype(int)
    assert len(df) == 31

    # ---------------- 地图面板 + 五分位分级 ----------------
    class_summary = []
    for metric, rank_col, label in [
        ("d1", "d1_rank", "D1 调查企业交易型数字应用（%）"),
        ("d2", "d2_rank", "D2 固定宽带接入配置（户/百人）"),
    ]:
        values = df[metric]
        # 五等分断点：取相邻两省中点，避免断点与观测值重合导致分级不均
        s = np.sort(values.values)
        n = len(s)
        breaks = []
        for k in range(1, 5):
            pos = k * n / 5.0          # 6.2, 12.4, 18.6, 24.8
            i = int(np.floor(pos))     # 6, 12, 18, 24
            breaks.append(round(float((s[i - 1] + s[i]) / 2), 4))
        assert len(set(breaks)) == 4, breaks

        def cls(v: float) -> int:
            for i, b in enumerate(breaks):
                if v < b:
                    return i
            return 4

        m = df[["province_code", "province_name", "short_name", "region_4"]].copy()
        m["value"] = df[metric].round(4)
        m["rank"] = df[rank_col]
        m["class_id"] = [cls(v) for v in df[metric]]
        write(m.sort_values("rank"), f"map_panel_{metric}.csv")

        rows = []
        for i in range(5):
            sub = m[m["class_id"] == i]
            rows.append(
                {
                    "class_id": i,
                    "lower": "" if i == 0 else breaks[i - 1],
                    "upper": "" if i == 4 else breaks[i],
                    "break_value": "" if i == 4 else breaks[i],
                    "color": MAP_RAMP[i],
                    "n": len(sub),
                    "provinces": "、".join(sub["short_name"]),
                }
            )
        write(pd.DataFrame(rows), f"map_classes_{metric}.csv")
        class_summary.append(
            {
                "metric": metric,
                "label": label,
                "breaks": breaks,
                "class_counts": [len(m[m["class_id"] == i]) for i in range(5)],
                "classes": rows,
            }
        )

    # ---------------- 区域均值/中位数 ----------------
    reg_rows = []
    for metric in ["d1", "d2"]:
        for region in REGION_ORDER:
            s = df.loc[df["region_4"] == region, metric]
            reg_rows.append(
                {
                    "metric": metric,
                    "region": region,
                    "n": len(s),
                    "mean": round(float(s.mean()), 4),
                    "median": round(float(s.median()), 4),
                    "mean_minus_median": round(float(s.mean() - s.median()), 4),
                    "min": round(float(s.min()), 4),
                    "max": round(float(s.max()), 4),
                }
            )
    reg = pd.DataFrame(reg_rows)
    for metric in ["d1", "d2"]:
        mask = reg["metric"] == metric
        reg.loc[mask, "mean_rank"] = reg.loc[mask, "mean"].rank(ascending=False, method="min").astype(int)
        reg.loc[mask, "median_rank"] = reg.loc[mask, "median"].rank(ascending=False, method="min").astype(int)
    write(reg, "regional_mean_median.csv")

    # ---------------- 散点（均值参考线 + 象限） ----------------
    xm, ym = float(df["d2"].mean()), float(df["d1"].mean())
    sc = df[["short_name", "province_name", "region_4", "d1", "d2", "d1_rank", "d2_rank",
             "gov_category_2024"]].copy()
    sc = sc.rename(columns={"d1": "ecommerce_pct", "d2": "accounts_per100",
                            "gov_category_2024": "gov_tier"})
    sc["x_side"] = np.where(sc["accounts_per100"] >= xm, "配置高于均值", "配置低于均值")
    sc["y_side"] = np.where(sc["ecommerce_pct"] >= ym, "应用高于均值", "应用低于均值")
    sc["quadrant"] = sc["x_side"] + "·" + sc["y_side"]
    for c in ["ecommerce_pct", "accounts_per100"]:
        sc[c] = sc[c].round(4)
    write(sc.sort_values("d1_rank"), "scatter_quadrant_panel.csv")

    quad_counts = sc.groupby("quadrant").size().reset_index(name="n")
    write(quad_counts, "scatter_quadrant_counts.csv")

    # ---------------- 政府档级 ----------------
    tier = (
        df.groupby(["region_4", "gov_category_2024"]).size().unstack(fill_value=0)
        .reindex(REGION_ORDER)
        .reindex(columns=TIER_ORDER, fill_value=0)
    )
    tier_rows = []
    for region, row in tier.iterrows():
        total = int(row.sum())
        tier_rows.append(
            {
                "region": region,
                "n": total,
                "excellent": int(row["优秀"]),
                "good": int(row["良好"]),
                "medium": int(row["中等"]),
                "excellent_pct": round(row["优秀"] / total * 100, 2),
                "good_pct": round(row["良好"] / total * 100, 2),
                "medium_pct": round(row["中等"] / total * 100, 2),
            }
        )
    nat = {
        "region": "全国31省",
        "n": int(tier.values.sum()),
        "excellent": int(tier["优秀"].sum()),
        "good": int(tier["良好"].sum()),
        "medium": int(tier["中等"].sum()),
    }
    for k in ["excellent", "good", "medium"]:
        nat[f"{k}_pct"] = round(nat[k] / nat["n"] * 100, 2)
    write(pd.DataFrame(tier_rows + [nat]), "gov_category_counts.csv")

    # ---------------- 旭日层级（区域→省） ----------------
    sun = df[["short_name", "province_name", "region_4"]].copy()
    sun["region_order"] = sun["region_4"].map({r: i for i, r in enumerate(REGION_ORDER)})
    sun = sun.sort_values(["region_order", "short_name"]).reset_index(drop=True)
    sun["d1"] = df.set_index("short_name").loc[sun["short_name"], "d1"].values.round(4)
    sun["d1_rank"] = df.set_index("short_name").loc[sun["short_name"], "d1_rank"].values
    sun["class_id"] = df.set_index("short_name").loc[sun["short_name"], "d1"].values
    breaks_d1 = [r["break_value"] for r in class_summary[0]["classes"] if r["break_value"] != ""]
    sun["class_id"] = [sum(v >= b for b in breaks_d1) for v in sun["d1"]]
    write(sun, "sunburst_hierarchy.csv")

    # ---------------- 底图清单 ----------------
    geo_path = ROOT / "data/raw/geo/china_provinces_100000_full.json"
    raw = geo_path.read_bytes()
    manifest = {
        "file": str(geo_path.relative_to(ROOT)).replace("\\", "/"),
        "source": "阿里云 DataV 全国省级边界 GeoJSON（https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json）",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "features": 35,
        "note": "34个省级区划 + 1个九段线要素（adcode=100000_JD）；仅作示意底图，不作测绘用途；研究范围为31个省级行政区，不含港澳台。",
        "projection": "Albers 等积圆锥（标准纬线25°N/47°N，中央经线105°E，原点35°N）",
    }
    (OUT / "basemap_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------- 关键数字 ----------------
    s4 = json.loads((SRC / "stage4/stage4_key_numbers.json").read_text(encoding="utf-8"))
    key = {
        "meta": {
            "stage": "stage5",
            "route": "方案B：D1/D2连续分项 + D3档级分类 + 案例；不合成三维总分",
            "route_statement": "基于公开数据的31省数字化发展分项画像研究",
            "n_provinces": 31,
            "region_rule": "东部10、中部6、西部12、东北3（本研究固定口径，不含港澳台）",
        },
        "descriptive": s4["descriptive"],
        "national": s4["national"],
        "region_orders": {
            "d1_mean_order": reg[reg.metric == "d1"].sort_values("mean", ascending=False)["region"].tolist(),
            "d1_median_order": reg[reg.metric == "d1"].sort_values("median", ascending=False)["region"].tolist(),
            "d2_mean_order": reg[reg.metric == "d2"].sort_values("mean", ascending=False)["region"].tolist(),
            "d2_median_order": reg[reg.metric == "d2"].sort_values("median", ascending=False)["region"].tolist(),
        },
        "regional": reg.to_dict("records"),
        "map_classes": class_summary,
        "quadrant": {
            "x_mean": round(xm, 4),
            "y_mean": round(ym, 4),
            "counts": quad_counts.to_dict("records"),
        },
        "cases": s4["cases"],
        "rank_gap": s4["rank_gap"],
        "correlation": s4["correlation"],
        "government_tiers": s4["government_tiers"],
        "fragility": s4["fragility"],
        "claims": {
            "d1_central_west": (
                "中西部整体接近；等权均值西部略高、中位数中部略高，且西部均值受个别省份拉动，"
                "排序不稳健，不宜下“谁更高”的定论。"
            ),
            "northeast": (
                "在本研究采用的三个分项中整体相对靠后；但东北仅3省，样本小，"
                "只应理解为指标体系内的相对位置，不能外推为数字化各方面全面落后。"
            ),
        },
    }
    (OUT / "stage5_key_numbers.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---------------- 控制台核对 ----------------
    for cs in class_summary:
        print(cs["metric"], "breaks", cs["breaks"], "counts", cs["class_counts"])
    print(reg[["metric", "region", "n", "mean", "median", "mean_rank", "median_rank"]].to_string(index=False))
    print(quad_counts.to_string(index=False))
    print("files:", sorted(p.name for p in OUT.glob("*")))


if __name__ == "__main__":
    main()
