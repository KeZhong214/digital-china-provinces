# 数字中国的省际图景：第一阶段数据项目

**第四阶段（研究整合与图表升级）已完成。** 研究路线锁定为方案B：31省分项画像 + 2024年网上政府档级展示 + 典型地区案例，**不合成三维综合总分、不生成综合排行榜**。优先阅读 `reports/stage4_summary.md`（含任务书五问回答与交付清单）、`reports/stage4_research_draft.md`（研究正文初稿）、`reports/figures_stage4/`（7张V1图，PNG 300dpi + PDF 矢量）；图表规范与索引见 `reports/figure_style_guide.md`、`reports/figure_index.md`；汇报大纲见 `reports/stage4_presentation_outline.md`；底表在 `data/processed/stage4/`。第四阶段脚本为 `scripts/stage4_build.py`、`stage4_style.py`、`stage4_figures.py`、`stage4_verify.py`（56项核对）。

第二阶段研究已增补：优先阅读 `reports/stage2_summary.md`、`reports/stage2_indicator_shortlist.md`、`reports/stage2_preanalysis.md`。全部新增值在 `data/processed/stage2/new_values_31_provinces.csv`，四张分项图及PDF在 `reports/figures_stage2/`。第一阶段报告保留作为历史基线。

第二阶段数据已并入现有候选库；下文的第一阶段 `pipeline.py build` 会重建第一阶段快照，不作为第二阶段入口。第二阶段研究脚本为 `stage2_update_data.py`、`stage2_preanalysis.py`、`stage2_reports.py`，未改变原表结构或进行工程重构。

本项目按用户任务书完成候选数据采集、逐值溯源、覆盖率及来源审计。**尚未批准最终指标、权重，也未计算自主综合排名或制作PPT。** 原始大纲保留在 `PROJECT_PLAN.md`，核验后的修正见 `reports/change_log.md`。

## 先看这几个文件

1. `reports/stage1_summary.md`：本阶段实际成果与尚缺什么。
2. `reports/indicator_selection_proposal.md`：三套下一步路线及其代价。
3. `reports/data_availability.md`：每指标、期间、31省覆盖与建议。
4. `reports/coverage_heatmap.png`：一眼看清哪里有数值、哪里只有档级、哪里未取得。
5. `reports/source_audit.md`、三个 `*_findings.md`：原表页码、重复计量、报告内部冲突和统计口径。

## 数据在哪

- `data/digital_china.sqlite`：包含sources、provinces、indicators、observations、missingness、derived_values、source_audit七张表。
- `data/processed/observations_long.csv`：一个地区×一个指标×一个统计期×一个来源版本一行；每值有来源、表/页、原字段及核验状态。
- `data/processed/candidate_panel_2024.csv`：仅2024全年/年末候选；不混入5月或10月截面。列名保留source_id及data_version。
- `data/processed/candidate_panel_2024_05.csv`：5月单独面板。
- `metadata/`：31省和全称映射、四区域、来源主表、指标字典、来源指标关联。
- `reports/coverage_matrix.csv`：所有已采年份和待取得候选的逐省状态；`missingness.csv`逐项记录缺口。
- `work/economy/`、`work/government/`、`work/auxiliary/`：下载原PDF/JPG、核验页图像、人工转录清单与JSON；都属于正式溯源附件，请保留。
- `data/raw/`：课程PDF、主任务归档、官方网页工具文本快照及失败响应。**403响应只证明访问失败，不是源表原文。**

> **本仓库不含 `work/` 目录。** 其中的原始 PDF、扫描页图像（共约141 MB）属第三方出版物，不随仓库分发；本地副本才是逐值溯源的最终凭据，`observations_long.csv` 等表中的表/页/字段记录即为指向它们的索引。克隆后运行第3步重建数据库不需要这些文件。

CSV使用UTF-8 BOM，可直接用Excel打开。数值型空值保持空白；档级只在category_value保存。6位省代码为地区连接键，不包含港澳台或兵团。省级代码来源核查范围及区域依据见来源审计。

## 本地复算：按顺序操作

以下命令会重新生成项目内数据库、processed、metadata和自动报告；不会覆盖Downloads原文件。若你已手动改动这些生成文件，请先备份；应优先修改有出处的转录清单或指标配置后重建。核验过的原始材料无需再次联网下载。

**第1步：进入项目目录。** 在PowerShell执行：

```powershell
cd 'D:\code\政治\digital-china-provinces'
```

成功标志：当前目录有README.md、scripts和data文件夹。

**第2步：准备Python依赖。** 当前已在本机Python 3.14.4通过运行。新环境建议Python 3.11或更新版本；安装依赖会占用环境空间，建议单独虚拟环境。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

成功标志：安装命令没有ERROR。后续命令中的`python`可替换为`.\.venv\Scripts\python.exe`。

**第3步：从归档与核验清单重建数据库。** 这一步是离线处理，不会重新爬取网站。

```powershell
python scripts/pipeline.py build
```

成功标志：打印来源/观察值条数和`PASS`；生成SQLite、长表、宽表及覆盖矩阵。人工转录清单已经逐图核验，重建可复现清单到数据库的过程；不声称自动OCR可替代人工核图。

**第4步：运行必要检查并生成覆盖图。** 检查用于防止省份错位、档级转数值、单位混用和断开溯源。

```powershell
python -m unittest discover -s tests -v
python scripts/coverage_figure.py
```

成功标志：测试结尾为`OK`，并生成`reports/coverage_heatmap.png`。检查明细见validation_checks.csv及validation_summary.md。

**可选补下载：** 只有需要重新尝试某个公开源时执行，可能遇到403或网站变动；脚本保存新hash版本，不覆盖旧归档，也不会自动把新文件判成已核验数据。

```powershell
python scripts/fetch_sources.py S05
```

成功标志：logs/fetch_log.csv有真实HTTP状态和内容hash。`downloaded_pending_content_review`仍需检查内容；`http_failed`表示失败，不能当数据导入。

## 研究约束

不插补、不以0填空、不把档级转连续分，不把不同年份和时点混成统一截面，不把既有指数改名为自建排名。每个派生值保存输入观察ID、公式与版本。S03附录分项与正文存在不一致，附录分项仅作审计；研究机构指数与官方原始统计明确区分。政府27省模型与4直辖市模型分别保存，不合并评分。

日期采用用户指定北京时间2026-11-09作为研究核验日；实际网络请求时间另记。标题所称“数字现代化”是待审核的研究操作定义，不是官方认证指数。
