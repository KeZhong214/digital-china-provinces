"""第六阶段底表：省份编号（地图用）、档级矩阵布局、关键数字。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
S3 = ROOT / "data/processed/stage3"
S5 = ROOT / "data/processed/stage5"
OUT = ROOT / "data/processed/stage6"
OUT.mkdir(parents=True, exist_ok=True)

REGION_ORDER = ["东部", "中部", "西部", "东北"]
TIER_ORDER = ["优秀", "良好", "中等"]


def read(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, encoding="utf-8-sig")


def main() -> None:
    panel = read(S3 / "indicator_review_panel_2024.csv")
    single = read(ROOT / "data/processed/stage2/single_indicator_panel.csv")
    df = panel.merge(single[["province_code", "gov_category_2024"]], on="province_code", how="left")
    df = df.rename(columns={"ecommerce": "d1", "accounts": "d2", "gov_category_2024": "tier"})
    df["d1_rank"] = df["d1"].rank(ascending=False, method="min").astype(int)
    df["d2_rank"] = df["d2"].rank(ascending=False, method="min").astype(int)

    # 编号：按区域分组 + 行政代码顺序（不表示名次）
    df["region_order"] = df["region_4"].map({r: i for i, r in enumerate(REGION_ORDER)})
    df = df.sort_values(["region_order", "province_code"]).reset_index(drop=True)
    df["map_no"] = np.arange(1, 32)

    key_provs = {"北京", "河北", "广东", "宁夏", "重庆"}
    out = df[
        ["map_no", "short_name", "province_name", "region_4", "d1", "d1_rank", "d2", "d2_rank", "tier"]
    ].copy()
    out["is_key"] = out["short_name"].isin(key_provs)
    out["d1"] = out["d1"].round(4)
    out["d2"] = out["d2"].round(4)
    out.to_csv(OUT / "province_numbering.csv", index=False, encoding="utf-8-sig")

    # 档级矩阵布局：区域行 + 行内列号
    rows = []
    for region in REGION_ORDER:
        sub = df[df["region_4"] == region].sort_values("province_code")
        for i, (_, r) in enumerate(sub.iterrows(), start=1):
            rows.append(
                {
                    "region": region,
                    "col": i,
                    "map_no": int(r["map_no"]),
                    "short_name": r["short_name"],
                    "tier": r["tier"],
                    "d1": round(float(r["d1"]), 4),
                }
            )
    matrix = pd.DataFrame(rows)
    matrix.to_csv(OUT / "gov_matrix_layout.csv", index=False, encoding="utf-8-sig")

    # 关键数字：在 stage5 基础上补充编号与矩阵摘要
    key = json.loads((S5 / "stage5_key_numbers.json").read_text(encoding="utf-8"))
    key["meta"]["stage"] = "stage6"
    key["meta"]["note"] = (
        "样本为中国内地31个省级行政区；港澳台不纳入统计，但地图保留中国台湾省及完整版图要素。"
    )
    key["numbering"] = {
        "rule": "按区域分组（东部1-10、中部11-16、西部17-28、东北29-31），组内按行政代码顺序；编号仅为标识，不代表名次。",
        "provinces": out[["map_no", "short_name", "region_4"]].to_dict("records"),
        "key_provinces": sorted(key_provs),
    }
    tier_counts = matrix.groupby(["region", "tier"]).size().unstack(fill_value=0).reindex(REGION_ORDER)
    for c in TIER_ORDER:
        if c not in tier_counts:
            tier_counts[c] = 0
    key["gov_matrix"] = {
        "by_region": {
            r: {t: int(tier_counts.loc[r, t]) for t in TIER_ORDER} | {"n": int(tier_counts.loc[r].sum())}
            for r in REGION_ORDER
        },
        "total": {t: int(tier_counts[t].sum()) for t in TIER_ORDER},
    }
    (OUT / "stage6_key_numbers.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")

    print(out[["map_no", "short_name", "region_4", "d1", "d2", "tier"]].to_string(index=False))
    print("\nfiles:", sorted(p.name for p in OUT.glob("*")))


if __name__ == "__main__":
    main()
