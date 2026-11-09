"""按来源台账补下载；新文件用内容hash命名，绝不覆盖既有归档。"""
import csv, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    ids=set(sys.argv[1:])
    if not ids:raise SystemExit('请指定 source_id，如 python scripts/fetch_sources.py S05；不会自动批量请求所有站点。')
    log=ROOT/'logs/fetch_log.csv'
    fields=['fetched_at','source_id','url','http_status','status','local_path','sha256','error']
    with (ROOT/'metadata/sources.csv').open(encoding='utf-8-sig') as f: sources=list(csv.DictReader(f))
    for s in sources:
        if s['source_id'] not in ids:continue
        row=dict(fetched_at=datetime.now(timezone.utc).isoformat(),source_id=s['source_id'],url=s['source_url'])
        try:
            r=requests.get(s['source_url'],timeout=30)
            h=hashlib.sha256(r.content).hexdigest()
            suffix='.pdf' if r.content.startswith(b'%PDF') else '.jpg' if r.content.startswith(b'\xff\xd8') else '.html'
            target=ROOT/'data/raw'/f'{s["source_id"]}_{r.status_code}_{h[:12]}{suffix}'
            if not target.exists():target.write_bytes(r.content)
            row.update(http_status=r.status_code,status='downloaded_pending_content_review' if r.ok else 'http_failed',local_path=target.relative_to(ROOT).as_posix(),sha256=h,error='')
        except requests.RequestException as exc:row.update(status='network_failed',error=str(exc))
        exists=log.exists()
        with log.open('a',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader() if not exists else None;w.writerow(row)
        print(json.dumps(row,ensure_ascii=False))
