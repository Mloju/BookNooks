"""Build a searchable HTML table from the latest collected books CSV."""

import csv
import html
import json
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_FILE = PROJECT_DIR / "books_table.html"


def main():
    csv_files = sorted(PROCESSED_DIR.glob("books_sample_*.csv"))
    if not csv_files:
        raise SystemExit(f"No collected books CSV found in {PROCESSED_DIR}")

    source = csv_files[-1]
    with source.open(encoding="utf-8-sig", newline="") as file:
        books = list(csv.DictReader(file))

    payload = json.dumps(books, ensure_ascii=False).replace("<", "\\u003c")
    source_name = html.escape(source.relative_to(PROJECT_DIR).as_posix())
    document = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Collected fantasy books | BookNooks</title>
<style>
:root{font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#202522;background:#f5f6f2}
body{margin:0;padding:36px clamp(16px,4vw,56px)}main{max-width:1500px;margin:auto}h1{font-size:clamp(26px,4vw,38px);margin:0 0 4px}.meta{color:#66716a;margin:0 0 22px}
.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:20px 0 12px}input{font:inherit;padding:10px 12px;border:1px solid #cbd2cc;border-radius:8px;min-width:min(360px,90vw);background:white}.count{color:#536057}
.table-wrap{overflow:auto;border:1px solid #dce1dc;border-radius:10px;background:white}table{border-collapse:collapse;width:100%;min-width:1000px}th,td{text-align:left;vertical-align:top;padding:12px 14px;border-bottom:1px solid #edf0ed}th{position:sticky;top:0;background:#eef2ee;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#4c5a50}tr:last-child td{border-bottom:0}td.title{font-weight:650;min-width:210px}td.author{min-width:160px}td.subjects{min-width:210px;color:#536057}td.description{min-width:300px;max-width:500px;color:#46524a}.desc{max-height:5.7em;overflow:hidden;white-space:pre-line}.desc.open{max-height:none}button{border:0;background:none;color:#315d45;font:inherit;text-decoration:underline;cursor:pointer;padding:4px 0}.id{font:12px ui-monospace,monospace;color:#637067;white-space:nowrap}a{color:#315d45}.empty{padding:32px;color:#66716a;text-align:center}
</style></head><body><main>
<h1>Collected fantasy books</h1>
<p class="meta">100 book records from the Open Library API · Data: SOURCE</p>
<div class="toolbar"><input id="search" type="search" placeholder="Search title, author, subject, description…" aria-label="Search books"><span class="count" id="count"></span></div>
<div class="table-wrap"><table><thead><tr><th>#</th><th>Title</th><th>Author</th><th>First published</th><th>Subjects / genres</th><th>Description</th><th>Work ID</th></tr></thead><tbody id="rows"></tbody></table><div id="empty" class="empty" hidden>No matching books.</div></div>
</main><script>
const books=DATA;
const rows=document.querySelector('#rows'),search=document.querySelector('#search'),count=document.querySelector('#count'),empty=document.querySelector('#empty');
function render(){const q=search.value.trim().toLowerCase();const found=books.map((b,i)=>({b,i})).filter(({b})=>Object.values(b).join(' ').toLowerCase().includes(q));count.textContent=`Showing ${found.length} of ${books.length} books`;empty.hidden=found.length>0;rows.innerHTML=found.map(({b,i})=>`<tr><td>${i+1}</td><td class="title">${esc(b.title)||'Untitled'}</td><td class="author">${esc(b.author)||'—'}</td><td>${esc(b.publication_year)||'—'}</td><td class="subjects">${esc(b.genres)||'—'}</td><td class="description"><div class="desc" id="d${i}">${esc(b.description)||'No description available.'}</div>${b.description?`<button type="button" onclick="document.querySelector('#d${i}').classList.toggle('open');this.textContent=this.textContent==='Read more'?'Show less':'Read more'">Read more</button>`:''}</td><td class="id"><a href="https://openlibrary.org${encodeURI(b.book_id)}" target="_blank" rel="noopener">${esc(b.book_id)}</a></td></tr>`).join('')}
function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
search.addEventListener('input',render);render();
</script></body></html>'''
    document = document.replace("100 book records", f"{len(books)} book records")
    document = document.replace("SOURCE", source_name).replace("DATA", payload)
    OUTPUT_FILE.write_text(document, encoding="utf-8")
    print(f"Created {OUTPUT_FILE} with {len(books)} records from {source.name}")

import pandas as pd

df = pd.read_csv("data/processed/books_sample_20261010_044503.csv")
print(df.head(50))