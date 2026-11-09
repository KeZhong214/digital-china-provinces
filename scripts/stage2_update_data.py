"""第二阶段采集结果入现有候选库；保留第一阶段快照，不改变既有表结构。"""
from pathlib import Path
import csv, json, sqlite3, hashlib, re
from pipeline import normalize_source, normalize_obs, insert_rows, dump_csv, provinces

ROOT=Path(__file__).resolve().parents[1]
FOLDERS=['stage2_government','stage2_infrastructure','stage2_economy']
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def main():
    con=sqlite3.connect(ROOT/'data/digital_china.sqlite');con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    p=provinces();mapping={name:r['province_code'] for r in p for name in [r['short_name'],r['province_name']]}
    sources=[];observations=[];newind=[];logs=[]
    for folder in FOLDERS:
        directory=ROOT/'work'/folder
        for fname,target in [('sources.json',sources),('observations.json',observations),('indicators.json',newind),('search_log.json',logs)]:
            path=directory/fname
            if path.exists():target.extend(load(path))
    for raw in sources:
        s=normalize_source(raw)
        if con.execute('SELECT 1 FROM sources WHERE source_id=?',(s['source_id'],)).fetchone():continue
        insert_rows(con,'sources',[s])
        insert_rows(con,'source_audit',[dict(audit_id='stage2_'+s['source_id'],source_id=s['source_id'],audited_at='2026-11-09',auditor='Codex',method='source_retrieval_and_table_review',finding=s.get('citation_note',''),evidence_path=s.get('local_path',''))])
    for raw in newind:
        r=dict(raw);iid=r['indicator_id'];note=r.get('definition',r.get('notes',''))
        year=str(r['candidate_period'])[:4] if re.match(r'^\d{4}',str(r['candidate_period'])) else ''
        row=dict(indicator_id=iid,indicator_name=r.get('name',r.get('indicator_name',iid)),dimension=r['dimension'],definition=note,unit=r['unit'],direction=r.get('direction','positive'),value_type=r['value_type'],numerator_id=r.get('numerator_id',''),denominator_id=r.get('denominator_id',''),candidate_year=year,source_priority='official_then_research',expected_coverage=r.get('expected_coverage',31),include_in_index=0,approval_status='pending_researcher_review',notes=r.get('notes',note))
        if con.execute('SELECT 1 FROM indicators WHERE indicator_id=?',(iid,)).fetchone():
            con.execute('UPDATE indicators SET indicator_name=?,definition=?,unit=?,notes=?,candidate_year=? WHERE indicator_id=?',(row['indicator_name'],row['definition'],row['unit'],row['notes'],row['candidate_year'],iid))
        else:insert_rows(con,'indicators',[row])
    count=0
    for raw in observations:
        if raw.get('is_derived'):raise ValueError('新派生值必须另给输入ID，不直接混原值')
        o=normalize_obs({**raw,'data_version':raw.get('data_version','stage2_source_archived_2026-11-09')},mapping)
        if o['verification_status'] not in ['source_confirmed','manually_checked']:raise ValueError('未核验值不能并入此轮核验表')
        if con.execute('SELECT 1 FROM observations WHERE observation_id=?',(o['observation_id'],)).fetchone():continue
        insert_rows(con,'observations',[o]);count+=1
    # 同版同年末账户密度，万户/万人单位相消；不是居民普及率。
    definitions=[]
    if con.execute("SELECT COUNT(*) FROM observations WHERE indicator_id='BB_TOTAL_YEAR_END' AND numeric_value IS NOT NULL").fetchone()[0]==31:
        definitions.append(dict(iid='BB_ACCOUNTS_PER100',name='每百人固定宽带账户数',dimension='D2',unit='户/百人',num='BB_TOTAL_YEAR_END',den='population_year_end',factor=100,note='2024年末固定宽带用户账户数/同版年末常住人口×100；包含家庭及机构账户，不等于居民普及率。'))
    choice=ROOT/'work/stage2_derived_definitions.json'
    if choice.exists():definitions.extend(load(choice))
    derived_count=0
    for spec in definitions:
        iid=spec['iid'];num=spec['num'];den=spec['den']
        if not con.execute('SELECT 1 FROM indicators WHERE indicator_id=?',(iid,)).fetchone():
            insert_rows(con,'indicators',[dict(indicator_id=iid,indicator_name=spec['name'],dimension=spec['dimension'],definition=spec['note'],unit=spec['unit'],direction='positive',value_type=spec.get('value_type','rate'),numerator_id=num,denominator_id=den,candidate_year='2024',source_priority='official_same_edition',expected_coverage=31,include_in_index=0,approval_status='pending_researcher_review',notes=spec['note'])])
        for r in p:
            a=con.execute('SELECT * FROM observations WHERE province_code=? AND indicator_id=? AND period=?',(r['province_code'],num,'2024')).fetchall()
            b=con.execute('SELECT * FROM observations WHERE province_code=? AND indicator_id=? AND period=?',(r['province_code'],den,'2024')).fetchall()
            if len(a)!=1 or len(b)!=1:raise ValueError(f'派生输入未唯一：{r["short_name"]}/{iid}')
            a,b=a[0],b[0]
            o=normalize_obs(dict(province=r['short_name'],indicator_id=iid,period='2024',period_type='year_end' if spec['dimension']=='D2' else spec.get('period_type',a['period_type']),period_start='2024-12-31' if spec['dimension']=='D2' else a['period_start'],period_end='2024-12-31' if spec['dimension']=='D2' else a['period_end'],raw_value='',numeric_value=a['numeric_value']/b['numeric_value']*spec['factor'],unit=spec['unit'],source_id=a['source_id'],source_page_or_table='作者计算；分子 '+a['source_page_or_table']+'；分母 '+b['source_page_or_table'],original_label=spec['name'],extraction_method='derived_from_verified_source_values',verification_status='source_confirmed',qc_note=spec['note'],data_version='stage2_derived_v1'),mapping)
            o.update(is_derived=1,formula_id=iid+'_v1')
            if con.execute('SELECT 1 FROM observations WHERE observation_id=?',(o['observation_id'],)).fetchone():continue
            insert_rows(con,'observations',[o]);derived_count+=1
            insert_rows(con,'derived_values',[dict(observation_id=o['observation_id'],formula=f'{num} / {den} * {spec["factor"]}',input_observation_ids=json.dumps([a['observation_id'],b['observation_id']]),calculation_version='stage2_v1',qc_status='verified_inputs')])
    # 删除仅限已填齐指标、同统计期的旧缺失占位，不删除原观察值。
    con.execute('DELETE FROM missingness WHERE EXISTS(SELECT 1 FROM observations o WHERE o.province_code=missingness.province_code AND o.indicator_id=missingness.indicator_id AND o.period=missingness.period AND o.numeric_value IS NOT NULL)')
    con.commit()
    for table,path in [('sources','metadata/sources.csv'),('indicators','metadata/indicators.csv'),('observations','data/processed/observations_long.csv'),('derived_values','data/processed/derived_values.csv'),('missingness','reports/missingness.csv')]:
        dump_csv(path,[dict(r) for r in con.execute('SELECT * FROM '+table)])
    obs=[dict(r) for r in con.execute('SELECT * FROM observations')]
    inds=[dict(r) for r in con.execute('SELECT * FROM indicators')]
    maps=[dict(source_id=sid,indicator_id=iid,relation='derived' if derived else 'observed') for sid,iid,derived in sorted({(o['source_id'],o['indicator_id'],o['is_derived']) for o in obs})]
    for r in con.execute('SELECT d.input_observation_ids,o.indicator_id,o.source_id FROM derived_values d JOIN observations o USING(observation_id)'):
        for oid in json.loads(r['input_observation_ids']):
            source=con.execute('SELECT source_id FROM observations WHERE observation_id=?',(oid,)).fetchone()[0]
            relation=dict(source_id=source,indicator_id=r['indicator_id'],relation='derived_input')
            if source!=r['source_id'] and relation not in maps:maps.append(relation)
    dump_csv('metadata/source_indicator_map.csv',maps)
    panel=[]
    for r in p:
        row=dict(r)
        for o in obs:
            if o['province_code']==r['province_code'] and o['period']=='2024' and o['verification_status'] in ['source_confirmed','manually_checked']:
                row[o['indicator_id']+'__'+o['source_id']+'__'+o['data_version']]=o['numeric_value'] if o['numeric_value'] is not None else o['category_value']
        panel.append(row)
    dump_csv('data/processed/candidate_panel_2024.csv',panel)
    # 新数据31省核对表，列名带来源，保留空值而不是补齐。
    newids={r['indicator_id'] for r in observations}|{r['iid'] for r in definitions}
    checkpanel=[]
    for r in p:
        row=dict(r)
        for o in obs:
            if o['province_code']==r['province_code'] and o['indicator_id'] in newids:
                row[o['indicator_id']+'__'+o['period']+'__'+o['source_id']]=o['numeric_value'] if o['numeric_value'] is not None else o['category_value']
        checkpanel.append(row)
    dump_csv('data/processed/stage2/new_values_31_provinces.csv',checkpanel)
    coverage=[]
    oldmissing={(r['province_code'],r['indicator_id'],r['period']):r['reason_code'] for r in con.execute('SELECT * FROM missingness')}
    for ind in inds:
        iid=ind['indicator_id'];items=[o for o in obs if o['indicator_id']==iid]
        periods=sorted({o['period'] for o in items}|({str(ind['candidate_year'])} if not items else set()))
        for period in periods:
            row=dict(indicator_id=iid,indicator_name=ind['indicator_name'],dimension=ind['dimension'],period=period)
            for r in p:
                values=[o for o in items if o['period']==period and o['province_code']==r['province_code']]
                row[r['short_name']]='numeric_verified' if any(o['numeric_value'] is not None for o in values) else 'category_verified' if any(o['category_value'] is not None for o in values) else 'not_applicable' if oldmissing.get((r['province_code'],iid,period))=='not_applicable' else 'missing'
            row['numeric_verified_count']=sum(row[r['short_name']]=='numeric_verified' for r in p)
            row['category_verified_count']=sum(row[r['short_name']]=='category_verified' for r in p)
            coverage.append(row)
    dump_csv('reports/coverage_matrix.csv',coverage)
    checks=[]
    def ck(name,result):checks.append(dict(check=name,result='PASS' if result else 'FAIL'))
    ck('原1041条记录全部保留',all(con.execute('SELECT 1 FROM observations WHERE observation_id=?',(r['observation_id'],)).fetchone() for r in csv.DictReader((ROOT/'work/stage2_baseline/observations_long.csv').open(encoding='utf-8-sig'))))
    ck('所有外键有效',not con.execute('PRAGMA foreign_key_check').fetchall())
    ck('完整性',con.execute('PRAGMA integrity_check').fetchone()[0]=='ok')
    ck('无档级数值化',con.execute('SELECT COUNT(*) FROM observations WHERE category_value IS NOT NULL AND numeric_value IS NOT NULL').fetchone()[0]==0)
    ck('未批准综合计分',con.execute('SELECT COUNT(*) FROM indicators WHERE include_in_index<>0').fetchone()[0]==0)
    ck('无综合排名文件',not (ROOT/'data/processed/province_rankings.csv').exists() and not (ROOT/'data/processed/province_scores.csv').exists())
    for s in con.execute('SELECT DISTINCT s.* FROM sources s JOIN observations o USING(source_id)'):
        path=ROOT/s['local_path'];ck('来源归档 '+s['source_id'],path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==s['sha256'])
    for r in con.execute('SELECT * FROM derived_values'):
        ids=json.loads(r['input_observation_ids']);ck('派生输入 '+r['observation_id'],all(con.execute('SELECT 1 FROM observations WHERE observation_id=?',(k,)).fetchone() for k in ids))
    dump_csv('reports/stage2_validation_checks.csv',checks)
    assert all(r['result']=='PASS' for r in checks),checks
    summary=dict(stage2_registered_sources=len(sources),stage2_raw_observations=len(observations),stage2_derived_observations=con.execute("SELECT COUNT(*) FROM observations WHERE data_version='stage2_derived_v1'").fetchone()[0],inserted_raw_this_run=count,inserted_derived_this_run=derived_count,all_sources=con.execute('SELECT COUNT(*) FROM sources').fetchone()[0],all_observations=len(obs),all_indicators=len(inds),checks=len(checks),new_indicator_ids=sorted(newids))
    (ROOT/'work/stage2_update_result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False));con.close()
if __name__=='__main__':main()
