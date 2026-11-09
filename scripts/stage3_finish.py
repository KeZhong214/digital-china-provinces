"""整理本轮研究证据、派生值、送审清单与总报告；不改原数据库。"""
from pathlib import Path
import json, hashlib, textwrap
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'data/processed/stage3';REPORT=ROOT/'reports'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def csv(df,path):df.to_csv(path,index=False,encoding='utf-8-sig')
def md(name,text):(REPORT/name).write_text(text,encoding='utf-8')
def main():
    facts=read(DATA/'analysis_facts.json');panel=pd.read_csv(DATA/'indicator_review_panel_2024.csv',dtype={'province_code':str})
    oldobs=pd.read_csv(ROOT/'data/processed/observations_long.csv',dtype={'province_code':str,'period':str})
    oldsources=pd.read_csv(ROOT/'metadata/sources.csv').fillna('')
    cards=read(ROOT/'work/stage3_cases/case_cards.json')
    source_rows=[];logs=[]
    used=['E02','E201','E202','I203','I204','A01','G202','S07','S27','S03','S01','S11']
    for r in oldsources[oldsources.source_id.isin(used)].to_dict('records'):source_rows.append(dict(r,stage_status='阶段2及之前已得，本轮沿用/复核'))
    for folder in ['stage3_government','stage3_economy','stage3_cases']:
        for r in read(ROOT/'work'/folder/'sources.json'):source_rows.append(dict(r,stage_status='阶段3新归档证据；非新增31省原值'))
        for r in read(ROOT/'work'/folder/'search_log.json'):logs.append(dict(task=folder,**r))
    main_sources=[
      dict(source_id='I301',title='2024年通信业统计公报',publisher='工业和信息化部运行监测协调局',source_url='https://www.miit.gov.cn/gxsj/tjfx/txy/art/2025/art_641c048c5d4f4e308098bf6c4e3dcb4a.html',published_at='2025-01-26',coverage_period='2024年末/全年；区域级',local_path='work/stage3_infrastructure/MIIT_2024_bulletin_web.txt',access_status='official_web_snapshot_archived',source_page_or_table='五（二），注1/3',short_excerpt='东、中、西部和东北地区',result='核区域千兆/5G汇总；不能拆31省，2024为初步数'),
      dict(source_id='I302',title='2024通信业年度统计数据编者说明',publisher='工业和信息化部',source_url='https://www.miit.gov.cn/txnj2024/tx/编者说明.html',published_at='',coverage_period='2024年度',local_path='work/stage3_infrastructure/targeted_sources_web.txt',access_status='web_timeout_failed_detail_not_obtained',source_page_or_table='本轮正常访问超时，明细未取得',short_excerpt='',result='未取得年末千兆/5G分省原表，记录后停止'),
      dict(source_id='I303',title='中国通信年鉴2003—2025商业目录',publisher='统计年鉴资料整理网站（非原发布机构）',source_url='https://www.tongjinianjian.com/china-communications-yearbook.html',published_at='',coverage_period='目录列2024年分省表，非原数',local_path='work/stage3_infrastructure/targeted_sources_web.txt',access_status='locator_only_not_numeric_source',source_page_or_table='2025年鉴目录；获取说明',short_excerpt='不提供免费下载',result='仅目录定位，未取得合法可复核表；授权馆藏为可执行后续，不算已得'),
      dict(source_id='I304',title='2024年通信业统计公报解读',publisher='工业和信息化部运行监测协调局',source_url='https://www.miit.gov.cn/gxsj/tjfx/txy/art/2025/art_8ebb624c805b4b43b9297ab3e11d268e.html',published_at='2025-01-26',coverage_period='2024全国，家庭分母另见注3',local_path='work/stage3_infrastructure/MIIT_interpretation_web.txt',access_status='official_web_snapshot_archived',source_page_or_table='三、通信服务；注3',short_excerpt='第七次人口普查家庭数',result='核家庭/全体账户不同；不把七普家庭数直接冒充2024同年省级分母')]
    for r in main_sources:
        r['sha256']=hashlib.sha256((ROOT/r['local_path']).read_bytes()).hexdigest()
        source_rows.append(dict(r,stage_status='阶段3新复核/归档证据；非新增31省质量原值'))
        logs.append(dict(task='stage3_infrastructure',**r,searched_at='2026-11-09',next_action='已达原机构/官方年鉴/授权替代路径停止点；不扩展拼表。'))
    for row in source_rows:
        path=row.get('local_path','')
        if path:
            p=Path(path)
            if not p.is_absolute():p=ROOT/p
            assert p.is_file(),path
            h=hashlib.sha256(p.read_bytes()).hexdigest()
            assert not row.get('sha256') or row['sha256']==h,row['source_id']
            row['sha256']=h;row['local_path']=p.relative_to(ROOT).as_posix()
    csv(pd.DataFrame(source_rows),DATA/'source_index.csv');csv(pd.DataFrame(logs),REPORT/'stage3_source_log.csv')
    logtext=['# 第三阶段定向检索及证据台账','', '既有31省数值不重复统计为新数据。本轮无新增合格31省统一原始产出/质量表；I2为旧原值新派生，广东为单省补证。下表的“未取得”只指本轮有边界检索，不等于全网不存在。','',f'本轮记录{len(logs)}条检索/复核；完整URL、获取状态、原件路径和SHA256见data/processed/stage3/source_index.csv。','', '|方向/来源|原始材料与机构|统计期/定位|结果及下一步|','|---|---|---|---|']
    for r in logs:
        url=r.get('source_url',r.get('url',''));title=r.get('title','见源页');sid=r.get('source_id','复核线索')
        loc=r.get('source_page_or_table',r.get('location',r.get('table_or_page','见专项报告证据矩阵')))
        result=r.get('result',r.get('finding',r.get('status',r.get('access_status','见专项报告'))))
        logtext.append(f'|{r["task"]} / {sid}|[{title}]({url})；{r.get("publisher","见原页")}|{r.get("coverage_period","待核")}；{loc}|{result}；{r.get("next_action","见相应审核报告；停止无边界扩搜")}|')
    logtext += ['', '原机构、官方年鉴和至少一种可执行替代渠道已核。G202/S07只沿用原件复核时间，不重复采31标签；门户只正常页面一次核查；D1新国家报告/分类为定义背景；D2局部原表不拼31省；案例材料分别标实施年、发布时间和自报性质。没有访问外部账号或联系机构，咨询稿未发送。']
    md('stage3_source_log.md','\n'.join(logtext)+'\n')

    # 广东只保存实际取得的1省，不创建30个“补全”行。
    gdurl='https://gdca.miit.gov.cn/zwgk/xysjtj/art/2025/art_81fc37f1ac634f5a9409132c27379ce2.html'
    gd=[]
    for oid,ind,raw,val,unit,formula,inputs,status in [
        ('C303_GD_BB','GD_BB_TOTAL_C303','5049.5',5049.5,'万户','',[],'阶段3新来源核对；数值与阶段2 I203一致'),
        ('C303_GD_GIGA','GD_GIGABIT_USERS_C303','1503.5',1503.5,'万户','',[],'阶段3新得单省质量原值'),
        ('C303_GD_GIGA_SHARE','GD_GIGABIT_SHARE_C303','',1503.5/5049.5*100,'%','GD_GIGABIT_USERS_C303 / GD_BB_TOTAL_C303 * 100',['C303_GD_GIGA','C303_GD_BB'],'阶段3新派生单省；不可排名31省')]:
        gd.append(dict(observation_id=oid,province_code='440000',province='广东',indicator_id=ind,raw_value=raw,numeric_value=val,unit=unit,period_end='2024-12-31',period_type='year_end',source_id='C303',source_url=gdurl,source_page_or_table='三、电信用户发展情况，固定宽带用户同段',original_label='千兆以上用户总数' if 'USERS' in ind else '固定宽带用户' if ind=='GD_BB_TOTAL_C303' else '作者计算',formula=formula,input_observation_ids=json.dumps(inputs),actual_province_count=1,stage_status=status))
    csv(pd.DataFrame(gd),DATA/'guangdong_quality_context.csv')
    regional=[]
    for i,region in enumerate(['东部','中部','西部','东北']):
        for iid,value in [('gigabit_share_region',[31.2,31.2,31.7,23.6][i]),('5g_user_share_region',[56.6,57.2,56.3,56.2][i])]:regional.append(dict(area=region,area_level='region',indicator_id=iid,numeric_value=value,unit='%',period_end='2024-12-31',source_id='I301',source_page_or_table='五（二）各地区5G和千兆用户占比',formula_type='主管部门区域用户总数之比，非省份等权均值',stage_status='阶段3核实既有区域背景，非新增分省表',can_enter_province_index=False))
    csv(pd.DataFrame(regional),DATA/'regional_quality_context_2024.csv')
    # 七维审核仅定性，不把等级做成另一个任意总分。
    review=[
      ('NBS_ECOM_SHARE','E1主候选','调查企业交易应用强；完整数字经济弱','31连续','2024全年明确','官方同表原值派生，高','统一样本制度；行业组合不同仍需解释','不与分子/同调查代理堆叠','中，需准确名称','仅独立展示；概念批准后可送2024合成审核','阶段2已得'),
      ('NBS_ICT_LEGAL_SHARE','E2备选','组织结构强；产出/就业弱','31连续','2024年度覆盖，月日未明示','官方同表原值派生，高','法人非企业；登记总部及行业混合','不共E1分子分母，仍有构念交叉','中高，法人单位解释门槛','仅独立展示/替代送审','阶段2已得'),
      ('NBS_COMP100','解释替补','企业设备配置；非技能/福利','31连续','2024全年明确','官方调查，高','企业人员而非居民；行业结构影响','与E1/网站同调查','中','仅独立解释/替补','阶段1/2已得'),
      ('BB_ACCOUNTS_PER100','I1主候选','接入配置强；质量/普及弱','31连续','2024年末明确','官方同版原值派生，高','人口与账户对象不一，结构影响','原数不双计；I2共人口且供需链','中高，需要测量边界','可作为2024狭义候选送审；未批准','阶段2已得'),
      ('BB_PORTS_PER100','I2替代','端口供给；非使用/速度','31连续','2024年末明确','官方旧原数新派生，高','端口容量未测闲置/空间覆盖','与I1ρ0.679，共人口','中高，个/百人非百分比','仅独立展示/替代送审','阶段3新派生'),
      ('THU_GOV_G202_SCORE','D3条件候选','数字政府概念贴合','31连续','G3-B，实际评价年待核','研究机构原图，高；底层公开有限','同图31省已核，完整规则未独立确认','与门户/BIMSA治理项同源','高，需区分报告年/数据期','仅独立展示；当前不进2024','阶段2已得，阶段3终审'),
      ('gov_online_category','保底D3','网上政府服务代理非全部治理','31档级','2024年9月上旬—10月上旬','研究机构分类，已核','同表类别，档内不能排序','不转分，不叠同义政府分','中','仅独立分类展示','阶段1/2已得'),
      ('BIMSA_INDUSTRY','外部参考','含产业应用/产业化，但底层未全披露','31连续','2019—2024机构口径','机构含补缺；附录冲突已审','公开分项不等于原统计','与D2/D3可能重叠','高','仅外部参考；不作本轮主输入','阶段1已得')]
    df=pd.DataFrame(review,columns=['indicator_id','role','concept_fit','coverage','time_consistency','source_reliability','regional_comparability','non_duplication','interpretation_difficulty','admission_recommendation','stage_status'])
    csv(df,REPORT/'stage3_candidate_validity_matrix.csv')
    candidates=df[df.indicator_id.isin(['NBS_ECOM_SHARE','NBS_ICT_LEGAL_SHARE','BB_ACCOUNTS_PER100','BB_PORTS_PER100','THU_GOV_G202_SCORE','gov_online_category'])].copy()
    candidates['include_in_index']=False;candidates['approval_status']='pending_researcher_review'
    csv(candidates,REPORT/'stage3_final_candidate_indicators.csv')

    # 三张推荐省的对照卡：数据与实施事实分层，非因果图。
    recommended=[c for c in cards if c['recommended_for_presentation']]
    assert len(cards)>=4 and 2<=len(recommended)<=3
    plt.rcParams.update({'font.family':'Microsoft YaHei','pdf.fonttype':42,'axes.unicode_minus':False})
    fig,axes=plt.subplots(1,len(recommended),figsize=(15,8.7))
    cardrows=[]
    body={
      '北京':('2024调查企业电商参与23.29%\n年末账户45.45户/百人','2024工作总结（2025-03发布）\n京津冀一网通办专区417项\n来源：C301，主管部门自报','与河北对照：区域内部差异\n以标准互认、跨域受理协作','不能认定跨域通办导致电商比例；\n417不是受益人数或全部覆盖率。'),
      '河北':('2024调查企业电商参与8.53%\n年末账户45.35户/百人','2024工作回顾（2025-01发布）\n京津冀1053项跨省通办\n来源：C302，省政府报告','与北京共同说明区域协作\n不是要求每省走同一应用路径','1053与417清单口径不同，不能相加；\n较低电商代理不等于整体数字落后。'),
      '宁夏':('2024调查企业电商参与11.03%\n年末账户53.14户/百人','中卫2024总结：7项目投运\n标准机架累计12.1万架\n来源：C305，市级主管部门自报','C306确认2024算电协同部署\n关注算力—电力—需求跨区衔接','中卫不是全宁夏；机架不等于利用率；\n不能推断项目导致全省两个代理变化。')}
    for ax,card in zip(axes,recommended):
        name=card['province'];data,project,meaning,limit=body[name]
        ax.set_axis_off();ax.set_xlim(0,1);ax.set_ylim(0,1)
        ax.add_patch(FancyBboxPatch((.015,.025),.97,.93,boxstyle='round,pad=.012',facecolor='#F5F7F9',edgecolor='#DCE2E8'))
        ax.text(.07,.89,name+'｜'+card['region_4'],fontsize=21,fontweight='bold',color='#0072B2' if card['region_4']=='东部' else '#009E73')
        for y,title,txt in [(.80,'数据表现（代理）',data),(.61,'实施事实与时间',project),(.38,'区域协调话题',meaning),(.19,'证据边界',limit)]:
            ax.text(.07,y,title,fontsize=12,fontweight='bold');ax.text(.07,y-.04,txt,fontsize=10.8,va='top',linespacing=1.7)
        cardrows.append(dict(province=name,data=data,implementation=project,regional_topic=meaning,boundary=limit))
    fig.suptitle('从省际代理差异到区域协作实践：三省推荐证据卡',x=.04,ha='left',fontsize=20,fontweight='bold')
    fig.text(.04,.035,'数据：国家统计局年鉴2025表16-39、16-36、2-5，n=31中的3省；政策/项目仅为对应地区实施事实，不能作因果归因。',fontsize=10)
    fig.text(.04,.010,'原始URL、表页、发布日期和参考期见stage3_case_evidence.md及source_index.csv；E02/I203/A01为旧数据，本轮未计算综合分。',fontsize=9)
    fig.subplots_adjust(left=.03,right=.98,top=.90,bottom=.075,wspace=.08)
    fig.savefig(REPORT/'figures_stage3/04_case_evidence_cards.png',dpi=300,facecolor='white');fig.savefig(REPORT/'figures_stage3/04_case_evidence_cards.pdf',facecolor='white');plt.close(fig)
    csv(pd.DataFrame(cardrows),DATA/'case_evidence_figure_data.csv')

    # 检查仅限本轮研究计算与逐值溯源，不增工程测试。
    byid=oldobs.set_index('observation_id');derived=pd.read_csv(DATA/'derived_ports_per100_long.csv',dtype={'province_code':str})
    checks=[]
    for r in derived.itertuples():
        a,b=json.loads(r.input_observation_ids);expected=byid.loc[a,'numeric_value']/byid.loc[b,'numeric_value']*100
        checks.append(dict(item='端口强度 '+r.province,result='通过' if abs(expected-r.numeric_value)<1e-10 else '失败'))
    for card in cards:
        for f in card['data_facts']:
            origin=byid.loc[f['observation_id']];v=origin.numeric_value if pd.notna(origin.numeric_value) else origin.category_value
            equal=abs(v-f['value'])<1e-10 if isinstance(f['value'],(int,float)) else v==f['value']
            checks.append(dict(item='案例原值 '+card['province']+' '+f['indicator_id'],result='通过' if equal else '失败'))
    assert all(c['result']=='通过' for c in checks)
    csv(pd.DataFrame(checks),REPORT/'stage3_numeric_review_checks.csv')
    md('stage3_analysis_notes.md','''# 第三阶段图表、底表与解读

本轮四张新图均为分项/证据分析；300dpi PNG及矢量PDF保存在figures_stage3。没有计算综合指数、E2合成分或正式总榜。

## 图1 企业应用×账户配置

2024全年调查企业电商与2024年末账户密度，31省Spearman为0.267。北京、广东等单项位置不一致，说明两个代理不可互相替代；不能由账户配置低推断网速、居民普及率或总体基础设施落后。图中没有回归因果或综合象限分类。

底表：indicator_review_panel_2024.csv；来源E02/I203/A01。

## 图2 候选有效性与重复风险

E1/E2的Spearman为0.498，天津、辽宁两种单项位置最大差20；I1/I2为0.679，北京、辽宁、江西差14。候选虽非完全同义，也不因相关低就自动有效或需要合成。图左为2024年度应用/结构，右为2024年末配置，不能混为一种产出。

底表：indicator_correlations.csv、indicator_review_panel_2024.csv；来源E02/E201/I203/A01。

## 图3 中心统计量与单省影响

西部电商均值11.80%略高中部11.36%，但中位数西11.40%低于中12.23%；仅删重庆后的西部均值为11.32%。这只是影响诊断，不能据此改正式31省范围；线段不是置信区间，也不证明某个区域真实发展一定高低。

底表：regional_review_statistics.csv、leave_one_province_out.csv、west_central_influence_diagnostic.csv；同前述官方源。

## 图4 案例证据卡

北京与河北的应用差异连到京津冀公共服务协作；宁夏配置与应用的不同侧重连到中卫项目和算电协同部署。三省均仅被作为候选案例推荐，项目事实不证明提高任何指数，事项清单不相加，市级项目不外推全省效果。广东另保留为代理诊断备用卡。

底表：case_evidence_figure_data.csv及work/stage3_cases/case_cards.json；完整链接与日期见stage3_case_evidence.md。
''')
    c=read(ROOT/'work/stage3_government/conclusion.json')
    summary=f'''# 第三阶段研究总报告（提交下一轮审核）

**当前仍不具备正式计算2024年31省三维综合排行榜的条件。** D3终审为G3-B：31省数值完整，但没有足够直接证据确认G202的2024评价目标；D1仍为企业应用/行业组织代理，D2仍主要测固定接入配置。推荐保留严格同年方案A为目标，当前采用方案B分项画像与2024网上政府档级作为可靠保底；方案C仅供特别审批，本轮未合成。

## 一、D3最高优先事项的裁决

G202 PDF13/印刷9总方法仅称“多数”分指数面向2024，第十章PDF97/印刷93仅说明“历时半年”，未逐项列评价期。PDF101的2024是机构成立年，不能补证。清华新定位发布页证明S07名义2024的发布事件，仍不能把G202与它的版本关系视作已证。版本同一不是必需前提：直接证明G202自身评价目标2024也可送审，但本轮未得。

本轮13项证据矩阵区分直接/间接/未证实，四维框架和31省同图已核；完整权重、缺失规则、跨省加分和窗口未完全公开，不替机构保证。未证实不等于证伪，因此判G3-B，不判其永久无效或G3-C。咨询稿已经准备但未发送。

## 二、D1与D2测量有效性及定向补证

|指标|统计期证据|样本与数值完整性|数据性质|概念是否足够贴合|重复计量风险|可否用于2024三维合成|未满足条件|
|---|---|---|---|---|---|---|---|
|E1电商参与比例|官方表16-39，2024全年|31连续，阶段2已得|官方调查派生比例|只贴合调查企业交易应用|分子/同调查代理重复|概念批准后可作条件候选，未批准|D1收窄命名及正向含义|
|E2信息服务法人占比|官方表1-5，2024年度覆盖|31连续，阶段2已得|官方组织数派生结构|不是产出、就业或完整数字产业|与E1不同分子，但构念交叉仍审|独立辅助/替代候选|是否需要组织基础、归并理由|
|I1宽带账户强度|2024年末表16-36/2-5|31连续，阶段2已得|账户/人口，户/百人|狭义接入配置，非居民普及或质量|与原数、I2共分母/供需链|可提交狭义候选审核，不是正式采用|D2名称、分母偏差与方向|
|I2端口强度|同版2024年末|原值阶段2；阶段3新派生31值|供给/人口，个/百人|供给容量非使用或速率|与I1ρ0.679|仅独立/替代送审|不默认同维双计|
|G202政府分|2025报告，2024目标未直接证明|31连续，阶段2已得|机构复合指数|政府构念贴合，方法公开有限|与门户/BIMSA有共享信息|否，G3-B卡点|直接年度、窗口/跨年与省际规则证据|
|S27政府档级|2024年9月上旬—10月上旬|31档级，旧资料|机构分类|网上政府服务代理|不转数值/不叠同义分|只独立展示|不产生31个精确分数|

E1/E2 Pearson=0.606、Spearman=0.498，最大单项位置差20；I1/I2分别0.655、0.679，最大差14。它们并非完全等价，但相关性不能代替概念审核。没有计算E2合成、正式权重或总排名。

定向查过国家数据局新归档2024报告、国家统计局分类与全国核算、工信部数字产业和同源替代；未取得统一31省数字产业产出原表，E3本轮不采用。通信部门原机构/年鉴/授权目录路径查到停止点，仍无31省年末千兆/5G统一质量表。广东同段新证据可算1503.5/5049.5×100=29.78%，仅一省，不替其余30省。

广东39.51户/百人、海南58.14户/百人的含义是账户配置。家庭规模、机构账户、移动替代和统计归属是待检验机制，未作因果确定。官方全国家庭宽带与全部宽带的分拆只能帮助辨别对象；其家庭数引用七普，不能假装已经得到2024年31省家庭修正分母。

## 三、门户只作对照核查，不替换主框架

门户2025默认北京“数字政府”二级69.64与G202独立分81.64不同，G202表2-1也证明前者再合成多个政府相关指数。门户数据来源页仍写2023版/2022数据，普通2024参数访问仍见2025默认，未核到2024三项二级31省完整表，停止长期抓取。既不能因页面入口存在就宣布有2024合格原值，也不能因一次GET未取得就断言网站没有交互数据。未来外部对照也需披露与G202同源，不叫严格独立验证。

## 四、推荐框架与方法审议

目标A最小树：D1优先E1“调查企业交易应用”，E2仅辅助；D2优先I1“固定接入配置”，I2替代；D3保留G202条件候选，先过时间和规则。任何维度宽名称均待批准。保底B：D1/D2单独连续展示，D3用真实2024调查档级，保持31省；C只是非严格同期的特别审批方案，不实际合成。

方法备忘录比较Min–Max、Z和百分位，提出维度内先归并再维度间赋权、一级等权仅候选、批准后再做权重扰动/代理替换/标准化敏感性。七维定性审核包括概念、覆盖、时间、来源、地区可比、重复和解释难度；未把它们再随意加成一个准入总分。

## 五、区域分析与政策案例研究

新增4张图及底表：应用×账户散点、两组候选有效性对照、区域单省影响诊断、三省推荐案例卡。只做单项和证据对照，没有综合图或地图。

西部电商均值11.80%略高中部11.36%，但中位数西11.40%低于中12.23%；仅删除重庆的诊断中西部均值11.32%低于中部。这说明均值排序受个别省影响，不能宣布稳定的中西发展次序，也不能真的删省改样本。东部内部北京与河北仍差14.75个百分点，政策回应应面向省内外具体短板，而非只报四区域平均。

已做4张证据卡：北京、河北、广东、宁夏。推荐北京—河北对照与宁夏，共3省；广东作为代理诊断备用。北京2024总结的417项一网通办与河北2024回顾的1053项跨省通办不是同口径，不能相加。宁夏卡用中卫2024投运项目及中央部门对2024算电协同部署的确认，市级进展不冒充全省效果。

|数据发现→研究问题|原始实施证据|可提出的区域协调回应|不可声称|
|---|---|---|---|
|京冀应用差异，不能抹成东部均值|C301/C302：2024跨域公共服务清单与受理实践|关注标准互认、办事可及和实际使用，后续按同定义评估受益|不能说跨省通办导致两省电商比例或缩小差距|
|宁夏配置/交易代理不同侧重|C305：中卫7项目投运、12.1万机架；C306确认2024部署|讨论算力—电力—需求衔接和地区功能互补，补测利用率/能效/跨区服务|不能以机架数证明充分利用、居民获益或东西差距已缩小|
|广东人均账户低不能推出总体设施差|C303单省千兆结构29.78%，与账户密度不同量|最终测度需分开配置、速率和体验；没有31省质量表时坦诚边界|不能给广东排全国质量名次，或认定家庭规模已解释异常|

这是对中国式现代化区域协调发展议题的实证切口：不要求每个地区在所有代理上同一序列，以真实协作实践讨论公共服务普惠与优势互补；现有代理没有直接测居民获得感、数字鸿沟或政策因果效果，不能补写这些结论。2025/2026材料只按其实施/回顾时间使用，不倒因2024数据。

## 六、第三阶段五问的明确答案

1. **G202能否归2024？** 本轮不能直接确认；依据是PDF13“多数”及PDF97未列窗口，G3-B；不是证实它不属于2024。
2. **D1测什么？** 仍是企业交易应用/行业组织结构；没有新统一31省数字产业产出。
3. **D2测什么？** 完整31省只测配置；新增I2派生和广东一省质量补证，仍无完整31省年末质量/5G。
4. **哪套最合理？** A为条件目标，E1/I1为最小可解释候选；目前B是可靠交付，C仅待特别审批。
5. **下一阶段能否算总榜？** 尚不能。需先补D3直接年度与规则证据、批准D1/D2概念及方法；B无需等待总榜即可开展课堂分项汇报准备。

## 提交下一轮审核的三项决定

1. 接受D1收窄为调查企业交易应用、D2收窄为固定接入配置吗？如不接受，原宽概念的产出/质量缺口仍成立。
2. 是否先按方案B确定课堂研究叙事：京冀内部差异与公共服务协作、宁夏功能互补，广东作方法警示？不涉及批准总榜。
3. 是否审阅咨询稿并安排原团队确认G202评价目标与省际规则？邮件尚未发送。标准化、一级权重与正式总榜留待证据和方法另轮批准。

## 交付与核对入口

- 总报告：stage3_summary.md。
- 关键审核：stage3_government_time_audit.md、stage3_portal_review.md、stage3_economy_review.md、stage3_infrastructure_review.md。
- 候选体系及方法：stage3_indicator_framework.md、stage3_final_candidate_indicators.csv、stage3_candidate_validity_matrix.csv、stage3_method_options.md。
- 独立准入结论：stage3_ranking_readiness.md；案例：stage3_case_evidence.md；来源：stage3_source_log.md/.csv及data/processed/stage3/source_index.csv。
- 统计/溯源：data/processed/stage3/内31省审核底表、31个新派生值及输入ID、相关矩阵、单省影响诊断、广东单省/四区域背景、图4底表；这些不重复冒称新31省原始统计。
- 图：figures_stage3/共4组PNG（300dpi）及PDF，图注与数据索引见stage3_analysis_notes.md。
- 本轮有限计算核对共{len(checks)}项（31个派生、12个案例原值），均与原观察一致；归档源hash逐项比对无冲突。仅作研究必要核对，没有扩展工程测试或改数据库架构。

第一、二阶段研究结论保留。所有指标仍待批准，未计算、发布正式综合排名，未改变31省范围，未发邮件，未开展工程复现或开源工作。
'''
    md('stage3_summary.md',summary)
    print(json.dumps(dict(source_index_rows=len(source_rows),source_log_rows=len(logs),derived_ports=31,case_cards=len(cards),recommended_cases=len(recommended),figures=4,numeric_checks=len(checks),ranking_ready=False),ensure_ascii=False))
if __name__=='__main__':main()
