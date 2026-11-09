"""第二阶段研究：单项描述统计与四大区域比较，不生成综合指数。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/figures_stage2'
DATA=ROOT/'data/processed/stage2'
REGIONS=['东部','中部','西部','东北']
COLORS={'东部':'#0072B2','中部':'#E69F00','西部':'#009E73','东北':'#CC79A7'}
plt.rcParams.update({'font.family':'Microsoft YaHei','font.size':11,'axes.titlesize':15,'axes.titleweight':'bold','axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'axes.unicode_minus':False,'savefig.dpi':300})

def save(fig,name):
    fig.savefig(OUT/(name+'.png'),dpi=300,facecolor='white')
    fig.savefig(OUT/(name+'.pdf'),facecolor='white')
    plt.close(fig)
def csv(df,name):df.to_csv(DATA/name,index=False,encoding='utf-8-sig')

def stats(panel,col,iid,period):
    rows=[]
    for region in REGIONS:
        g=panel[panel.region_4==region];s=g[col]
        lo=g.loc[s.idxmin()];hi=g.loc[s.idxmax()]
        rows.append(dict(indicator_id=iid,period=period,region_4=region,n=len(s),mean=s.mean(),median=s.median(),std_population=s.std(ddof=0),cv_pct=s.std(ddof=0)/s.mean()*100,min=s.min(),max=s.max(),range=s.max()-s.min(),min_province=lo.short_name,max_province=hi.short_name))
    return pd.DataFrame(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True)
    p=pd.read_csv(ROOT/'metadata/provinces.csv',dtype={'province_code':str})
    d=pd.read_csv(ROOT/'data/processed/observations_long.csv',dtype={'province_code':str,'period':str})
    d=d[d.verification_status.isin(['source_confirmed','manually_checked'])]
    config=ROOT/'work/stage2_analysis_choice.json'
    choice=json.loads(config.read_text(encoding='utf-8')) if config.exists() else dict(indicator_id='BB_1000M_SHARE',period='2024-05',name='千兆及以上宽带用户占比',unit='%',source_note='工信部2024年5月分省宽带表（S05）；千兆用户数/固定宽带总用户数×100。',time_label='截至2024年5月',limitation='账户速率结构，不等于居民普及率；与企业指标时点不同。')
    def get(iid,period):
        a=d[(d.indicator_id==iid)&(d.period==period)]
        if a.province_code.duplicated().any():raise ValueError('单指标存在来源/版本冲突，须显式选源：'+iid)
        assert len(a)==31 and a.numeric_value.notna().all(),iid
        return a.set_index('province_code').numeric_value
    panel=p.copy()
    panel['ecommerce_share']=panel.province_code.map(get('NBS_ECOM_SHARE','2024'))
    panel['infra_value']=panel.province_code.map(get(choice['indicator_id'],choice['period']))
    for name in ['ecommerce_share','infra_value']:
        panel['rank_'+name]=panel[name].rank(method='min',ascending=False).astype(int)
    panel['single_indicator_rank_gap']=panel.rank_ecommerce_share-panel.rank_infra_value
    cats=d[(d.indicator_id=='gov_online_category')&(d.period=='2024-10')]
    assert len(cats)==31 and cats.category_value.notna().all()
    panel['gov_category_2024']=panel.province_code.map(cats.set_index('province_code').category_value)
    csv(panel,'single_indicator_panel.csv')
    e=stats(panel,'ecommerce_share','NBS_ECOM_SHARE','2024');b=stats(panel,'infra_value',choice['indicator_id'],choice['period'])
    regional=pd.concat([e,b],ignore_index=True)
    # 企业加权率另列，不将它与省份等权均值混称区域总体比例。
    orig=d[(d.period=='2024')&d.indicator_id.isin(['NBS_ENT','NBS_ECOM_ENT'])].pivot(index='province_code',columns='indicator_id',values='numeric_value')
    totals=p.merge(orig,left_on='province_code',right_index=True).groupby('region_4')[['NBS_ENT','NBS_ECOM_ENT']].sum()
    e['enterprise_pooled_share']=[100*totals.loc[r,'NBS_ECOM_ENT']/totals.loc[r,'NBS_ENT'] for r in e.region_4]
    csv(e,'regional_ecommerce_statistics.csv');csv(b,'regional_infrastructure_statistics.csv');csv(regional,'regional_statistics.csv')
    category=pd.crosstab(panel.region_4,panel.gov_category_2024).reindex(index=REGIONS,columns=['优秀','良好','中等'],fill_value=0)
    cat=category.reset_index().melt(id_vars='region_4',var_name='category',value_name='province_count')
    cat['region_n']=cat.region_4.map(panel.groupby('region_4').size())
    cat['share_pct']=cat.province_count/cat.region_n*100
    csv(cat,'government_category_by_region.csv')

    def rankfig(col,title,time,source,name,unit,limitation):
        g=panel.sort_values([col,'display_order'],ascending=[False,True])
        fig,ax=plt.subplots(figsize=(10,12))
        ax.barh(g.short_name,g[col],color=g.region_4.map(COLORS),height=.68)
        ax.invert_yaxis();ax.set_xlim(0,g[col].max()*1.17)
        for i,v in enumerate(g[col]):ax.text(v+g[col].max()*.012,i,f'{v:.2f}',va='center',fontsize=10)
        ax.set_xlabel(unit);ax.set_title(title+'\n'+time+'｜31省单项比较',loc='left',pad=16)
        ax.xaxis.grid(True,alpha=.15);ax.set_axisbelow(True)
        ax.legend(handles=[Patch(color=COLORS[r],label=r) for r in REGIONS],loc='lower right',frameon=False)
        fig.text(.11,.052,'来源：'+source,fontsize=8.8)
        fig.text(.11,.030,limitation,fontsize=8.8,color='#555555')
        fig.subplots_adjust(left=.11,right=.96,top=.91,bottom=.11)
        save(fig,name)
    rankfig('ecommerce_share','调查企业电子商务参与比例','2024全年','国家统计局《中国统计年鉴2025》表16-39（E02）；电商企业数/调查企业数×100；作者计算。','01_ecommerce_share_2024','调查企业电商参与比例（%）','调查范围为一套表企业；不代表所有企业或数字经济规模；并列按同位次处理。')
    rankfig('infra_value',choice['name'],choice['time_label'],choice['source_note'],'02_infrastructure_single_indicator',choice['name']+'（'+choice['unit']+'）',choice['limitation'])

    fig,axes=plt.subplots(1,2,figsize=(14,6.6))
    for ax,col,st,title,unit in [(axes[0],'ecommerce_share',e,'调查企业电子商务参与比例｜2024全年','%'),(axes[1],'infra_value',b,choice['name']+'｜'+choice['time_label'],choice['unit'])]:
        for x,r in enumerate(REGIONS):
            g=panel[panel.region_4==r].sort_values('display_order')
            jitter=np.linspace(-.13,.13,len(g))
            ax.scatter(x+jitter,g[col],c=COLORS[r],s=34,alpha=.72,zorder=3)
            row=st[st.region_4==r].iloc[0]
            ax.plot([x-.25,x+.25],[row['mean']]*2,color='#20262d',lw=2.2,zorder=4)
            ax.scatter(x,row['median'],marker='D',s=42,facecolors='white',edgecolors='#20262d',zorder=5)
            ax.annotate(f'均值 {row["mean"]:.2f}',(x,row['max']),xytext=(0,13),textcoords='offset points',ha='center',fontsize=9)
        ax.set_xticks(range(4),[f'{r}\n(n={sum(panel.region_4==r)})' for r in REGIONS]);ax.set_ylabel(unit);ax.set_title(title,fontsize=12,pad=17)
        ax.set_ylim(0,panel[col].max()*1.2);ax.yaxis.grid(True,alpha=.16);ax.set_axisbelow(True)
    fig.text(.07,.075,'圆点：每个省份；黑横线：省份等权均值；空心菱形：中位数。31省为比较总体，标准差使用ddof=0。',fontsize=9)
    fig.text(.07,.046,'来源：国家统计局年鉴表16-39（E02）与所选基础设施原表；作者计算。各分项分别展示，不合成总分。',fontsize=9)
    fig.text(.07,.018,'基础设施来源及期间：'+choice['source_note']+' '+choice['time_label'],fontsize=8)
    fig.subplots_adjust(left=.07,right=.97,bottom=.20,top=.87,wspace=.25)
    save(fig,'03_regional_distributions')

    fig,ax=plt.subplots(figsize=(11,6.4));left=np.zeros(4)
    catcolors={'优秀':'#0072B2','良好':'#56B4E9','中等':'#E69F00'}
    for c in ['优秀','良好','中等']:
        counts=category[c].to_numpy();pct=counts/category.sum(axis=1).to_numpy()*100
        ax.barh(REGIONS,pct,left=left,color=catcolors[c],label=c,height=.58)
        for y,(n,v,start) in enumerate(zip(counts,pct,left)):
            if n:ax.text(start+v/2,y,f'{n}省\n{v:.1f}%',ha='center',va='center',color='white' if c=='优秀' else '#17232c',fontsize=12)
        left+=pct
    ax.invert_yaxis();ax.set_xlim(0,100);ax.set_xlabel('区域内省份占比（%）')
    ax.set_title('省级网上政府评价档级的区域分布\n2024年9月上旬至10月上旬调查｜31省',loc='left',pad=18)
    ax.legend(ncol=3,frameon=False,loc='lower right',bbox_to_anchor=(1,-.26))
    fig.text(.12,.065,'来源：清华《2024年网上政府创新发展报告》PDF58/印刷52页（S27）；作者计数；兵团排除。',fontsize=9)
    fig.text(.12,.025,'档级仅展示类别，不转换连续分数或计算均值；各区域省数为东10、中6、西12、东北3。',fontsize=9)
    fig.subplots_adjust(left=.12,right=.97,top=.80,bottom=.25)
    save(fig,'04_government_categories_2024')

    rho=np.corrcoef(panel.ecommerce_share.rank(),panel.infra_value.rank())[0,1]
    es=panel.sort_values('ecommerce_share',ascending=False);bs=panel.sort_values('infra_value',ascending=False)
    diff=panel.loc[panel.single_indicator_rank_gap.abs().sort_values(ascending=False).index].head(6).copy()
    csv(diff,'case_candidates.csv')
    facts=dict(infrastructure=choice,ecommerce_top=es.head(3)[['short_name','ecommerce_share']].to_dict('records'),ecommerce_bottom=es.tail(3)[['short_name','ecommerce_share']].to_dict('records'),infra_top=bs.head(3)[['short_name','infra_value']].to_dict('records'),infra_bottom=bs.tail(3)[['short_name','infra_value']].to_dict('records'),region_ecommerce=e.to_dict('records'),region_infra=b.to_dict('records'),government=cat.to_dict('records'),spearman_exploratory=float(rho),case_candidates=diff.to_dict('records'))
    (DATA/'analysis_facts.json').write_text(json.dumps(facts,ensure_ascii=False,indent=2),encoding='utf-8')
    # 每图50—150字事实解读，原因另待后续案例证据。
    eorder='、'.join(e.sort_values('mean',ascending=False).region_4)
    border='、'.join(b.sort_values('mean',ascending=False).region_4)
    cmax=e.loc[e['range'].idxmax()];bmax=b.loc[b['range'].idxmax()]
    descriptions=[
      ('01_ecommerce_share_2024',f'2024年调查企业电商参与比例中，{es.iloc[0].short_name}为{es.iloc[0].ecommerce_share:.2f}%，{es.iloc[-1].short_name}为{es.iloc[-1].ecommerce_share:.2f}%，相差{es.iloc[0].ecommerce_share-es.iloc[-1].ecommerce_share:.2f}个百分点。这里比较的是调查企业应用比例，不能解释为数字经济规模或所有企业普及率。'),
      ('02_infrastructure_single_indicator',f'{choice["time_label"]}，{choice["name"]}最高为{bs.iloc[0].short_name}（{bs.iloc[0].infra_value:.2f}{choice["unit"]}），最低为{bs.iloc[-1].short_name}（{bs.iloc[-1].infra_value:.2f}{choice["unit"]}）。该结果只对应这一设施代理，不能代表整个数字基础设施维度。'),
      ('03_regional_distributions',f'按省份等权均值，电商参与比例的区域顺序为{eorder}，基础设施代理的顺序为{border}。电商区域内极差最大的是{cmax.region_4}（{cmax["range"]:.2f}个百分点），显示区域均值不能替代省份分布。不同统计期仅作探索对照。'),
      ('04_government_categories_2024',f'31省网上政府档级为优秀{int(category["优秀"].sum())}省、良好{int(category["良好"].sum())}省、中等{int(category["中等"].sum())}省。区域图按各区域省数计算占比，东北只有3省。档级用于类别比较，不能推出档内排序、精确得分或区域平均政府分。')]
    lines=['# 第二阶段分项预分析','', '本报告仅比较各分项，不生成数字现代化总分。排序采用未四舍五入原值，若并列取相同最小名次；图中文字保留两位小数。区域均值为省份等权均值，企业加权比例另列，不混称。','']
    for name,desc in descriptions:lines += [f'## {name}','',f'![{name}](figures_stage2/{name}.png)','',desc,'']
    lines += ['## 结构差异与候选案例','',f'两个连续分项的省际Spearman相关系数为{rho:.3f}，仅作描述性探索；统计期不同，不能解释为严格同期关系，更不能推断因果。案例候选按两项单指标名次绝对差前6位选出，数据见case_candidates.csv；尚未确定最终案例。','', '|省份|区域|电商比例%|电商单项名次|设施代理值|设施单项名次|名次差（电商−设施）|','|---|---|---:|---:|---:|---:|---:|']
    for r in diff.itertuples():lines.append(f'|{r.short_name}|{r.region_4}|{r.ecommerce_share:.2f}|{r.rank_ecommerce_share}|{r.infra_value:.2f}|{r.rank_infra_value}|{r.single_indicator_rank_gap}|')
    lines += ['','候选只提示两个代理指标不同步，不能称发展失衡或成功路径。后续须结合原统计范围、行业结构与官方案例材料解释。区域统计、类别计数、完整31省值及脚本均保留，未对档级进行数值化。']
    (ROOT/'reports/stage2_preanalysis.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({'figures':4,'regional_order_ecommerce':eorder,'regional_order_infrastructure':border,'rho':rho,'infra':choice['indicator_id']},ensure_ascii=False))
if __name__=='__main__':main()
