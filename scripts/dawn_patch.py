# 새벽말씀동행 유튜브 영상 링크를 index.html 의 <!--dawn:YYYYMMDD--> 칸에 붙인다.
import re, sys, html, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date
FEED = "https://www.youtube.com/feeds/videos.xml?channel_id=UCW4ozNTjPfSEiDTJYsiUPvQ"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
TITLE_RE = re.compile(r"^\[\s*수서동행교회\s*새벽말씀동행\s*#(\d+)\s*\]\s*(.+)$")
DAYS = "월화수목금토일"
page = sys.argv[1] if len(sys.argv) > 1 else "index.html"
xml_text = None
for _ in range(6):
    try:
        with urllib.request.urlopen(FEED, timeout=30) as r:
            xml_text = r.read().decode(); break
    except Exception as e:
        print("feed retry:", e); time.sleep(20)
if xml_text is None:
    print("FEED_FAIL"); sys.exit(0)
vids = {}
for e in ET.fromstring(xml_text).findall("a:entry", NS):
    title = e.find("a:title", NS).text.strip()
    if "#shorts" in title.lower():
        continue
    m = TITLE_RE.match(title)
    if not m:
        continue
    kst = datetime.fromisoformat(e.find("a:published", NS).text.replace("Z", "+00:00")) + timedelta(hours=9)
    no = int(m.group(1))
    if no not in vids or kst < vids[no]["kst"]:
        vids[no] = {"no": no, "title": m.group(2).strip(), "id": e.find("yt:videoId", NS).text, "kst": kst}
def links(key):
    s = date(int(key[:4]), int(key[4:6]), int(key[6:]))
    lo, hi = s + timedelta(days=1), s + timedelta(days=6)
    out = []
    for v in sorted(vids.values(), key=lambda v: v["no"]):
        d = v["kst"].date()
        if lo <= d <= hi:
            out.append(f'<a class="dl" href="https://www.youtube.com/watch?v={html.escape(v["id"])}" target="_blank" rel="noopener">'
                       f'<span class="dd">{DAYS[d.weekday()]} {d.month}.{d.day}</span><span class="dt">{html.escape(v["title"])}</span>'
                       f'<span class="dp" aria-hidden="true">▶</span></a>')
            print("VIDEO", v["no"], d.isoformat(), v["title"])
    return "".join(out)
t = open(page, encoding="utf-8").read()
def repl(m):
    l = links(m.group(1))
    return f"<!--dawn:{m.group(1)}-->{l}<!--/dawn-->" if l else m.group(0)
new = re.sub(r"<!--dawn:(\d{8})-->.*?<!--/dawn-->", repl, t, flags=re.S)
if new == t:
    print("NO_CHANGE")
else:
    open(page, "w", encoding="utf-8").write(new)
    print("UPDATED", len(re.findall(r'class="dl"', new)))
