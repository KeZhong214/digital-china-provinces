"""公开来源下载探查，不绕过访问限制。"""
import requests, json, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[1]
URLS={
 'S05_wap':'https://wap.miit.gov.cn/gxsj/tjfx/hlw/art/2024/art_562bd2a7a52a42c7971b7059f4100d81.html',
 'annual_note':'https://www.miit.gov.cn/txnj2024/tx/编者说明.html',
 'annual_home':'https://www.miit.gov.cn/txnj2024/',
 'annual_table':'https://www.miit.gov.cn/txnj2024/tx/2-3.html',
 'S06':'https://www.miit.gov.cn/gxsj/tjfx/txy/art/2025/art_641c048c5d4f4e308098bf6c4e3dcb4a.html',
}
def fetch(item):
 k,u=item
 try:
  r=requests.get(u,timeout=25)
  p=ROOT/'data/raw'/f'{k}.html'
  p.write_bytes(r.content)
  return dict(id=k,url=u,status=r.status_code,bytes=len(r.content),path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(r.content).hexdigest())
 except Exception as e:return dict(id=k,url=u,error=str(e))
if __name__=='__main__':
 rows=list(ThreadPoolExecutor(4).map(fetch,URLS.items()))
 (ROOT/'logs/probe_sources.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(rows,ensure_ascii=False,indent=2))
