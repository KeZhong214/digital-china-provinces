"""第一阶段：归档证据 -> 候选观察值 -> SQLite/CSV/覆盖率；不计算综合排名。"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, sqlite3, sys, calendar
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NOW = '2026-11-09'
def dump_csv(path, rows, fields=None):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None: fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w=csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
def md(path, text): (ROOT/path).write_text(text,encoding='utf-8')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def provinces():
    pairs=[(11,'北京','北京市'),(12,'天津','天津市'),(13,'河北','河北省'),(14,'山西','山西省'),(15,'内蒙古','内蒙古自治区'),(21,'辽宁','辽宁省'),(22,'吉林','吉林省'),(23,'黑龙江','黑龙江省'),(31,'上海','上海市'),(32,'江苏','江苏省'),(33,'浙江','浙江省'),(34,'安徽','安徽省'),(35,'福建','福建省'),(36,'江西','江西省'),(37,'山东','山东省'),(41,'河南','河南省'),(42,'湖北','湖北省'),(43,'湖南','湖南省'),(44,'广东','广东省'),(45,'广西','广西壮族自治区'),(46,'海南','海南省'),(50,'重庆','重庆市'),(51,'四川','四川省'),(52,'贵州','贵州省'),(53,'云南','云南省'),(54,'西藏','西藏自治区'),(61,'陕西','陕西省'),(62,'甘肃','甘肃省'),(63,'青海','青海省'),(64,'宁夏','宁夏回族自治区'),(65,'新疆','新疆维吾尔自治区')]
    regions={'东部':'北京 天津 河北 上海 江苏 浙江 福建 山东 广东 海南'.split(),'中部':'山西 安徽 江西 河南 湖北 湖南'.split(),'东北':'辽宁 吉林 黑龙江'.split(),'西部':'内蒙古 广西 重庆 四川 贵州 云南 西藏 陕西 甘肃 青海 宁夏 新疆'.split()}
    return [dict(province_code=f'{code}0000',province_name=full,short_name=name,region_4=next(k for k,v in regions.items() if name in v),display_order=i+1) for i,(code,name,full) in enumerate(pairs)]

def initial_sources():
    rows=[]
    for line in (ROOT/'PROJECT_PLAN.md').read_text(encoding='utf-8').splitlines():
        if re.match(r'\| S\d\d \|',line):
            f=[x.strip() for x in line.strip('|').split('|')]
            rows.append(dict(source_id=f[0],title=f[1],publisher=f[1].split('：')[0],source_url=f[5],host_domain=urlparse(f[5]).netloc,coverage_period=f[2],source_type='plan_candidate',access_status='pending_verification',citation_note=f[3],published_at='',local_path='',sha256='',plan_status=f[4],verification_date=NOW))
    return rows

def date_period(period, item):
    p=str(period)
    if item.get('period_start') and item.get('period_end'):
        return item['period_start'],item['period_end'],item.get('period_type','period_unconfirmed')
    if re.fullmatch(r'\d{4}',p):
        typ=item.get('period_type','annual')
        return (f'{p}-12-31' if typ=='year_end' else f'{p}-01-01',f'{p}-12-31',typ)
    if re.fullmatch(r'\d{4}-\d{2}',p):
        y,m=map(int,p.split('-')); return f'{p}-01',f'{p}-{calendar.monthrange(y,m)[1]}','month_end'
    return item.get('period_start',''), item.get('period_end',''),item.get('period_type','period_unconfirmed')

def broadband():
    path=ROOT/'data/raw/S05_web_snapshot.txt'
    rows=[]; agg=[]
    ids=['BB_TOTAL','BB_FTTH','BB_100M','BB_1000M']
    for line in path.read_text(encoding='utf-8').splitlines():
        m=re.search(r'L\d+: (.+?)\s+\|\s+([\d.]+)\s+\|\s+([\d.]+)\s+\|\s+([\d.]+)\s+\|\s+([\d.]+)',line)
        if not m: continue
        name,*vals=m.groups()
        if name not in {p['short_name'] for p in provinces()}:
            agg.append(dict(area=name,period='2024-05',**dict(zip(ids,map(float,vals))))); continue
        for iid,label,val in zip(ids,['合计','FTTH/O用户','100M速率以上用户','1000M速率以上用户'],vals):
            rows.append(dict(province=name,indicator_id=iid,period='2024-05',raw_value=val,numeric_value=float(val),category_value=None,unit='万户',source_id='S05',source_page_or_table='网页分省表；'+line.split(':')[0],original_label=label,extraction_method='regex_from_web_tool_snapshot',verification_status='source_confirmed',qc_note='直连403；通过web工具读取官方网页的文本快照，非原始HTML。西藏FTTH突变未修正。'))
    dump_csv('data/interim/S05_aggregate_checks_input.csv',agg)
    return rows,agg

BASE={
 'BB_TOTAL':('固定互联网宽带接入用户','D2','万户','count','2024-05','规模；家庭及机构接入账户数，不等于居民人数'),
 'BB_FTTH':('FTTH/O用户','D2','万户','count','2024-05','与宽带总数重叠；西藏字段需特别核对'),
 'BB_100M':('100M速率以上用户','D2','万户','count','2024-05','与1000M嵌套，不宜同时加权'),
 'BB_1000M':('1000M速率以上用户','D2','万户','count','2024-05','规模指标；建议转占比'),
 'BB_1000M_SHARE':('千兆宽带用户占比','D2','%','rate','2024-05','分子BB_1000M/分母BB_TOTAL×100，属于接入速率结构'),
 'BB_TOTAL_YEAR_END':('年末固定宽带用户数','D2','万户','count','2024','官方年度数据入口已定位；明细未取得'),
 'BB_1000M_YEAR_END':('年末千兆用户数','D2','万户','count','2024','同年末总数配对计算占比；未取得'),
 'gov_development_score':('数字政府连续分数','D3','分','continuous_score','2024','S07链接仅节选；不能凭题名断定统计截点'),
 'CORE_DIGITAL_GDP_SHARE':('数字经济核心产业增加值占GDP比重','D1','%','rate','2024','尚未取得同口径31省；地区自报不可直接拼接'),
 'BTS_5G':('年末5G基站数','D2','万个','count','2024','查工信部年度分省表；未获得不补零'),
 'population_year_end':('年末常住人口','AUX','万人','count','2024','年鉴2025表2-5；省级不含现役军人，全国含现役军人；辅助分母'),
 'gdp_current_price':('地区生产总值','AUX','亿元','count','2024','年鉴2025表3-9；当年价格、初步核算版；辅助解释变量'),
 'BIMSA_TOTAL':('数字经济综合指数（研究机构测算）','EXT','分','continuous_score','2024','仅外部参照；已含基础设施和治理，不进入自建三维加权'),
 'BIMSA_INDUSTRY':('数字产业发展分项（正文）','D1','分','continuous_score','2024','S03正文表4-2；与附录冲突；须核原始构成和计分尺度'),
 'BIMSA_INFRA':('基础设施分项（正文）','EXT','分','continuous_score','2024','报告内审计用途；非独立官方统计'),
 'BIMSA_TALENT':('人才分项（正文）','EXT','分','continuous_score','2024','报告内审计用途；非独立官方统计'),
 'BIMSA_GOV':('治理分项（正文）','EXT','分','continuous_score','2024','报告内审计用途；需核代理变量含义'),
 'NBS_ENT':('调查企业数','AUX','个','count','2024','年鉴16-39调查范围企业，非全社会所有企业'),
 'NBS_COMP':('期末使用计算机台数','D1','台','count','2024','规模型；取自年鉴16-39'),
 'NBS_COMP100':('每百人使用计算机数','D1','台/百人','rate','2024','调查企业信息化应用强度，非居民计算机普及率'),
 'NBS_WEBSITES':('企业拥有网站数','D1','个','count','2024','规模型；取自年鉴16-39'),
 'NBS_WEB100':('每百家企业拥有网站数','D1','个/百家企业','rate','2024','调查企业网站应用强度，非数字产业产出'),
 'NBS_ECOM_ENT':('有电子商务交易活动的企业数','D1','个','count','2024','分母应为同表调查企业数；非全体企业'),
 'NBS_ECOM_SALES':('电子商务销售额','D1','亿元','count','2024','调查企业电商销售额，不等于网上零售额或增加值'),
 'NBS_ECOM_PURCHASE':('电子商务采购额','D1','亿元','count','2024','与销售额存在交易重叠，不宜相加加权'),
 'NBS_ECOM_SHARE':('调查企业有电商交易活动占比','D1','%','rate','2024','NBS_ECOM_ENT/NBS_ENT×100；衡量企业数字应用，不等于数字经济规模'),
}
SEARCHED={'gov_development_score':'S07;S25;S27','CORE_DIGITAL_GDP_SHARE':'S03;S10;E01',
          'BB_TOTAL_YEAR_END':'S06;S13','BB_1000M_YEAR_END':'S06;S13','BTS_5G':'S06;S13'}

def load_agents():
    sources=[]; obs=[]
    for folder in ['economy','government','auxiliary']:
        combined=ROOT/'work'/folder/'government_deliverable.json'
        if folder=='government' and combined.exists():
            d=json.loads(combined.read_text(encoding='utf-8-sig'));sources.extend(d['sources']);obs.extend(d['observations']);continue
        for name,target in [('sources.json',sources),('observations.json',obs)]:
            path=ROOT/'work'/folder/name
            if path.exists():
                obj=json.loads(path.read_text(encoding='utf-8-sig'))
                if isinstance(obj,dict): obj=obj.get(name.split('.')[0],list(obj.values()))
                target.extend(obj)
    return sources,obs

def normalize_source(s):
    s=dict(s)
    for a,b in [('id','source_id'),('url','source_url'),('path','local_path'),('publication_date','published_at'),('statistical_period','coverage_period')]:
        if a in s and b not in s:s[b]=s[a]
    path=s.get('local_path','')
    if path:
        p=Path(path)
        if not p.is_absolute():p=ROOT/p
        if p.is_file(): s['local_path']=p.relative_to(ROOT).as_posix();s['sha256']=sha(p)
    s['host_domain']=urlparse(s.get('source_url','')).netloc
    return s

def normalize_obs(o, mapping):
    o=dict(o)
    province=o.get('province',o.get('province_name',o.get('short_name','')))
    code=str(o.get('province_code') or mapping.get(province,''))
    if code not in {p['province_code'] for p in provinces()}:raise ValueError(f'未知省份 {province}: {code}')
    period=str(o.get('period',o.get('year','')))
    start,end,typ=date_period(period,o)
    if o['indicator_id'].startswith('gov_open_data'):
        start,end,typ='','2024-08','cutoff_month'
    elif o['indicator_id'].startswith('gov_online'):
        start,end,typ='2024-09','2024-10','survey_window_month_precision'
    elif o['indicator_id']=='gov_service_category':
        start,end,typ='2025-08','2025-11','survey_window_month_precision'
    num=o.get('numeric_value')
    if num is not None and num!='':num=float(num)
    else:num=None
    category=o.get('category_value') or None
    iid=o['indicator_id'];sid=o['source_id'];version=str(o.get('data_version','archived_2026-11-09'))
    key='|'.join([code,iid,period,sid,version])
    return dict(observation_id=hashlib.sha256(key.encode()).hexdigest()[:24],province_code=code,indicator_id=iid,period=period,period_start=start,period_end=end,period_type=typ,raw_value=str(o.get('raw_value','')),numeric_value=num,category_value=category,unit=o.get('unit',''),source_id=sid,source_page_or_table=o.get('source_page_or_table',''),original_label=o.get('original_label',iid),extraction_method=o.get('extraction_method','manual_transcription'),verification_status=o.get('verification_status','machine_extracted'),qc_note=o.get('qc_note',''),is_derived=0,formula_id='',data_version=version,created_at=NOW)

def make_indicators(obs):
    extra=ROOT/'work/government/indicators.json'
    if extra.exists():
        for r in json.loads(extra.read_text(encoding='utf-8-sig')):
            name=r.get('name',r.get('indicator_name'))
            if r['indicator_id'].startswith('gov_open_data_city'):name='开放数据城市模型·'+name
            elif r['indicator_id'].startswith('gov_open_data'):name='开放数据省域模型·'+name
            BASE[r['indicator_id']]=(name,r['dimension'],r['unit'],r['value_type'],r['candidate_period'],r['notes'])
    out=[]
    for iid in sorted(set(BASE)|{o['indicator_id'] for o in obs}):
        ex=next((o for o in obs if o['indicator_id']==iid),{})
        if iid not in BASE:raise ValueError('需要显式定义指标字典：'+iid)
        vals=BASE[iid]
        name,dim,unit,vtype,year,note=vals
        out.append(dict(indicator_id=iid,indicator_name=name,dimension=dim,definition=note,unit=unit,direction='positive' if dim!='AUX' else 'context',value_type=vtype,numerator_id='BB_1000M' if iid=='BB_1000M_SHARE' else '',denominator_id='BB_TOTAL' if iid=='BB_1000M_SHARE' else '',candidate_year=str(year)[:4],candidate_period=year,source_priority='official_then_research',expected_coverage=31,include_in_index='false',approval_status='pending_researcher_review',notes=note))
    return out

SCHEMA='''
PRAGMA foreign_keys=ON;
CREATE TABLE sources(source_id TEXT PRIMARY KEY,title TEXT,publisher TEXT,host_domain TEXT,source_url TEXT,local_path TEXT,published_at TEXT,coverage_period TEXT,source_type TEXT,access_status TEXT,sha256 TEXT,citation_note TEXT,metadata_json TEXT);
CREATE TABLE provinces(province_code TEXT PRIMARY KEY,province_name TEXT,short_name TEXT UNIQUE,region_4 TEXT,display_order INTEGER);
CREATE TABLE indicators(indicator_id TEXT PRIMARY KEY,indicator_name TEXT,dimension TEXT,definition TEXT,unit TEXT,direction TEXT,value_type TEXT,numerator_id TEXT,denominator_id TEXT,candidate_year TEXT,source_priority TEXT,expected_coverage INTEGER,include_in_index INTEGER CHECK(include_in_index=0),approval_status TEXT,notes TEXT);
CREATE TABLE observations(observation_id TEXT PRIMARY KEY,province_code TEXT REFERENCES provinces,indicator_id TEXT REFERENCES indicators,period TEXT,period_start TEXT,period_end TEXT,period_type TEXT,raw_value TEXT,numeric_value REAL,category_value TEXT,unit TEXT,source_id TEXT REFERENCES sources,source_page_or_table TEXT,original_label TEXT,extraction_method TEXT,verification_status TEXT,qc_note TEXT,is_derived INTEGER,formula_id TEXT,data_version TEXT,created_at TEXT,UNIQUE(province_code,indicator_id,period,source_id,data_version),CHECK(NOT(numeric_value IS NOT NULL AND category_value IS NOT NULL)));
CREATE TABLE derived_values(observation_id TEXT PRIMARY KEY REFERENCES observations,formula TEXT,input_observation_ids TEXT,calculation_version TEXT,qc_status TEXT);
CREATE TABLE missingness(province_code TEXT REFERENCES provinces,indicator_id TEXT REFERENCES indicators,period TEXT,reason_code TEXT,searched_sources TEXT,evidence_note TEXT,next_action TEXT);
CREATE TABLE source_audit(audit_id TEXT PRIMARY KEY,source_id TEXT REFERENCES sources,audited_at TEXT,auditor TEXT,method TEXT,finding TEXT,evidence_path TEXT);
'''
def insert_rows(con,table,rows):
    fields=[r[1] for r in con.execute(f'PRAGMA table_info({table})')]
    for row in rows:
        r=dict(row)
        if table=='sources': r['metadata_json']=json.dumps(row,ensure_ascii=False)
        if table=='indicators':r['include_in_index']=0
        con.execute(f'INSERT INTO {table} ({",".join(fields)}) VALUES ({",".join("?" for _ in fields)})',[r.get(k) for k in fields])

def build():
    for path in ['data/processed','reports','metadata','config','logs']: (ROOT/path).mkdir(parents=True,exist_ok=True)
    prov=provinces();mapping={k:p['province_code'] for p in prov for k in [p['short_name'],p['province_name']]}
    sources={s['source_id']:s for s in initial_sources()}
    agents,other=load_agents()
    for raw in agents:
        s=normalize_source(raw);sources[s['source_id']]={**sources.get(s['source_id'],{}),**s}
    sources['S05'].update(local_path='data/raw/S05_web_snapshot.txt',sha256=sha(ROOT/'data/raw/S05_web_snapshot.txt'),access_status='web_snapshot_archived_direct_http_403',published_at='2024-06-24',coverage_period='2024-05',source_type='official_statistics',citation_note='官方网页完整数值文本，经web工具读取；本地HTTP响应403文件并非数据原文，另存日志。')
    sources['S06'].update(local_path='data/raw/S06.html',sha256=sha(ROOT/'data/raw/S06.html'),access_status='direct_http_403_web_read',source_type='official_statistics',published_at='2025-01-26',coverage_period='2024',citation_note='直连403响应仅为失败证据；web可读全国与四区域公报，不能当31省明细。')
    sources['S13']=dict(source_id='S13',title='2024年通信业年度统计数据编者说明及目录待取得',publisher='工业和信息化部运行监测协调局',source_url='https://www.miit.gov.cn/txnj2024/tx/编者说明.html',host_domain='www.miit.gov.cn',coverage_period='2024',source_type='official_metadata',access_status='web_metadata_confirmed_detail_not_obtained',local_path='data/raw/annual_note.html',sha256=sha(ROOT/'data/raw/annual_note.html'),published_at='2025-10-31',citation_note='web核到编者说明：年度决算、含全国分省；直连403文件非明细，表级URL尚未取得。')
    sources['S10'].update(access_status='web_snapshot_archived',local_path='data/raw/S10_web_snapshot.txt',sha256=sha(ROOT/'data/raw/S10_web_snapshot.txt'),published_at='2024-03-28',coverage_period='2024-01—2024-02',source_type='official_statistics',citation_note='web工具核原表，单位万元，表注明确西藏无统计数据；只作短期口径证据，不当全年输入。')
    bb,aggregates=broadband();obs=[normalize_obs(o,mapping) for o in bb+other]
    derived=[]
    for p in prov:
        parts={o['indicator_id']:o for o in obs if o['province_code']==p['province_code'] and o['period']=='2024-05' and o['source_id']=='S05'}
        a,b=parts['BB_1000M'],parts['BB_TOTAL']
        row=normalize_obs(dict(province=p['short_name'],indicator_id='BB_1000M_SHARE',period='2024-05',raw_value='',numeric_value=a['numeric_value']/b['numeric_value']*100,unit='%',source_id='S05',source_page_or_table='网页分省表；由原值计算',original_label='作者自算千兆用户占比',extraction_method='derived_exact_ratio',verification_status='source_confirmed',qc_note='输入为一位小数万户原值，派生精度不代表原值精度'),mapping)
        row.update(is_derived=1,formula_id='gigabit_share_v1');obs.append(row)
        derived.append(dict(observation_id=row['observation_id'],formula='BB_1000M / BB_TOTAL * 100',input_observation_ids=json.dumps([a['observation_id'],b['observation_id']]),calculation_version='v1',qc_status='verified_inputs'))
    for p in prov:
        parts={o['indicator_id']:o for o in obs if o['province_code']==p['province_code'] and o['period']=='2024' and o['indicator_id'] in ['NBS_ENT','NBS_ECOM_ENT']}
        if set(parts)!= {'NBS_ENT','NBS_ECOM_ENT'}:continue
        a,b=parts['NBS_ECOM_ENT'],parts['NBS_ENT']
        row=normalize_obs(dict(province=p['short_name'],indicator_id='NBS_ECOM_SHARE',period='2024',raw_value='',numeric_value=a['numeric_value']/b['numeric_value']*100,unit='%',source_id=a['source_id'],source_page_or_table='年鉴2025表16-39同表分子与分母；作者自算',original_label='调查企业有电商交易活动占比',extraction_method='derived_exact_ratio',verification_status='source_confirmed',qc_note='仅调查范围内企业，不等于全社会企业电商普及率'),mapping)
        row.update(is_derived=1,formula_id='enterprise_ecommerce_share_v1');obs.append(row)
        derived.append(dict(observation_id=row['observation_id'],formula='NBS_ECOM_ENT / NBS_ENT * 100',input_observation_ids=json.dumps([a['observation_id'],b['observation_id']]),calculation_version='v1',qc_status='verified_inputs'))
    inds=make_indicators(obs)
    for i in inds:
        observed_units={o['unit'] for o in obs if o['indicator_id']==i['indicator_id']}
        if len(observed_units)==1:i['unit']=next(iter(observed_units))
        if i['indicator_id']=='NBS_ECOM_SHARE':i.update(numerator_id='NBS_ECOM_ENT',denominator_id='NBS_ENT')
    missing=[];coverage=[]
    govfile=ROOT/'work/government/government_deliverable.json'
    govmissing={}
    if govfile.exists():
        for r in json.loads(govfile.read_text(encoding='utf-8'))['missingness']:
            govmissing[(mapping[r['province']],r['indicator_id'],r['period'])]=r
    for ind in inds:
        iid=ind['indicator_id'];periods=sorted({o['period'] for o in obs if o['indicator_id']==iid}|{str(ind['candidate_period'])})
        for period in periods:
            cv=dict(indicator_id=iid,indicator_name=ind['indicator_name'],dimension=ind['dimension'],period=period)
            for p in prov:
                items=[o for o in obs if o['province_code']==p['province_code'] and o['indicator_id']==iid and o['period']==period]
                verified=[o for o in items if o['verification_status'] in ['source_confirmed','manually_checked']]
                cv[p['short_name']]='numeric_verified' if any(o['numeric_value'] is not None for o in verified) else 'category_verified' if any(o['category_value'] for o in verified) else 'pending_verification' if items else 'missing'
                if not verified:
                    reason='pending_verification' if items else 'not_obtained'
                    if iid=='gov_development_score':reason='incomplete_public_pdf'
                    record=dict(province_code=p['province_code'],indicator_id=iid,period=period,reason_code=reason,searched_sources=SEARCHED.get(iid,';'.join(sorted({o['source_id'] for o in obs if o['indicator_id']==iid}))),evidence_note=ind['notes'],next_action='见 reports/missing_data.md；不补零、不估值')
                    if (p['province_code'],iid,period) in govmissing:
                        r=govmissing[(p['province_code'],iid,period)]
                        record.update({k:r[k] for k in ['reason_code','searched_sources','evidence_note','next_action']})
                        if r['reason_code']=='not_applicable':cv[p['short_name']]='not_applicable'
                    missing.append(record)
            cv['numeric_verified_count']=sum(v=='numeric_verified' for v in [cv[p['short_name']] for p in prov]);cv['category_verified_count']=sum(v=='category_verified' for v in [cv[p['short_name']] for p in prov]);coverage.append(cv)
    maps=[dict(source_id=sid,indicator_id=iid,relation='derived' if iid in ['BB_1000M_SHARE','NBS_ECOM_SHARE'] else 'observed') for sid,iid in sorted({(o['source_id'],o['indicator_id']) for o in obs})]
    audit=[dict(audit_id=f'A{i:03}',source_id=s['source_id'],audited_at=NOW,auditor='Codex',method='artifact_hash_and_source_inspection',finding=s.get('citation_note','')+'; access_status='+s.get('access_status',''),evidence_path=s.get('local_path','')) for i,s in enumerate(sources.values(),1)]
    tmp=ROOT/'data/digital_china.build.sqlite'
    if tmp.exists(): tmp.unlink()
    con=sqlite3.connect(tmp);con.executescript(SCHEMA)
    for t,r in [('sources',list(sources.values())),('provinces',prov),('indicators',inds),('observations',obs),('derived_values',derived),('missingness',missing),('source_audit',audit)]:insert_rows(con,t,r)
    con.commit();con.close();tmp.replace(ROOT/'data/digital_china.sqlite')
    for path,rows in [('metadata/provinces.csv',prov),('metadata/sources.csv',list(sources.values())),('metadata/indicators.csv',inds),('metadata/source_indicator_map.csv',maps),('data/processed/observations_long.csv',obs),('reports/coverage_matrix.csv',coverage),('reports/missingness.csv',missing),('data/processed/derived_values.csv',derived)]:dump_csv(path,rows)
    # 不把同年月份合并：主面板仅收2024全年/年末，月度和档级另表。
    for period,filename in [('2024','candidate_panel_2024.csv'),('2024-05','candidate_panel_2024_05.csv')]:
        panel=[]
        for p in prov:
            row=dict(p)
            for o in obs:
                if o['province_code']==p['province_code'] and o['period']==period and o['verification_status'] in ['source_confirmed','manually_checked']:
                    col=o['indicator_id']+'__'+o['source_id']+'__'+o['data_version']
                    row[col]=o['numeric_value'] if o['numeric_value'] is not None else o['category_value']
            panel.append(row)
        dump_csv('data/processed/'+filename,panel)
    md('config/indicators.json',json.dumps(inds,ensure_ascii=False,indent=2))
    # 加总核验保留原始差，不强行凑齐。容差取31省及全国四舍五入的最大累计0.05万户。
    checks=[]
    for field in ['BB_TOTAL','BB_FTTH','BB_100M','BB_1000M']:
        for ag in aggregates:
            ps=[p for p in prov if ag['area']=='全国' or p['region_4']+'地区'==ag['area']]
            if not ps:continue
            total=sum(o['numeric_value'] for o in obs if o['indicator_id']==field and o['province_code'] in {p['province_code'] for p in ps} and o['source_id']=='S05' and o['period']=='2024-05' and o['data_version']=='archived_2026-11-09')
            tol=(len(ps)+1)*0.05+1e-9
            checks.append(dict(indicator_id=field,area=ag['area'],province_sum=round(total,4),reported_total=ag[field],difference=round(total-ag[field],4),rounding_tolerance=tol,result='pass' if abs(total-ag[field])<=tol else 'review'))
    dump_csv('reports/aggregate_checks.csv',checks)
    report=['# 候选数据可得性（第一阶段）','',f'核验日期：{NOW}。原始及已有指数观察值 {sum(not o["is_derived"] for o in obs)} 条；作者派生值 {len(derived)} 条。所有候选指标均未批准进入综合评价。','', '|指标ID|指标|维度|期间|类型|数值/31|档级/31|缺失省份|来源|2024同年口径|重复风险|建议与理由|','|---|---|---|---|---|---:|---:|---|---|---|---|---|']
    for cv in coverage:
        iid=cv['indicator_id'];sids=','.join(sorted({o['source_id'] for o in obs if o['indicator_id']==iid and o['period']==cv['period']})) or '待取得'
        recommendation='待核口径/重复计量' if cv['numeric_verified_count']==31 else '仅辅助，不转分数' if cv['category_verified_count'] else '待取得/覆盖不足'
        if iid.startswith('BB_') and cv['period']=='2024-05':recommendation='月度辅助；不可直接替代年末'
        ind=next(i for i in inds if i['indicator_id']==iid)
        absent='、'.join(p['short_name'] for p in prov if cv[p['short_name']] in ['missing','pending_verification']) or '无'
        excluded='、'.join(p['short_name'] for p in prov if cv[p['short_name']]=='not_applicable')
        if excluded:absent+='；模型不适用：'+excluded
        same='年度/年末；仍须核源定义' if cv['period']=='2024' else '调查截止月，非年末' if iid.startswith('gov_') and cv['period'].startswith('2024-') else '月度截面，非年末' if cv['period'].startswith('2024-') else '非2024'
        risk='高，见S03专项审计' if iid.startswith('BIMSA') else '嵌套/派生勿重复加权' if iid.startswith('BB_') or iid.startswith('NBS_ECOM') else '待审核'
        report.append(f'|{iid}|{cv["indicator_name"]}|{cv["dimension"]}|{cv["period"]}|{ind["value_type"]}|{cv["numeric_verified_count"]}|{cv["category_verified_count"]}|{absent}|{sids}|{same}|{risk}|{recommendation}；{ind["notes"]}|')
    report += ['','完整逐省状态见 coverage_matrix.csv；空值及排除原因见 missingness.csv。已取得31省也不代表可进入2024三维综合指数。','', '## 五个决策问题','', '1. 哪些真正完整：上表数值/31等于31的行已取得连续数值；年度研究机构指数须与官方原始统计分开，月末宽带须与年末分开。GDP/人口是辅助变量，不直接代表数字化。','2. 哪些只有分档：S08为2025年服务能力档级；S07原链接仅6页节选，未提供可复算的31省得分。','3. 哪些主要反映体量：宽带用户数、基站数、软件业务收入、GDP、人口。千兆占比是结构，亦不等于居民互联网普及率。','4. 哪些可能重复：S03总指数含基础设施和治理；附录分项机械按总分权重拆分，不能用于独立维度；正文产业分项也需说明跨维度内容和来源冲突。','5. 今天能否三维精确排名：尚无合规最小方案。数字政府2024连续数值与实际统计期尚未取得；年末基础设施表仍需补齐。不得用2025档级或5月数据自动拼入2024三维分数。']
    report_text=('\n'.join(report)+'\n').replace('数字政府2024连续数值与实际统计期尚未取得','数字政府2024同模型31省连续数值未齐；S07实际统计截点未知')
    md('reports/data_availability.md',report_text)
    print(json.dumps(dict(sources=len(sources),indicators=len(inds),observations=len(obs),derived=len(derived),missing_records=len(missing)),ensure_ascii=False))
    validate()

def validate():
    con=sqlite3.connect(ROOT/'data/digital_china.sqlite');con.row_factory=sqlite3.Row
    checks=[]
    def ck(name,condition):
        checks.append(dict(check=name,result='PASS' if condition else 'FAIL'))
    ck('31省唯一',con.execute('SELECT COUNT(*),COUNT(DISTINCT province_code) FROM provinces').fetchone()[:]==(31,31))
    ck('四区域10/6/12/3',dict(con.execute('SELECT region_4,COUNT(*) FROM provinces GROUP BY region_4'))=={'东部':10,'中部':6,'西部':12,'东北':3})
    ck('外键完整',not con.execute('PRAGMA foreign_key_check').fetchall())
    ck('SQLite完整性',con.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    ck('档级未转数值',con.execute('SELECT COUNT(*) FROM observations WHERE category_value IS NOT NULL AND numeric_value IS NOT NULL').fetchone()[0]==0)
    ck('全体候选尚未批准',con.execute('SELECT COUNT(*) FROM indicators WHERE include_in_index!=0').fetchone()[0]==0)
    ck('指标与观察值单位一致',con.execute('SELECT COUNT(*) FROM observations o JOIN indicators i USING(indicator_id) WHERE o.unit!=i.unit').fetchone()[0]==0)
    ck('政府调查未伪作完整年度',con.execute("SELECT COUNT(*) FROM observations WHERE indicator_id LIKE 'gov_%' AND period_type='annual'").fetchone()[0]==0)
    ck('逐值定位字段完整',con.execute("SELECT COUNT(*) FROM observations WHERE source_page_or_table='' OR original_label='' OR raw_value='' AND is_derived=0").fetchone()[0]==0)
    for s in con.execute('SELECT DISTINCT s.* FROM sources s JOIN observations o USING(source_id)'):
        p=ROOT/(s['local_path'] or '')
        ck('来源归档hash '+s['source_id'],p.is_file() and sha(p)==s['sha256'])
    rates=con.execute("SELECT numeric_value FROM observations WHERE unit='%' AND numeric_value IS NOT NULL").fetchall()
    ck('百分比0到100',all(0<=r[0]<=100 for r in rates))
    for code, in con.execute('SELECT province_code FROM provinces'):
        b=dict(con.execute("SELECT indicator_id,numeric_value FROM observations WHERE province_code=? AND source_id='S05'",(code,)))
        ck('宽带嵌套 '+code,0<=b['BB_1000M']<=b['BB_100M']<=b['BB_TOTAL'] and 0<=b['BB_FTTH']<=b['BB_TOTAL'])
        ck('派生占比 '+code,abs(b['BB_1000M_SHARE']-100*b['BB_1000M']/b['BB_TOTAL'])<1e-10)
    for r in con.execute('SELECT * FROM derived_values'):
        ids=json.loads(r['input_observation_ids'])
        ck('派生溯源 '+r['observation_id'],all(con.execute('SELECT 1 FROM observations WHERE observation_id=?',(i,)).fetchone() for i in ids))
    dump_csv('reports/validation_checks.csv',checks)
    failures=[r for r in checks if r['result']=='FAIL']
    md('reports/validation_summary.md',f'# 验证结果\n\n检查 {len(checks)} 项，通过 {len(checks)-len(failures)} 项，失败 {len(failures)} 项。\n\n'+('全部必要完整性检查通过。加总差异见 aggregate_checks.csv；该检查不代表指标已获批准。\n' if not failures else json.dumps(failures,ensure_ascii=False)))
    con.close()
    if failures:raise AssertionError(failures)
    print(f'PASS: {len(checks)} checks')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['build','validate'],default='build',nargs='?');args=ap.parse_args()
    build() if args.command=='build' else validate()
