# 第六阶段图表索引（终版）

> 三层结构：**主图（7 组，必须进 PPT）** / **辅图（备选）** / **附录图**。
> 全部主图位于 `reports/figures_stage6/`（PNG 300dpi + PDF）；底表在 `data/processed/stage5/`、`data/processed/stage6/`；规范见 `figure_style_guide_final.md`。
> 统一口径：D1＝调查企业交易型数字应用（2024全年，%）；D2＝固定宽带接入配置（2024年末，户/百人）；D3＝2024年网上政府发展档级（2024年9—10月）。三项未合成综合分；统计对象为中国内地31省，港澳台未纳入样本。

---

## 一、主图（7 组 / 9 个文件）

| 编号 | 文件 | 一句话作用 | 回答的问题 | 对应结论 |
|---|---|---|---|---|
| 主图1 | `map_d1_ecommerce_final.png/.pdf` | D1 全国空间格局（编号地图+对照表） | 哪些省更高/更低？ | 结论1 |
| 主图2 | `map_d2_accounts_final.png/.pdf` | D2 全国空间格局（编号地图+对照表） | 哪些省更高/更低？ | 结论1 |
| 主图3 | `regional_mean_median_final.png/.pdf` | 四大区域均值/中位数/名次 | 区域差异是否稳定？ | 结论2 |
| 主图4 | `scatter_d1_d2_final.png/.pdf` | 两维散点 + 四组计数 | 两个维度是否同步？ | 结论3 |
| 主图5 | `gov_category_matrix_final.png/.pdf` | 31省档级矩阵 | 档级如何分布？ | 结论1/2 |
| 主图6 | `sunburst_region_province_main.png/.pdf` | 区域—省份层级结构 | 整体结构如何？ | 结构总览 |
| 主图7A | `case_card_beijing_hebei_final.png/.pdf` | 京冀左右对照卡 | 内部差异如何落到实践？ | 结论2/3 |
| 主图7B | `case_card_ningxia_final.png/.pdf` | 宁夏案例卡 | 西部是否有不同路径？ | 结论3 |
| 主图7C | `case_card_guangdong_final.png/.pdf` | 广东方法警示卡（备用） | 单一指标能否定强弱？ | 结论3（方法） |

### 主图1　企业数字交易应用（编号地图 + 信息面板）

- **形式**：中国省级地图五分位着色 + 31省编号圆点 + 右侧省份对照表（编号/省份/区域/数值/档级）+ 表头摘要（最高/最低/极差）。
- **地图要素**：含中国台湾省（灰色 + 双行标注"中国台湾省／（未纳入样本）"，完整可见）、港澳灰色、南海诸岛小图（置于地图西南角，不遮挡台湾）、九段线。
- **关键省份**：北京、河北（陶红高亮）。
- **核心解读**：北京 23.29%（第1）；重庆 17.00%（第3）；天津第27、河北第28，两省低于西部全部12省；均值12.01%、极差15.60、CV 26.18%。
- **不能怎么讲**：不能说"北京数字经济全国第一"；不能把颜色深浅当综合水平；不能称其为数字经济规模。

### 主图2　固定宽带接入配置（编号地图 + 信息面板）

- **关键省份**：广东、宁夏。
- **核心解读**：海南58.14第1；宁夏53.14第5（西部最高）；广东39.51第31，但千兆以上占比29.78%；东北集中在26—30位。
- **图注强调**：指标为每百人固定宽带接入账户数，反映接入配置强度，不等于完整网络质量或居民实际普及率。

### 主图3　四大区域：均值与中位数

- **形式**：双面板哑铃图（实心圆＝均值、空心菱形＝中位数）+ 右侧"均值→中位数"名次列 + 提示带。
- **核心解读**：D1 均值"东＞西＞中＞东北"、中位数"东＞中＞西＞东北"；D2 两口径一致；东部 D1 极差14.75最大。

### 主图4　企业应用 × 接入配置（散点）

- **形式**：散点（区域分色）+ 均值虚线 + 右栏四组计数（9/7/7/8）。
- **核心解读**：Pearson 0.18、Spearman 0.27；平均名次差9.2位；北京(1/20)、广东(9/31)、宁夏(21/5)。

### 主图5　网上政府档级矩阵

- **形式**：四大区域各一行、31省各一格（0.52×0.52 in），颜色表示档级；右侧档级计数与各区域优秀率横条；底部核心发现提示带。
- **核心解读**：优秀13/良好14/中等4；东部70.0%、西部41.7%、中部16.7%、东北0%。
- **不能怎么讲**：不能换算成分数、不能排名、不能与其他指标相加。

### 主图6　区域—省份旭日图（结构总览）

- **形式**：内环四大区域（弧长按省数）、外环31省（等角）、颜色＝D1五分位；右侧说明"层级/作用/边界"与区域省数。
- **定位**：**结构示意图**，不承担排序与精确比较；图注写明"更具体的数值比较以地图、区域比较图和排序图为准"。

### 主图7　案例证据卡组

- **7A 京冀**：左右双卡 + 中间差距带（14.75 / 0.10）；417项一网通办、230项同事同标、1053项跨省通办。
- **7B 宁夏**：配置第5、应用第21；中卫7个项目、12.1万架；算电协同部署。
- **7C 广东**（备用）：D2第31，千兆占比29.78%；账户密度≠质量。

---

## 二、辅图（备选）

| 图 | 文件 | 用途 |
|---|---|---|
| 纯地图版 D1 | `figures_stage5/map_ecommerce_2024.png/.pdf` | 印刷稿、全屏展示、备用页 B6 |
| 纯地图版 D2 | `figures_stage5/map_accounts_2024.png/.pdf` | 同上 |
| D1 排名横条 | `figures_stage4/fig1_ecommerce_ranking.png/.pdf` | 需要密集排序信息时 |
| D2 排名横条 | `figures_stage4/fig2_broadband_ranking.png/.pdf` | 同上 |
| 名次差全表 | `data/processed/stage4/stage4_rank_gap_table.csv` | 答辩 B4 |
| 区域离散表 | `data/processed/stage5/regional_mean_median.csv` | 答辩 B3 |

---

## 三、附录图

| 图 | 文件 | 用途 |
|---|---|---|
| 旧版档级堆叠图 | `figures_stage5/gov_category_distribution.png/.pdf` | 备查，正式汇报用主图5 替代 |
| 旧版散点 | `figures_stage5/scatter_ecommerce_accounts_quadrant.png` | 备查 |
| 旧版旭日 | `figures_stage5/sunburst_region_province_structure.png` | 备查（主图6 为其升级版） |

---

## 四、图与底表对照

| 主图 | 主底表 | 辅助数据 |
|---|---|---|
| 主图1 | `stage5/map_panel_d1.csv`、`stage6/province_numbering.csv` | `stage5/map_classes_d1.csv` |
| 主图2 | `stage5/map_panel_d2.csv`、`stage6/province_numbering.csv` | `stage5/map_classes_d2.csv` |
| 主图3 | `stage5/regional_mean_median.csv` | — |
| 主图4 | `stage5/scatter_quadrant_panel.csv` | `stage5/scatter_quadrant_counts.csv` |
| 主图5 | `stage6/gov_matrix_layout.csv`、`stage6/stage6_key_numbers.json` | `stage4/fig5_government_tier_by_province.csv` |
| 主图6 | `stage6/province_numbering.csv` | `stage5/map_classes_d1.csv` |
| 主图7 | `stage6/stage6_key_numbers.json`（cases） | `stage3/case_evidence_figure_data.csv` |

---

## 五、主图与页面对应

| PPT 页 | 主图 |
|---|---|
| P4 | 主图1 |
| P5 | 主图2 |
| P6 | 主图3 |
| P7 | 主图4 |
| P8 | 主图5 |
| P9 | 主图6 |
| P10 | 主图7A（7B 口播/备用、7C 答辩） |
