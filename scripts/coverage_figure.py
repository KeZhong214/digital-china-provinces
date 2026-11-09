"""覆盖率诊断图；不是发展水平/排名图。"""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=pd.read_csv(ROOT/'metadata/provinces.csv')
    c=pd.read_csv(ROOT/'reports/coverage_matrix.csv',dtype=str)
    c=c[c.period.str.startswith(('2024','2025'))].copy()
    # 只展示每个候选的主截面和明确的非同年政府档级，避免多年指数挤占视图。
    c=c.drop_duplicates(['indicator_id','period'])
    names=p.short_name.tolist(); codes={'missing':0,'not_applicable':0,'pending_verification':1,'category_verified':2,'numeric_verified':3}
    a=c[names].replace(codes).astype(int).to_numpy()
    plt.rcParams['font.family']='Microsoft YaHei'
    fig,ax=plt.subplots(figsize=(15,max(8,len(c)*.31)))
    ax.imshow(a,cmap=ListedColormap(['#e7ebef','#ecb454','#a99bd2','#237c89']),vmin=0,vmax=3,aspect='auto')
    ax.set_xticks(range(31),names,rotation=90,fontsize=9)
    ax.set_yticks(range(len(c)),[f'{r.indicator_name} | {r.period}' for r in c.itertuples()],fontsize=9)
    ax.set_title('31省候选数据覆盖情况\n颜色表示可得性，不表示发展水平；所有指标尚未批准计分',loc='left',fontsize=16,pad=18)
    ax.set_xticks([x-.5 for x in range(32)],minor=True);ax.set_yticks([x-.5 for x in range(len(c)+1)],minor=True)
    ax.grid(which='minor',color='white',linewidth=.7);ax.tick_params(which='minor',length=0)
    ax.legend(handles=[Patch(facecolor=color,label=label) for color,label in [('#237c89','已核验连续数值'),('#a99bd2','仅档级'),('#ecb454','待核验'),('#e7ebef','未取得或模型不适用')]],loc='upper left',bbox_to_anchor=(0,-.075),ncol=4,frameon=False)
    fig.text(.02,.012,'来源：本项目逐值来源台账及核验记录；作者整理。核验日期：2026-11-09。详见 coverage_matrix.csv。',fontsize=9,color='#52606d')
    fig.subplots_adjust(left=.35,right=.98,top=.91,bottom=.13)
    fig.savefig(ROOT/'reports/coverage_heatmap.png',dpi=160,facecolor='white');plt.close(fig)
if __name__=='__main__': main()
