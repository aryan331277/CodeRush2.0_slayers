cat > /mnt/user-data/outputs/paper_graph.py << 'EOF'
import requests
import feedparser
import urllib.parse
import json
import sys
import os
import tempfile
import webbrowser

# ============================================
# SEARCH OPENALEX
# ============================================
def search_openalex(topic, limit=8):
    encoded_topic = urllib.parse.quote(topic)
    url = (
        f"https://api.openalex.org/works"
        f"?search={encoded_topic}"
        f"&per-page={limit}"
        f"&select=title,publication_year,doi,primary_location,concepts,abstract_inverted_index"
    )
    papers = []
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        for paper in data.get("results", []):
            concepts = [c["display_name"].lower() for c in paper.get("concepts", [])[:8]]
            inv = paper.get("abstract_inverted_index") or {}
            words = []
            for word, positions in inv.items():
                for pos in positions:
                    words.append((pos, word))
            abstract = " ".join(w for _, w in sorted(words))[:300]
            location = paper.get("primary_location") or {}
            doi = paper.get("doi")
            papers.append({
                "title":    paper.get("title", "Untitled"),
                "year":     paper.get("publication_year", "?"),
                "pdf":      location.get("pdf_url"),
                "doi":      doi,
                "url":      f"https://doi.org/{doi}" if doi else None,
                "source":   "OpenAlex",
                "concepts": concepts,
                "abstract": abstract,
                "authors":  ""
            })
    except Exception as e:
        print(f"  OpenAlex error: {e}")
    return papers

# ============================================
# SEARCH ARXIV
# ============================================
def search_arxiv(topic, limit=8):
    query = urllib.parse.quote(topic)
    url = (
        f"http://export.arxiv.org/api/query?"
        f"search_query=all:{query}&start=0&max_results={limit}"
    )
    papers = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            pdf     = entry.id.replace("/abs/", "/pdf/") + ".pdf"
            cats    = [tag.get("term", "").lower() for tag in entry.get("tags", [])]
            abstract= getattr(entry, "summary", "")[:300].replace("\n", " ")
            authors = ", ".join(a.get("name", "") for a in entry.get("authors", [])[:3])
            papers.append({
                "title":    entry.title.replace("\n", " ").strip(),
                "year":     entry.published[:4],
                "pdf":      pdf,
                "doi":      None,
                "url":      entry.id,
                "source":   "arXiv",
                "concepts": cats,
                "abstract": abstract,
                "authors":  authors
            })
    except Exception as e:
        print(f"  arXiv error: {e}")
    return papers

# ============================================
# DEDUPLICATE
# ============================================
def remove_duplicates(papers):
    seen, unique = set(), []
    for p in papers:
        key = p["title"].lower().strip().replace(" ", "")[:60]
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique

# ============================================
# HTML (self-contained graph)
# ============================================
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Paper Graph — {topic}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<style>
  * {{ box-sizing:border-box;margin:0;padding:0; }}
  body {{ font-family:system-ui,sans-serif;background:#0f1117;color:#e2e8f0;min-height:100vh; }}
  #app {{ display:flex;flex-direction:column;height:100vh; }}
  #header {{ padding:14px 20px;background:#1a1d27;border-bottom:1px solid #2d3148;display:flex;align-items:center;gap:12px;flex-wrap:wrap; }}
  #header h1 {{ font-size:15px;font-weight:600;color:#a78bfa;white-space:nowrap; }}
  #search-row {{ display:flex;gap:8px;flex:1;min-width:260px; }}
  #topic-input {{ flex:1;padding:8px 12px;border-radius:8px;border:1px solid #3d4268;background:#252840;color:#e2e8f0;font-size:14px;outline:none; }}
  #topic-input:focus {{ border-color:#7c3aed; }}
  #filter-btn {{ padding:8px 18px;border-radius:8px;background:#7c3aed;color:#fff;border:none;font-size:14px;font-weight:500;cursor:pointer; }}
  #filter-btn:hover {{ background:#6d28d9; }}
  #status {{ padding:6px 20px;font-size:12px;color:#94a3b8;background:#13151f;border-bottom:1px solid #1e2030;min-height:28px;display:flex;align-items:center; }}
  #main {{ display:flex;flex:1;overflow:hidden; }}
  #graph-wrap {{ flex:1;position:relative;overflow:hidden; }}
  #graph-svg {{ width:100%;height:100%; }}
  #legend {{ position:absolute;bottom:16px;left:16px;background:rgba(26,29,39,.92);border:1px solid #2d3148;border-radius:10px;padding:10px 14px;font-size:12px;color:#94a3b8; }}
  .leg-item {{ display:flex;align-items:center;gap:7px;margin-bottom:5px; }}
  .leg-dot {{ width:11px;height:11px;border-radius:50%;flex-shrink:0; }}
  #hint {{ position:absolute;top:12px;left:12px;background:rgba(26,29,39,.85);border:1px solid #2d3148;border-radius:8px;padding:7px 11px;font-size:11px;color:#64748b;line-height:1.6; }}
  #side {{ width:300px;background:#1a1d27;border-left:1px solid #2d3148;overflow-y:auto;flex-shrink:0; }}
  #side-hdr {{ padding:14px 16px;font-size:13px;font-weight:600;color:#a78bfa;border-bottom:1px solid #2d3148; }}
  .pc {{ padding:12px 16px;border-bottom:1px solid #1e2030;cursor:pointer;transition:background .12s; }}
  .pc:hover {{ background:#252840; }}
  .pc.active {{ background:#2a1f4a;border-left:3px solid #7c3aed; }}
  .pc-title {{ font-size:12px;font-weight:500;color:#cbd5e1;line-height:1.4;margin-bottom:5px; }}
  .pc-meta {{ font-size:11px;color:#64748b;display:flex;gap:8px;flex-wrap:wrap;margin-bottom:4px; }}
  .badge {{ padding:2px 6px;border-radius:4px;font-size:10px;font-weight:600; }}
  .b-arxiv {{ background:#1e3a5f;color:#60a5fa; }}
  .b-oa    {{ background:#1e3d2f;color:#4ade80; }}
  .pc-links {{ display:flex;gap:8px; }}
  .pc-link {{ font-size:10px;color:#7c3aed;text-decoration:none; }}
  .pc-link:hover {{ text-decoration:underline; }}
  #tip {{ position:absolute;pointer-events:none;background:#1e2035;border:1px solid #3d4268;border-radius:8px;padding:10px 13px;max-width:270px;font-size:12px;color:#cbd5e1;display:none;z-index:100;line-height:1.6;box-shadow:0 4px 20px rgba(0,0,0,.5); }}
  #tip strong {{ color:#a78bfa;display:block;margin-bottom:4px; }}
</style>
</head>
<body>
<div id="app">
  <div id="header">
    <h1>📄 {topic}</h1>
    <div id="search-row">
      <input id="topic-input" type="text" placeholder="Filter by keyword, year, source…"/>
      <button id="filter-btn" onclick="doFilter()">Filter</button>
    </div>
  </div>
  <div id="status">Loaded {count} papers — drag nodes · scroll to zoom · click to explore connections</div>
  <div id="main">
    <div id="graph-wrap">
      <svg id="graph-svg"></svg>
      <div id="hint">🖱 Drag · Scroll zoom · Click node</div>
      <div id="legend">
        <div class="leg-item"><div class="leg-dot" style="background:#60a5fa"></div>arXiv</div>
        <div class="leg-item"><div class="leg-dot" style="background:#4ade80"></div>OpenAlex</div>
        <div class="leg-item"><div style="width:28px;height:2px;background:#7c3aed;opacity:.9"></div>Strong link</div>
        <div class="leg-item"><div style="width:28px;height:1px;background:#334155"></div>Weak link</div>
      </div>
      <div id="tip"></div>
    </div>
    <div id="side">
      <div id="side-hdr">Papers ({count})</div>
      <div id="paper-list"></div>
    </div>
  </div>
</div>
<script>
const PAPERS = {papers_json};

function buildEdges(papers) {{
  const edges = [];
  function tok(p) {{
    return new Set([p.title, ...(p.concepts||[]), p.abstract||''].join(' ').toLowerCase().match(/\b[a-z]{{4,}}\b/g)||[]);
  }}
  const tc = papers.map(tok);
  for (let i=0;i<papers.length;i++) {{
    for (let j=i+1;j<papers.length;j++) {{
      const inter=[...tc[i]].filter(t=>tc[j].has(t)).length;
      const union=new Set([...tc[i],...tc[j]]).size;
      const score=union?inter/union:0;
      const yb=Math.abs((+papers[i].year||2000)-(+papers[j].year||2000))<=2?0.04:0;
      const tot=score+yb;
      if(tot>0.08) edges.push({{source:i,target:j,weight:tot}});
    }}
  }}
  edges.sort((a,b)=>b.weight-a.weight);
  return edges.slice(0,papers.length*5);
}}

const COL={{arXiv:{{f:'#1e3a5f',s:'#60a5fa'}},OpenAlex:{{f:'#1a3326',s:'#4ade80'}}}};
const DEF={{f:'#2d2010',s:'#fb923c'}};
let sim;

function renderSide(papers) {{
  document.getElementById('side-hdr').textContent=`Papers (${{papers.length}})`;
  document.getElementById('paper-list').innerHTML=papers.map(p=>`
    <div class="pc" id="card-${{p.id}}" onclick="hl(${{p.id}})">
      <div class="pc-title">${{p.title}}</div>
      <div class="pc-meta">
        <span class="badge ${{p.source==='arXiv'?'b-arxiv':'b-oa'}}">${{p.source}}</span>
        <span>${{p.year}}</span>
        ${{p.authors?`<span style="color:#475569">${{p.authors}}</span>`:''}}
      </div>
      <div class="pc-links">
        ${{p.pdf?`<a class="pc-link" href="${{p.pdf}}" target="_blank">PDF ↗</a>`:''}}
        ${{p.url&&!p.pdf?`<a class="pc-link" href="${{p.url}}" target="_blank">Link ↗</a>`:''}}
        ${{p.doi?`<a class="pc-link" href="https://doi.org/${{p.doi}}" target="_blank">DOI ↗</a>`:''}}
      </div>
    </div>`).join('');
}}

function doFilter() {{
  const q=document.getElementById('topic-input').value.trim().toLowerCase();
  const matched=q?PAPERS.filter(p=>
    p.title.toLowerCase().includes(q)||
    (p.concepts||[]).some(c=>c.includes(q))||
    String(p.year).includes(q)||
    (p.authors||'').toLowerCase().includes(q)||
    (p.source||'').toLowerCase().includes(q)
  ):PAPERS;
  const vis=new Set(matched.map(p=>p.id));
  d3.select('#graph-svg').selectAll('.ng').style('opacity',d=>vis.has(d.id)?1:0.07);
  d3.select('#graph-svg').selectAll('line').style('opacity',d=>vis.has(d.source.id)&&vis.has(d.target.id)?null:0.03);
  renderSide(matched);
  document.getElementById('status').textContent=q?`${{matched.length}} papers matching "${{q}}"`:`Showing all ${{PAPERS.length}} papers`;
}}

function renderGraph() {{
  const wrap=document.getElementById('graph-wrap');
  const W=wrap.clientWidth,H=wrap.clientHeight;
  const svg=d3.select('#graph-svg').attr('viewBox',`0 0 ${{W}} ${{H}}`);

  const defs=svg.append('defs');
  const fl=defs.append('filter').attr('id','glow').attr('x','-50%').attr('y','-50%').attr('width','200%').attr('height','200%');
  fl.append('feGaussianBlur').attr('stdDeviation','5').attr('result','b');
  const fm=fl.append('feMerge');
  fm.append('feMergeNode').attr('in','b');
  fm.append('feMergeNode').attr('in','SourceGraphic');

  const g=svg.append('g');
  svg.call(d3.zoom().scaleExtent([0.1,6]).on('zoom',e=>g.attr('transform',e.transform)));

  const edges=buildEdges(PAPERS);
  const wExt=d3.extent(edges,e=>e.weight);
  const sW=d3.scaleLinear().domain(wExt).range([0.6,3.5]);
  const sO=d3.scaleLinear().domain(wExt).range([0.12,0.85]);

  const link=g.append('g').selectAll('line').data(edges).join('line')
    .attr('stroke',d=>d.weight>(wExt[0]+wExt[1])/2?'#7c3aed':'#334155')
    .attr('stroke-width',d=>sW(d.weight))
    .attr('stroke-opacity',d=>sO(d.weight));

  const deg=new Array(PAPERS.length).fill(0);
  edges.forEach(e=>{{deg[e.source]++;deg[e.target]++;}});
  const rS=d3.scaleLinear().domain(d3.extent(deg)).range([10,26]);

  const node=g.append('g').selectAll('g').data(PAPERS).join('g')
    .attr('class','ng').style('cursor','pointer')
    .call(d3.drag()
      .on('start',(e,d)=>{{if(!e.active)sim.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;}})
      .on('drag', (e,d)=>{{d.fx=e.x;d.fy=e.y;}})
      .on('end',  (e,d)=>{{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null;}}))
    .on('click',      (e,d)=>{{e.stopPropagation();hl(d.id);}})
    .on('mouseenter', (e,d)=>showTip(e,d,deg))
    .on('mousemove',   e   =>moveTip(e))
    .on('mouseleave', ()  =>hideTip());

  node.append('circle')
    .attr('r',d=>rS(deg[d.id]))
    .attr('fill',  d=>(COL[d.source]||DEF).f)
    .attr('stroke',d=>(COL[d.source]||DEF).s)
    .attr('stroke-width',1.5);

  node.append('text')
    .text(d=>d.title.split(' ').slice(0,2).join(' '))
    .attr('text-anchor','middle').attr('dy','0.35em')
    .attr('font-size',d=>Math.max(7,rS(deg[d.id])*0.48)+'px')
    .attr('fill','#94a3b8').attr('pointer-events','none')
    .style('user-select','none');

  sim=d3.forceSimulation(PAPERS)
    .force('link',   d3.forceLink(edges).id(d=>d.id).distance(d=>90+(1-d.weight)*80).strength(0.5))
    .force('charge', d3.forceManyBody().strength(-260))
    .force('center', d3.forceCenter(W/2,H/2))
    .force('collide',d3.forceCollide(d=>rS(deg[d.id])+6))
    .on('tick',()=>{{
      link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
          .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
      node.attr('transform',d=>`translate(${{d.x}},${{d.y}})`);
    }});

  svg.on('click',clearHl);
}}

function hl(id) {{
  document.querySelectorAll('.pc').forEach(c=>c.classList.remove('active'));
  const card=document.getElementById(`card-${{id}}`);
  if(card){{card.classList.add('active');card.scrollIntoView({{behavior:'smooth',block:'nearest'}});}}
  const conn=new Set([id]);
  d3.select('#graph-svg').selectAll('line').each(d=>{{
    if(d.source.id===id) conn.add(d.target.id);
    if(d.target.id===id) conn.add(d.source.id);
  }});
  d3.select('#graph-svg').selectAll('.ng').style('opacity',d=>conn.has(d.id)?1:0.07);
  d3.select('#graph-svg').selectAll('.ng circle').attr('filter',d=>d.id===id?'url(#glow)':null);
  d3.select('#graph-svg').selectAll('line').style('opacity',d=>(d.source.id===id||d.target.id===id)?1:0.03);
  document.getElementById('status').textContent=`"${{PAPERS[id].title}}" · ${{conn.size-1}} related papers`;
}}

function clearHl() {{
  document.querySelectorAll('.pc').forEach(c=>c.classList.remove('active'));
  d3.select('#graph-svg').selectAll('.ng').style('opacity',1);
  d3.select('#graph-svg').selectAll('.ng circle').attr('filter',null);
  d3.select('#graph-svg').selectAll('line').style('opacity',null);
  document.getElementById('status').textContent=`Loaded ${{PAPERS.length}} papers — drag nodes · scroll to zoom · click to explore connections`;
}}

function showTip(e,d,deg) {{
  const t=document.getElementById('tip');
  t.style.display='block';
  t.innerHTML=`<strong>${{d.title}}</strong>${{d.source}} · ${{d.year}}${{d.authors?' · '+d.authors:''}}<br>
    <span style="color:#475569">${{deg[d.id]}} connections</span>
    ${{d.abstract?`<br><span style="color:#64748b;font-size:11px">${{d.abstract.slice(0,130)}}…</span>`:''}}`; 
  moveTip(e);
}}
function moveTip(e) {{
  const t=document.getElementById('tip');
  const r=document.getElementById('graph-wrap').getBoundingClientRect();
  let x=e.clientX-r.left+14,y=e.clientY-r.top+14;
  if(x+280>r.width)x-=290;if(y+170>r.height)y-=160;
  t.style.left=x+'px';t.style.top=y+'px';
}}
function hideTip(){{document.getElementById('tip').style.display='none';}}

renderSide(PAPERS);
renderGraph();
document.getElementById('topic-input').addEventListener('keydown',e=>{{if(e.key==='Enter')doFilter();}});
</script>
</body>
</html>"""

# ============================================
# MAIN
# ============================================
def main():
    topic = input("Enter Research Topic: ").strip()
    if not topic:
        print("No topic entered.")
        return

    print(f"\nSearching OpenAlex...")
    oa = search_openalex(topic)
    print(f"  Found {len(oa)} papers")

    print(f"Searching arXiv...")
    ax = search_arxiv(topic)
    print(f"  Found {len(ax)} papers")

    papers = remove_duplicates(oa + ax)
    print(f"Total after dedup: {len(papers)} papers")

    if not papers:
        print("No papers found. Try a different topic.")
        return

    # Assign ids
    for i, p in enumerate(papers):
        p["id"] = i

    # Build HTML
    papers_json = json.dumps(papers, ensure_ascii=False)
    html = HTML_TEMPLATE.format(
        topic=topic,
        count=len(papers),
        papers_json=papers_json
    )

    # Write to temp file and open in browser
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False,
        encoding="utf-8", prefix="paper_graph_"
    )
    tmp.write(html)
    tmp.close()

    print(f"\nOpening graph in browser: {tmp.name}")
    webbrowser.open(f"file://{tmp.name}")

if __name__ == "__main__":
    main()
EOF
echo "done"
Output

done
Done
