# 第五阶段 PPT 就绪说明

> 用途：告诉做 PPT 的同学/老师，哪些内容可以**直接使用**，哪些是**备选**，以及拼版时要注意什么。
> 结论一句话：**主图 6 个文件 + 案例 2 张卡 + 11 页大纲 = 可以直接开始做 PPT；其余为备选与附录。**

---

## 一、可以直接进 PPT（Ready）

### 1. 页面文案（11 页）

| 页 | 采用文件 | 内容 | 就绪度 |
|---|---|---|---|
| P1 封面 | 大纲 P1 | 标题 + 副标题 | ✅ 可直接用 |
| P2 背景 | 大纲 P2 | 三行短句 | ✅ |
| P3 设计 | 大纲 P3 | 三维度小表 + “不合成总分” | ✅ |
| P4 图A | `map_ecommerce_2024_combo.png` | 地图 + 前五/后五 | ✅ |
| P5 图B | `map_accounts_2024_combo.png` | 地图 + 前五/后五 | ✅ |
| P6 图C | `regional_mean_median_comparison.png` | 均值/中位数/名次 | ✅ |
| P7 图D | `scatter_ecommerce_accounts_quadrant.png` | 散点 + 四组计数 | ✅ |
| P8 图E | `gov_category_distribution.png` | 档级堆叠条 | ✅ |
| P9 图F1 | `case_card_beijing_hebei.png` | 京冀对照卡 | ✅ |
| P10 图F2 | `case_card_ningxia.png` | 宁夏案例卡 | ✅ |
| P11 结论 | 大纲 P11 | 三条结论 + 局限 | ✅ |

每页的中心句、上屏文字、口播要点见 `stage5_presentation_outline_revised.md`；直接复制即可。

### 2. 图表文件（16:9，300dpi，白底）

- 图A、图B 组合版：`map_ecommerce_2024_combo.png`、`map_accounts_2024_combo.png`
- 图C：`regional_mean_median_comparison.png`
- 图D：`scatter_ecommerce_accounts_quadrant.png`
- 图E：`gov_category_distribution.png`
- 图F1、F2：`case_card_beijing_hebei.png`、`case_card_ningxia.png`

全部为 **3999×2250 px（16:9）**，可直接铺满 16:9 版心；PDF 版可无损缩放。

### 3. 页脚口径小字（建议每页保留一行）

| 页 | 页脚建议文字 |
|---|---|
| P4 | 调查企业电商参与比例（2024全年）；不是数字经济规模。 |
| P5 | 每百人固定宽带账户数（2024年末）；只测配置，不测网速与覆盖。 |
| P6 | 区域值为省内等权平均；东北仅3省。 |
| P7 | 描述性散点，不做因果推断。 |
| P8 | 2024年网上政府档级（9—10月）；分类展示，不转分数。 |
| P9/P10 | 政策事实为公开文件中的实施事实，不等于效果评估。 |

---

## 二、备选（Backup，视时间/追问使用）

| 内容 | 文件 | 何时用 |
|---|---|---|
| 广东方法警示卡 | `case_card_guangdong.png` | 被问“广东最后一名是不是指标有问题” |
| 纯地图版（无表格） | `map_ecommerce_2024.png`、`map_accounts_2024.png` | 需要全屏展示空间格局，或印刷稿 |
| 旭日图（层级结构） | `sunburst_region_province_structure.png` | 附录页，展示“区域—省份”结构；**不作结论** |
| 名次差全表 | `data/processed/stage4/stage4_rank_gap_table.csv` | “哪些省最不同步” |
| 区域离散表 | `data/processed/stage5/regional_mean_median.csv` | “区域内部差距到底多大” |

---

## 三、PPT 拼版建议

1. **版心**：16:9；主图铺满或占 60%–70%，文字放右侧或底部。
2. **字号**：页面标题 28–32pt、正文 16–18pt、页脚 10–11pt；**不要小于图表内 8pt 的图注**。
3. **颜色**：沿用图表墨黑/中灰/陶红三色；不要给页面加彩色底或渐变，避免与地图色阶冲突。
4. **案例卡**：图F1 可整页；图F2 单卡放左侧、右侧配一句口播要点；**不要把三张卡塞进一页**。
5. **动画**：只用“出现/淡入”；地图可分两步（先省界后着色）。
6. **导出**：以 PDF 或 300dpi PNG 插入，缩放 ≤150%。

---

## 四、已知待处理（制作 PPT 时注意）

| 事项 | 说明 | 处理建议 |
|---|---|---|
| 图A/图B 地图省名较小 | 投影后排观众可能看不清省名 | 讲解时用激光笔/放大局部；或改用纯地图版全屏展示 |
| 图A 北京/河北标注密集 | 华北区域文字略挤 | 讲 P4 时先指北京、再指河北，避免同时指点 |
| 图D 部分点未标注 | 31省中仅标注9省 | 属正常设计；被问及时切到名次差全表（备用） |
| 图E 东北比例易被放大 | n=3，33.3%/66.7% | 口播必须补一句“东北仅3省” |
| 旭日图已生成 | 附录图 `sunburst_region_province_structure.png` | 只放附录；讲解时强调“角度不表示数值”，不要用它做比较 |

---

## 五、制作顺序建议（约 2 小时）

1. **0:00–0:20** 建模板：16:9、白底、标题/正文/页脚三级字号、页脚口径文字。
2. **0:20–1:00** 铺 6 张主图（P4–P9），每页只写一句中心句。
3. **1:00–1:30** 补 P1–P3 与 P11 文字页（可直接复制大纲文案）。
4. **1:30–1:50** 加页脚口径小字与页码。
5. **1:50–2:00** 通读一遍：确认没有“排名/综合/第一”等越界词（除否定句），确认每条结论后都有一句边界。

---

## 六、交付清单核对

| 类别 | 文件 | 状态 |
|---|---|---|
| 文本 | `stage5_summary.md` | ✅ |
| 文本 | `stage5_research_draft_revised.md` | ✅ |
| 文本 | `stage5_key_findings_revised.md` | ✅ |
| 文本 | `stage5_presentation_outline_revised.md` | ✅ |
| 文本 | `stage5_storyline_map_revised.md` | ✅ |
| 规范 | `figure_style_guide_revised.md` | ✅ |
| 索引 | `figure_index_revised.md` | ✅ |
| 说明 | `stage5_chart_notes.md` | ✅ |
| 说明 | `stage5_ppt_ready_notes.md` | ✅ |
| 图表 | `reports/figures_stage5/`（10 张 × PNG/PDF） | ✅ |
| 底表 | `data/processed/stage5/`（11 个 CSV/JSON） | ✅ |
