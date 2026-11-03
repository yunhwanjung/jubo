# 새벽말씀동행 유튜브 영상 링크를 index.html 의 <!--dawn:YYYYMMDD--> 칸에 붙인다.
# 1순위: 유튜브 RSS 피드. 피드가 안 되면(가끔 404) 채널 '동영상' 페이지를 읽는다.
import re, sys, html, json, time, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date, timezone
CH = "UCW4ozNTjPfSEiDTJYsiUPvQ"
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CH}"
PAGE_URL = f"https://www.youtube.com/channel/{CH}/videos"
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
TITLE_RE = re.compile(r"^\[\s*수서동행교회\s*새벽말씀동행\s*#(\d+)\s*\]\s*(.+)$")
DAYS = "월화수목금토일"
KST = timezone(timedelta(hours=9))
page = sys.argv[1] if len(sys.argv) > 1 else "index.html"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")

vids = {}
def add(no, title, vid, kst):
    if no not in vids or kst < vids[no]["kst"]:
        vids[no] = {"no": no, "title": title, "id": vid, "kst": kst}

def from_feed():
    for _ in range(3):
        try:
            xml_text = get(FEED); break
        except Exception as e:
            print("feed retry:", e); time.sleep(10)
    else:
        return False
    for e in ET.fromstring(xml_text).findall("a:entry", NS):
        title = e.find("a:title", NS).text.strip()
        if "#shorts" in title.lower():
            continue
        m = TITLE_RE.match(title)
        if m:
            kst = datetime.fromisoformat(e.find("a:published", NS).text.replace("Z", "+00:00")).astimezone(KST)
            add(int(m.group(1)), m.group(2).strip(), e.find("yt:videoId", NS).text, kst)
    return True

AGO = [(r"(\d+)\s*(초|second)", 1), (r"(\d+)\s*(분|minute)", 60), (r"(\d+)\s*(시간|hour)", 3600),
       (r"(\d+)\s*(일|day)", 86400), (r"(\d+)\s*(주|week)", 604800)]
def ago_to_kst(s):
    for pat, sec in AGO:
        m = re.search(pat, s)
        if m:
            return datetime.now(KST) - timedelta(seconds=int(m.group(1)) * sec)
    return None

def from_channel_page(known):
    try:
        t = get(PAGE_URL)
    except Exception as e:
        print("channel page fail:", e); return False
    found = False
    for b in t.split('"lockupViewModel":{')[1:]:
        c = re.search(r'"contentId":"([\w-]{11})"', b)
        ti = re.search(r'"lockupMetadataViewModel":\{"title":\{"content":"((?:[^"\\]|\\.)*)"', b)
        if not (c and ti):
            continue
        title = json.loads('"' + ti.group(1) + '"').strip()
        m = TITLE_RE.match(title)
        if not m or "#shorts" in title.lower():
            continue
        vid = c.group(1)
        if vid in known:                      # 이미 주보에 붙은 영상은 그 날짜를 그대로 쓴다
            kst = known[vid]
        else:
            ago = re.findall(r'"content":"([^"]*(?:전|ago))"', b)
            kst = ago_to_kst(ago[0]) if ago else None
            if kst is None:
                continue
        add(int(m.group(1)), m.group(2).strip(), vid, kst)
        found = True
    return found

t = open(page, encoding="utf-8").read()

# 주보에 이미 붙어 있는 링크의 날짜 (videoId -> 날짜)
known = {}
for block in re.finditer(r"<!--dawn:(\d{8})-->(.*?)<!--/dawn-->", t, flags=re.S):
    yr = int(block.group(1)[:4])
    for a in re.finditer(r'watch\?v=([\w-]{11}).*?<span class="dd">\S+ (\d+)\.(\d+)</span>', block.group(2)):
        known[a.group(1)] = datetime(yr, int(a.group(2)), int(a.group(3)), 6, 0, tzinfo=KST)

src = "feed" if from_feed() else ("channel" if from_channel_page(known) else None)
if src is None:
    print("FEED_FAIL"); sys.exit(0)
print("SOURCE", src, "videos:", len(vids))

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

def repl(m):
    l = links(m.group(1))
    return f"<!--dawn:{m.group(1)}-->{l}<!--/dawn-->" if l else m.group(0)
new = re.sub(r"<!--dawn:(\d{8})-->.*?<!--/dawn-->", repl, t, flags=re.S)
if new == t:
    print("NO_CHANGE")
else:
    open(page, "w", encoding="utf-8").write(new)
    print("UPDATED", len(re.findall(r'class="dl"', new)))
