"""以已核候选值和专项检索日志形成第二阶段研究决策材料。"""
from pathlib import Path
import json, sqlite3, hashlib
import pandas as pd
from pipeline import dump_csv
ROOT=Path(__file__).resolve().parents[1]
def write(name,text):(ROOT/'reports'/name).write_text(text,encoding='utf-8')
def main():
    con=sqlite3.connect(ROOT/'data/digital_china.sqlite');con.row_factory=sqlite3.Row
    obs=pd.read_csv(ROOT/'data/processed/observations_long.csv',dtype={'province_code':str,'period':str})
    prov=pd.read_csv(ROOT/'metadata/provinces.csv',dtype={'province_code':str})
    facts=json.loads((ROOT/'data/processed/stage2/analysis_facts.json').read_text(encoding='utf-8'))
    gov='THU_GOV_G202_SCORE'
    g=obs[obs.indicator_id==gov].merge(prov,on='province_code')
    independent=json.loads((ROOT/'work/stage2_government/independent_score_check.json').read_text(encoding='utf-8'))
    independent_rows=[dict(province=r.short_name,source_value=r.numeric_value,independently_read=independent[r.short_name],match=abs(r.numeric_value-independent[r.short_name])<1e-10) for r in g.itertuples()]
    assert len(g)==31 and all(r['match'] for r in independent_rows)
    dump_csv('reports/stage2_government_independent_check.csv',independent_rows)
    g.sort_values('display_order').to_csv(ROOT/'data/processed/stage2/government_scores_report2025_window_unconfirmed.csv',index=False,encoding='utf-8-sig')
    rows=[]
    # B包含可作有价值代理但尚不能直接冒称原本的广义数字经济维度。
    specs=[
      ('D1','NBS_ECOM_SHARE','2024','B','核心候选（需批准概念调整）','优先；仅调查企业交易数字应用，不是数字经济规模；分子不得重复计分。'),
      ('D1','NBS_ICT_LEGAL_SHARE','2024','B','备选/解释','同表行业组织结构，法人单位非企业/产出；不含数字制造、各行业内部数字化。'),
      ('D1','NBS_COMP100','2024','B','替补','同调查企业每百人计算机配置，不能解释为居民数字技能；与电商共享样本。'),
      ('D2','BB_ACCOUNTS_PER100','2024','A','核心候选（待负责人审定）','同版年末原值/年末人口；账户配置强度，非千兆质量、居民去重普及率或地理覆盖。'),
      ('D2','NBS_BB_PORTS_YEAR_END','2024','B','供给解释/备选原料','31省端口数量完整；原量体量效应强；可另拟人口强度，不与账户密度默认同时赋权。'),
      ('D3',gov,'report_2025_window_unconfirmed','B','连续分数候选/待时间核验','31省同图、精确数字；实际调查窗口和S07版本对应未证实，不能直接并入2024。'),
      ('D3','gov_online_category','2024-10','B','2024分档展示','31省类别完整；9月上旬至10月上旬调查；不取中值、不计算档级均分。'),
      ('D3','gov_service_category','2025','B','2025补充展示','31省档级完整，2025年调查；不能映射2024分数。')]
    inds={r['indicator_id']:dict(r) for r in con.execute('SELECT * FROM indicators')}
    for dim,iid,period,level,use,note in specs:
        d=obs[(obs.indicator_id==iid)&(obs.period==period)]
        covered=set(d[d.numeric_value.notna()|d.category_value.notna()].province_code)
        sources=';'.join(sorted(d.source_id.unique()))
        rows.append(dict(dimension=dim,indicator_id=iid,indicator_name=inds[iid]['indicator_name'],period=period,numeric_count=d[d.numeric_value.notna()].province_code.nunique(),category_count=d[d.category_value.notna()].province_code.nunique(),missing_provinces='、'.join(prov[~prov.province_code.isin(covered)].short_name) or '无',unit=inds[iid]['unit'],value_type=inds[iid]['value_type'],source_ids=sources,source_locations='；'.join(d.source_page_or_table.unique()) if len(d.source_page_or_table.unique())<4 else '见逐值表（原始字段与表页完整保留）',admission_level=level,recommended_use=use,limitation=note))
    for dim,iid,name,period,reason in [('D1','CORE_DIGITAL_GDP_SHARE','数字经济核心产业增加值/GDP','2024','全国值已取得，未取得统一31省分表，不拼省新闻。'),('D2','BB_1000M_YEAR_END','年末千兆宽带用户数/占比原料','2024','未取得31省年末千兆列；不可用5月外推。'),('D2','BTS_5G','年末5G基站数','2024','未取得31省5G列；全部移动基站不等于5G。'),('D2','BB_1000M_SHARE','千兆宽带用户占比','2024-05','31省真实月末值；与年末账户密度测量含义不同，不作增长对比。')]:
        d=obs[(obs.indicator_id==iid)&(obs.period==period)]
        rows.append(dict(dimension=dim,indicator_id=iid,indicator_name=name,period=period,numeric_count=d.numeric_value.notna().sum(),category_count=0,missing_provinces='无' if len(d)==31 else '全部31省',unit=inds.get(iid,{}).get('unit',''),value_type=inds.get(iid,{}).get('value_type',''),source_ids=';'.join(d.source_id.unique()),source_locations='见来源检索日志',admission_level='B' if len(d)==31 else 'C',recommended_use='独立月度展示' if len(d)==31 else '暂不采用',limitation=reason))
    dump_csv('reports/stage2_core_availability.csv',rows)
    lines=['# 第二版候选指标推荐表','', '以下A/B/C是准入审查建议，均未批准进入最终指数。A=数据和口径条件可提交核心审核；B=代理概念、时间或类别限制，只可展示/待复核；C=未取得合格原值。D1按原“数字经济规模”定义仍属窄代理，因此暂列B；研究负责人批准收窄为企业数字应用后再复核。','', '|维度|候选|统计期|数值/31|档级/31|等级|推荐用途|优点及局限|','|---|---|---|---:|---:|---|---|---|']
    for r in rows[:8]:lines.append(f'|{r["dimension"]}|{r["indicator_id"]} {r["indicator_name"]}|{r["period"]}|{r["numeric_count"]}|{r["category_count"]}|{r["admission_level"]}|{r["recommended_use"]}|{r["limitation"]}|')
    lines += ['', '每维最多3项推荐，其中D2只2项。不得把这些全放进总分：电商比例与分子企业数、原数量与人口强度、数字政府总分与其四分项均避免重复。现成BIMSA总指数仍只作外部对照；本轮未做PCA、熵权或任何最终赋权。','', '完整覆盖/缺口/来源定位见stage2_core_availability.csv；全部候选×期间×31省状态见coverage_matrix.csv。未取得的核心产业产出、年末千兆、5G均列C，并未制造占位成功。']
    write('stage2_indicator_shortlist.md','\n'.join(lines)+'\n')
    logs=[]
    for folder in ['stage2_government','stage2_infrastructure','stage2_economy']:
        path=ROOT/'work'/folder/'search_log.json'
        if path.exists():
            for row in json.loads(path.read_text(encoding='utf-8-sig')):logs.append(dict(task=folder,**row))
    dump_csv('reports/stage2_source_log.csv',logs)
    l=['# 第二阶段检索台账','',f'本轮检索记录{len(logs)}条。下列是原发布机构、原报告或实际定位页，不以搜索引擎结果页替代来源。已取得/只预览/访问失败/无省级明细分别保留。失败HTTP文件仅为失败证据，未作为观察值源。','']
    for row in logs:
        url=row.get('source_url',row.get('url',''))
        title=row.get('title','未标标题');sid=row.get('source_id','未登记为数值来源')
        result=row.get('result',row.get('finding',row.get('status','')))
        location=row.get('source_page_or_table',row.get('table_or_page',row.get('location','未取得数值表')))
        l += [f'## {sid}｜{title}',f'- 发布机构：{row.get("publisher","见原页")}；统计期：{row.get("coverage_period","未核准")}；发布日期：{row.get("published_at") or "未核准"}。',f'- [原始入口]({url})；表/页：{location}。',f'- 结果：{result}',f'- 后续：{row.get("next_action","见专项调查报告；无自动补缺或计分。")}','']
    l += ['## 原文件与获取状态','', '47个累计登记来源详见metadata/sources.csv。22个本轮新增登记来源包含元数据、政策及失败入口，不代表22份可计分数表。原PDF/JPG、提取文本、核验截图和SHA256在work/stage2_*及sources.csv中。第一阶段的25源和1041条记录均保留。']
    write('stage2_source_log.md','\n'.join(l)+'\n')
    e=facts['region_ecommerce'];b=facts['region_infra']
    est='、'.join(f'{r["region_4"]}{r["mean"]:.2f}%' for r in sorted(e,key=lambda r:-r['mean']))
    bst='、'.join(f'{r["region_4"]}{r["mean"]:.2f}' for r in sorted(b,key=lambda r:-r['mean']))
    total=con.execute('SELECT COUNT(*) FROM observations').fetchone()[0]
    rawnew=len(obs[(obs.data_version=='stage2_source_archived_2026-11-09')&obs.is_derived.eq(0)])
    # 来源版本可能自带精细标签，新原值计数直接按本轮manifest核，避免重跑导入重复计数。
    rawnew=sum(len(json.loads((ROOT/'work'/f/'observations.json').read_text(encoding='utf-8'))) for f in ['stage2_government','stage2_infrastructure','stage2_economy'])
    newder=con.execute("SELECT COUNT(*) FROM observations WHERE data_version='stage2_derived_v1'").fetchone()[0]
    govsource=dict(con.execute("SELECT * FROM sources WHERE source_id='G202'").fetchone())
    summary=f'''# 第二阶段总报告

本轮新增3类可核数据，共{rawnew}条来源原值和{newder}条有输入ID的派生值。**D1有31省企业应用及行业组织结构代理，D2已补齐2024年末31省接入数量/人均账户配置，D3已取得31省精确连续分数但统计窗口仍未核准；2024年31省三维综合评分仍不满足完整准入条件。**

## 三维数据可得性决策

|维度|当前最优候选|统计期|连续值覆盖|可否提交评分审核|证据/主要边界|
|---|---|---|---:|---|---|
|D1|调查企业电商参与比例；新增信息服务行业法人占比备选|2024全年/年度覆盖|均31/31|有条件：先决定是否接受代理概念，当前B|年鉴16-39（E02）、1-5（E201）；不是数字经济规模或增加值|
|D2|每百人固定宽带账户数；端口数量作解释|2024年末|31/31|可提交A类核心候选审核，非自动批准|年鉴16-36（I203）及人口表2-5（A01）；账户配置非去重普及率/千兆质量|
|D3|清华团队数字政府发展指数，收录于北大《数字生态指数2025》|报告2025；实际窗口未确认|31/31|暂不能通过2024时间准入，B|G202 PDF97/印刷93图10-1有31个数字；PDF13只说“多数”分指数面向2024，章节未逐项明确|

相较第一阶段，D2不再只有5月数据，D3也不再是找不到31省精确总分；剩余卡点从“数值完整性”转为“评价期与版本对应”。不能因为已拿齐31个数字就把它们自动填入2024年度面板。

## 新取得资料、真实缺口与质量问题

- D2：表16-36的年末宽带用户和端口各31值，共62原值；分省合计与全国差分别0.2万户和0.5万个，均在31行舍入容差1.6以内。年末宽带账户/人口×100另存31个派生值。没有取得年末千兆列或31省5G列，不把移动总基站冒称5G。
- D1：表1-5的全部法人单位、信息传输软件IT服务业法人单位各31值，共62原值，全国合计分别37,782,288和1,896,012，逐省加总精确一致；派生31个行业组织比重。法人单位不是企业数、增加值或就业；年度表未标月日，不虚构年末。
- D3：31个总分均来自原图顶部明确印刷标签，而非柱高估读，两次独立读数全部一致。来源是研究机构指数，底层权重/缺失处理细则与实际调查期仍未完全公开；未证明与S07预览是同一数据版本。保留period=report_2025_window_unconfirmed、起止为空，不混入2024面板。
- 未取得：统一31省数字经济核心产业增加值/GDP、年末千兆占比、年末5G，以及D3的明确实际窗口和完整方法。官方全国核心产业比重10.5%只作全国背景，不复制到省份。

## 已完成的四张分项图及可核事实

图表均有单位、样本、统计期、来源和公式，PNG为300dpi，另有矢量PDF。没有地图边界风险，也没有综合分数或三维榜单。

1. [2024调查企业电商比例](figures_stage2/01_ecommerce_share_2024.png)：北京23.29%，吉林7.69%；相差15.60个百分点。只反映调查企业。
2. [2024年末每百人宽带账户](figures_stage2/02_infrastructure_single_indicator.png)：账户含家庭和机构，不可解读为居民普及率，更不能由单项推断基础设施总体强弱。
3. [四大区域省份分布](figures_stage2/03_regional_distributions.png)：电商省均值为{est}；宽带账户密度省均值为{bst}户/百人。两项均值排序同为东、西、中、东北，但这不是稳健的统一发展次序：电商中位数为东13.51%、中12.23%、西11.40%、东北8.32%，中西顺序反转；宽带西中均值仅差约0.22户/百人。
4. [2024网上政府档级区域分布](figures_stage2/04_government_categories_2024.png)：全31省优秀13、良好14、中等4；东部优秀7/10、西部5/12、中部1/6、东北0/3。类别不转换得分，东北仅3省须谨慎解释。

电商东部内部极差14.75个百分点，北京/河北分别23.29%/8.53%，不能用区域均值抹平内部差异。两连续代理的Spearman相关系数为{facts['spearman_exploratory']:.3f}，只是省际描述，不作因果或严格同日结论。候选案例按两个单项名次差异提出广东、北京、天津、云南、新疆、宁夏，见case_candidates.csv；未确定最终典型省份。广东账户密度数值偏低也可能提示代理对家庭/机构、户规模的敏感性，不能据此称其数字基础设施整体落后。

## 最多三项研究决策

1. **D1定义**：是否接受“调查企业数字应用”为主、行业组织结构为备选；若坚持数字经济规模/产出，仍须继续补统一产出数据。
2. **D2定义**：是否接受年末每百人宽带账户配置作为核心候选；它与原拟千兆接入速率结构测量不同，端口作为解释或替补，勿默认堆叠计分。
3. **D3时间门槛**：是否继续通过原机构公开渠道确认G202实际窗口及S07版本对应；确认前维持路线A最终目标、按路线B分项展示，不做2024三维综合排名。

## 文件及关键原始证据

- 完整六份报告：本文件、stage2_government_findings.md、stage2_infrastructure_findings.md、stage2_economy_findings.md、stage2_indicator_shortlist.md、stage2_source_log.md。
- 数据：data/processed/stage2/new_values_31_provinces.csv逐省核对全部新值；government_scores_report2025_window_unconfirmed.csv单列政府分数；single_indicator_panel.csv与regional_*、case_candidates.csv为图表后台。
- 状态：stage2_core_availability.csv记录准入等级、31省连续/档级覆盖、精度类型与限制；coverage_matrix.csv为全候选矩阵；源、指标和观察长表已更新。
- 原始依据：[国家统计局年鉴16-36](https://www.stats.gov.cn/sj/ndsj/2025/html/C16-36.jpg)、[法人单位表1-5](https://www.stats.gov.cn/sj/ndsj/2025/html/C01-05.jpg)、[北大官网报告PDF]({govsource['source_url']})（PDF97/印刷93页）。全部有本地原件与hash，未绕过访问控制。
- 校验：stage2_validation_checks.csv核所有已用源hash、旧1041条保留、派生输入、外键及不提前评分；stage2_government_independent_check.csv逐省双读一致；全国加总文件在work/stage2_infrastructure和work/stage2_economy。

项目现有{con.execute('SELECT COUNT(*) FROM sources').fetchone()[0]}个登记来源、{con.execute('SELECT COUNT(*) FROM indicators').fetchone()[0]}个候选指标、{total}条观察记录（含派生），**这些计数不等于合格计分指标数**。第一阶段报告未覆盖改写，基线数据另存work/stage2_baseline。未做工程重构、GitHub发布、最终赋权、PCA/熵权、PPT或综合排名。
'''
    write('stage2_summary.md',summary)
    write('stage2_change_log.md','''# 第二阶段调整记录

1. 保留31省、2024优先与不提前综合计分的研究边界。
2. 通过国家统计局年鉴原表补齐年末宽带与端口；第一阶段5月数据保留新旧分期，不做跨期外推。
3. 新增行业法人单位结构代理，不冒称数字经济规模；当年统计覆盖不强改年末日期。
4. 新找到G202收录的清华数字政府31省连续精确标签，改变“未取得连续数值”状态；但实际窗口与S07版本对应未核，保持B类，单列未知期。
5. 两次独立读数一致；采用清晰原图而非web图形识别结果，防止安徽75.06等数字误读。
6. 四图为单项探索和分档区域计数。省份均值与合并分子分母比例分别存，不将名次差当综合榜或因果证据。
7. 研究者仍须决定D1/D2代理含义与D3时间门槛，未批准最终指标/权重。来源、指标、观察长表已补充，第一阶段报告与基线保留。
''')
    con.close();print(json.dumps({'core_availability_rows':len(rows),'source_log_rows':len(logs),'independent_score_matches':len(independent_rows),'summary_written':True},ensure_ascii=False))
if __name__=='__main__':main()
