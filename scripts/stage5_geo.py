"""中国省级地图底图与投影工具（第五阶段）。

底图：阿里云 DataV 全国省级边界 GeoJSON（data/raw/geo/china_provinces_100000_full.json，
sha256 见 data/processed/stage5/basemap_manifest.json）。仅作示意底图，不用于测绘用途。

不使用 geopandas/shapely：直接解析 GeoJSON 环，按 Albers 等积圆锥投影后交给
matplotlib 的 PolyCollection 绘制，避免新增依赖。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
GEO_PATH = ROOT / "data/raw/geo/china_provinces_100000_full.json"

# Albers 等积圆锥投影参数（中国常用）
PHI1, PHI2 = np.deg2rad(25.0), np.deg2rad(47.0)
LAM0, PHI0 = np.deg2rad(105.0), np.deg2rad(35.0)
R = 6371.0  # km

N_ = 0.5 * (np.sin(PHI1) + np.sin(PHI2))
C_ = np.cos(PHI1) ** 2 + 2 * N_ * np.sin(PHI1)
RHO0 = np.sqrt(C_ - 2 * N_ * np.sin(PHI0)) / N_


def albers(lon, lat):
    lam = np.deg2rad(np.asarray(lon, dtype=float))
    phi = np.deg2rad(np.asarray(lat, dtype=float))
    rho = np.sqrt(C_ - 2 * N_ * np.sin(phi)) / N_
    theta = N_ * (lam - LAM0)
    x = R * rho * np.sin(theta)
    y = R * (RHO0 - rho * np.cos(theta))
    return x, y


# adcode → 本项目短名（仅 31 个研究省）；其余为基底
ADCODE_SHORT = {
    110000: "北京", 120000: "天津", 130000: "河北", 140000: "山西", 150000: "内蒙古",
    210000: "辽宁", 220000: "吉林", 230000: "黑龙江", 310000: "上海", 320000: "江苏",
    330000: "浙江", 340000: "安徽", 350000: "福建", 360000: "江西", 370000: "山东",
    410000: "河南", 420000: "湖北", 430000: "湖南", 440000: "广东", 450000: "广西",
    460000: "海南", 500000: "重庆", 510000: "四川", 520000: "贵州", 530000: "云南",
    540000: "西藏", 610000: "陕西", 620000: "甘肃", 630000: "青海", 640000: "宁夏",
    650000: "新疆",
}
NON_STUDY = {710000: "台湾", 810000: "香港", 820000: "澳门"}


@dataclass
class Feature:
    adcode: int | str
    name: str
    short: str
    rings: list[np.ndarray]      # 投影后的环（N×2）
    center: tuple[float, float] | None  # 投影后中心


def _rings_from_geometry(geom: dict) -> list[list[list[float]]]:
    """返回 [ [ [lon,lat], ... ], ... ]（每个环一组坐标）。"""
    gtype, coords = geom["type"], geom["coordinates"]
    rings: list[list[list[float]]] = []
    if gtype == "Polygon":
        for ring in coords:
            rings.append(ring)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                rings.append(ring)
    else:
        raise ValueError(f"不支持的几何类型：{gtype}")
    return rings


class ChinaMap:
    def __init__(self, path: Path = GEO_PATH):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        self.features: list[Feature] = []
        self.jd_rings: list[np.ndarray] = []
        for f in data["features"]:
            props = f["properties"]
            adcode = props.get("adcode")
            name = props.get("name") or ""
            if str(adcode) == "100000_JD":
                self.jd_rings = [self._project_ring(r) for r in _rings_from_geometry(f["geometry"])]
                continue
            adcode_int = int(adcode)
            short = ADCODE_SHORT.get(adcode_int) or NON_STUDY.get(adcode_int) or name
            rings = [self._project_ring(r) for r in _rings_from_geometry(f["geometry"])]
            center = props.get("center")
            c_xy = albers(center[0], center[1]) if center else None
            self.features.append(Feature(adcode_int, name, short, rings, c_xy))

    @staticmethod
    def _project_ring(ring: list[list[float]]) -> np.ndarray:
        arr = np.asarray(ring, dtype=float)
        x, y = albers(arr[:, 0], arr[:, 1])
        return np.column_stack([x, y])

    def by_short(self) -> dict[str, Feature]:
        return {f.short: f for f in self.features}

    def bbox(self, include_non_study: bool = True, lat_min: float | None = None):
        xs, ys = [], []
        for f in self.features:
            if not include_non_study and f.adcode not in ADCODE_SHORT:
                continue
            for r in f.rings:
                xs.append(r[:, 0])
                ys.append(r[:, 1])
        x = np.concatenate(xs)
        y = np.concatenate(ys)
        return x.min(), x.max(), y.min(), y.max()

    def main_window(self, lat_min: float = 17.4, pad: float = 0.012):
        """主图窗口：取研究省 + 港澳台在 lat_min 以北的投影包络，四周留少量空白。"""
        y_cut = float(albers(110.0, lat_min)[1])
        xs, ys = [], []
        for f in self.features:
            for r in f.rings:
                m = r[:, 1] >= float(y_cut)
                if m.any():
                    xs.append(r[m, 0])
                    ys.append(r[m, 1])
        x = np.concatenate(xs)
        y = np.concatenate(ys)
        dx, dy = (x.max() - x.min()) * pad, (y.max() - y.min()) * pad
        return x.min() - dx, x.max() + dx, y.min() - dy, y.max() + dy


def window_from_lonlat(lon0, lon1, lat0, lat1):
    """把经纬度窗口转成投影坐标窗口（取四角与中点包络）。"""
    lons = np.linspace(lon0, lon1, 9)
    lats = np.linspace(lat0, lat1, 9)
    xx, yy = [], []
    for lo in lons:
        for la in lats:
            x, y = albers(lo, la)
            xx.append(float(x))
            yy.append(float(y))
    return min(xx), max(xx), min(yy), max(yy)
