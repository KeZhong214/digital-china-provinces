"""指标有效性所需的有限描述统计；不构建综合分或正式排名。"""
from pathlib import Path
import hashlib, json
from itertools import combinations
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/processed/stage3';FIG=ROOT/'reports/figures_stage3'
REGIONS=['东部','中部','西部','东北']
COLORS={'东部':'#0072B2','中部':'#E69F00','西部':'#009E73','东北':'#CC79A7'}
LABELS={'ecommerce':'调查企业电商参与比例（%）','ict_structure':'信息服务业法人单位占比（%）','accounts':'每百人固定宽带账户数（户/百人）','ports':'每百人宽带端口数（个/百人）'}
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':11,'axes.titlesize':14,'axes.titleweight':'bold','axes.spines.top':False,'axes.spines.right':False,'axes.unicode_minus':False,'pdf.fonttype':42})
def save(fig,name):
    fig.savefig(FIG/(name+'.png'),dpi=300,facecolor='white');fig.savefig(FIG/(name+'.pdf'),facecolor='white');plt.close(fig)
def csv(df,name):df.to_csv(DATA/name,index=False,encoding='utf-8-sig')
def corr(x,y,method):return float(np.corrcoef(x.rank() if method=='spearman' else x,y.rank() if method=='spearman' else y)[0,1])
def main():
    DATA.mkdir(exist_ok=True,parents=True);FIG.mkdir(exist_ok=True,parents=True)
    d=pd.read_csv(ROOT/'data/processed/observations_long.csv',dtype={'province_code':str,'period':str})
    p=pd.read_csv(ROOT/'metadata/provinces.csv',dtype={'province_code':str})
    def get(iid):
        a=d[(d.indicator_id==iid)&(d.period=='2024')]
        assert len(a)==31 and not a.province_code.duplicated().any()
        return a.set_index('province_code')
    table=p.copy()
    for col,iid in [('ecommerce','NBS_ECOM_SHARE'),('ict_structure','NBS_ICT_LEGAL_SHARE'),('accounts','BB_ACCOUNTS_PER100')]:table[col]=table.province_code.map(get(iid).numeric_value)
    ports=get('NBS_BB_PORTS_YEAR_END');pop=get('population_year_end');new=[]
    for r in p.itertuples():
        a=ports.loc[r.province_code];b=pop.loc[r.province_code]
        value=float(a.numeric_value/b.numeric_value*100)
        oid=hashlib.sha256(('stage3_ports_per100|'+r.province_code).encode()).hexdigest()[:24]
        new.append(dict(observation_id=oid,province_code=r.province_code,province=r.short_name,indicator_id='BB_PORTS_PER100',period='2024',period_start='2024-12-31',period_end='2024-12-31',period_type='year_end',numeric_value=value,unit='个/百人',formula='NBS_BB_PORTS_YEAR_END / population_year_end * 100',input_observation_ids=json.dumps([a.observation_id,b.observation_id]),source_ids='I203;A01',source_url='https://www.stats.gov.cn/sj/ndsj/2025/html/C16-36.jpg ; https://www.stats.gov.cn/sj/ndsj/2025/html/C02-05.jpg',source_page_or_table='年鉴2025表16-36宽带接入端口、表2-5年末人口',source_raw_values=f'{a.raw_value}万个 / {b.raw_value}万人',data_status='阶段3新派生；输入原值阶段2及之前已得',is_derived=1,verification_status='source_confirmed',qc_note='端口供给配置，不是用户/覆盖/网速；可大于100，不截断。'))
    derived=pd.DataFrame(new);csv(derived,'derived_ports_per100_long.csv')
    table['ports']=table.province_code.map(derived.set_index('province_code').numeric_value)
    for col in LABELS:table['rank_'+col]=table[col].rank(method='min',ascending=False).astype(int)
    table['rank_gap_ecommerce_ict']=table.rank_ecommerce-table.rank_ict_structure
    table['rank_gap_accounts_ports']=table.rank_accounts-table.rank_ports
    csv(table,'indicator_review_panel_2024.csv')
    cor=[]
    for a,b in combinations(LABELS,2):cor.append(dict(indicator_x=a,indicator_y=b,n=31,pearson=corr(table[a],table[b],'pearson'),spearman=corr(table[a],table[b],'spearman'),time_note='2024全年企业应用/2024年度法人结构/2024年末设施；非严格同日，不作因果'))
    cor=pd.DataFrame(cor);csv(cor,'indicator_correlations.csv')
    # 删除一省只作为区域统计影响诊断，不是抽样置信区间。
    loo=[];regional=[]
    for metric in LABELS:
        for region in REGIONS:
            g=table[table.region_4==region];values=g[metric]
            deletes=[]
            for r in g.itertuples():
                v=g[g.province_code!=r.province_code][metric].mean();deletes.append(v)
                loo.append(dict(metric=metric,region=region,deleted_province=r.short_name,remaining_n=len(g)-1,mean_after_delete=v,original_mean=values.mean(),delta=v-values.mean()))
            regional.append(dict(metric=metric,region=region,n=len(g),mean=values.mean(),median=values.median(),minimum=values.min(),maximum=values.max(),std_population=values.std(ddof=0),loo_mean_min=min(deletes),loo_mean_max=max(deletes)))
    regional=pd.DataFrame(regional);csv(regional,'regional_review_statistics.csv');csv(pd.DataFrame(loo),'leave_one_province_out.csv')
    # 仅检验中西次序是否由少数省影响，无概率或因果含义。
    ordering=[]
    for metric in ['ecommerce','accounts']:
        west=table[table.region_4=='西部'];central=table[table.region_4=='中部']
        ordering.append(dict(metric=metric,scenario='原全样本均值',west_mean=west[metric].mean(),central_mean=central[metric].mean(),gap_west_minus_central=west[metric].mean()-central[metric].mean()))
        for r in west.itertuples():
            w=west[west.province_code!=r.province_code][metric].mean()
            ordering.append(dict(metric=metric,scenario='仅删西部'+r.short_name,west_mean=w,central_mean=central[metric].mean(),gap_west_minus_central=w-central[metric].mean()))
    csv(pd.DataFrame(ordering),'west_central_influence_diagnostic.csv')

    fig,ax=plt.subplots(figsize=(10,7))
    for region in REGIONS:
        g=table[table.region_4==region];ax.scatter(g.accounts,g.ecommerce,s=65,label=region,c=COLORS[region],alpha=.82,edgecolors='white',linewidth=.6)
    selected=['北京','广东','河北','海南','重庆','宁夏','天津','吉林']
    offsets={'北京':(7,6),'广东':(8,7),'河北':(-34,-15),'海南':(-25,8),'重庆':(7,8),'宁夏':(7,-15),'天津':(5,-18),'吉林':(6,-12)}
    for r in table[table.short_name.isin(selected)].itertuples():ax.annotate(r.short_name,(r.accounts,r.ecommerce),xytext=offsets[r.short_name],textcoords='offset points',fontsize=10)
    ax.set_xlabel(LABELS['accounts']);ax.set_ylabel(LABELS['ecommerce']);ax.grid(alpha=.13);ax.legend(frameon=False,ncol=4,loc='lower right')
    ax.set_title('企业交易应用与固定宽带账户配置的省际对照\n2024全年应用 × 2024年末账户｜31省｜非综合发展名次',loc='left',pad=16)
    fig.text(.12,.065,'来源：国家统计局年鉴2025表16-39（E02）、16-36（I203）、2-5（A01）；作者按同表/同版原值计算。',fontsize=9)
    fig.text(.12,.025,'账户包括家庭与机构；图只比较两个代理，不推断网速、居民去重普及率或因果。',fontsize=9)
    fig.subplots_adjust(left=.12,right=.97,top=.82,bottom=.17);save(fig,'01_application_accounts_scatter')

    fig,axes=plt.subplots(1,2,figsize=(14,6.8))
    for ax,x,y,title in [(axes[0],'ecommerce','ict_structure','D1：应用与行业组织结构'),(axes[1],'accounts','ports','D2：账户与端口配置')]:
        for region in REGIONS:
            g=table[table.region_4==region];ax.scatter(g[x],g[y],s=43,c=COLORS[region],alpha=.8,label=region)
        rho=corr(table[x],table[y],'spearman');ax.set_title(title+f'\nSpearman ρ={rho:.3f}；n=31',fontsize=13)
        for r in table[table.short_name.isin(['广东','海南','北京'])].itertuples():ax.annotate(r.short_name,(getattr(r,x),getattr(r,y)),xytext=(5,6),textcoords='offset points',fontsize=9)
        ax.set_xlabel(LABELS[x],fontsize=10);ax.set_ylabel(LABELS[y],fontsize=10);ax.grid(alpha=.13)
    axes[0].legend(ncol=4,loc='upper left',frameon=False,fontsize=8)
    fig.text(.07,.073,'左：2024年度，E02企业电商/调查企业；E201信息服务业法人/全部法人。右：2024年末，I203各原值/A01人口×100。',fontsize=9)
    fig.text(.07,.038,'来源：国家统计局年鉴2025表16-39、1-5、16-36、2-5；作者计算。低相关不自动代表有效，高相关也不单独证明重复。',fontsize=9)
    fig.subplots_adjust(left=.07,right=.97,top=.82,bottom=.21,wspace=.28);save(fig,'02_candidate_validity_comparisons')

    fig,axes=plt.subplots(1,2,figsize=(13.5,6.6))
    for ax,metric,title in [(axes[0],'ecommerce','调查企业电商参与比例｜2024全年'),(axes[1],'accounts','每百人宽带账户｜2024年末')]:
        for i,region in enumerate(REGIONS):
            r=regional[(regional.metric==metric)&(regional.region==region)].iloc[0]
            ax.plot([r.loo_mean_min,r.loo_mean_max],[i,i],color=COLORS[region],lw=5,alpha=.6)
            ax.scatter(r['mean'],i,s=55,c=COLORS[region],zorder=4)
            ax.scatter(r['median'],i,marker='D',s=45,facecolors='white',edgecolors='black',zorder=5)
            from matplotlib.transforms import blended_transform_factory
            ax.text(.025,i+.25,f'均值{r["mean"]:.2f} / 中位{r["median"]:.2f}',fontsize=9,transform=blended_transform_factory(ax.transAxes,ax.transData))
        ax.set_yticks(range(4),[f'{r}（n={sum(table.region_4==r)}）' for r in REGIONS]);ax.invert_yaxis();ax.set_ylim(3.6,-.6)
        ax.set_xlabel(LABELS[metric]);ax.set_title(title,fontsize=12);ax.xaxis.grid(alpha=.15)
        ax.margins(x=.24)
    fig.suptitle('区域排序对中心统计量和单省影响的敏感性',x=.07,ha='left',fontsize=16,fontweight='bold')
    fig.text(.07,.070,'圆点：原区域均值；菱形：中位数；粗线：区域内每次删一省后均值的最小—最大范围。不是置信区间，不是综合排名。',fontsize=9)
    fig.text(.07,.034,'来源：国家统计局年鉴2025表16-39、16-36、2-5；作者计算。只诊断描述统计对个别省份的敏感性。',fontsize=9)
    fig.subplots_adjust(left=.10,right=.98,top=.82,bottom=.20,wspace=.42);save(fig,'03_regional_influence_diagnostic')
    out=dict(correlations=cor.to_dict('records'),regional_statistics=regional.to_dict('records'),d1_rank_changes=table.loc[table.rank_gap_ecommerce_ict.abs().sort_values(ascending=False).index,['short_name','ecommerce','ict_structure','rank_ecommerce','rank_ict_structure','rank_gap_ecommerce_ict']].head(8).to_dict('records'),d2_rank_changes=table.loc[table.rank_gap_accounts_ports.abs().sort_values(ascending=False).index,['short_name','accounts','ports','rank_accounts','rank_ports','rank_gap_accounts_ports']].head(8).to_dict('records'),west_central=ordering,derived_new_count=31,new_collected_full31_count=0)
    (DATA/'analysis_facts.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'correlations':out['correlations'],'d1_largest_changes':out['d1_rank_changes'][:3],'d2_largest_changes':out['d2_rank_changes'][:3]},ensure_ascii=False))
if __name__=='__main__':main()
