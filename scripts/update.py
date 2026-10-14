#!/usr/bin/env python3
"""Refresh the DRAWS table inside index.html from public Mark Six result pages."""
import re, urllib.request, pathlib, sys

UA = "Mozilla/5.0 (compatible; mark-six-estimator/1.0)"
JINA = "https://r.jina.ai/"
SRC = ["https://lottery.hk/en/mark-six/results/",
       "https://www.magayo.com/lotto/hong-kong/mark-six-results/"]
MONTHS = {m: i + 1 for i, m in enumerate(
    "January February March April May June July August September October November December".split())}
KEEP = 120


def fetch(url):
    req = urllib.request.Request(JINA + url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", "replace")


def parse_lotteryhk(t):
    t = re.sub(r"<[^>]+>", " ", t).replace("*", " ").replace("|", " ")
    t = re.sub(r"\s+", " ", t)
    out = {}
    for m in re.finditer(r"(\d{2}/\d{3})\s+(\d{2}/\d{2}/\d{4})\s+((?:\d{1,2}\s+){6}\d{1,2})", t):
        ns = [int(v) for v in m.group(3).split()]
        if len(ns) != 7 or len(set(ns)) != 7 or any(v < 1 or v > 49 for v in ns):
            continue
        d = "-".join(reversed(m.group(2).split("/")))
        out[d] = {"no": m.group(1), "n": sorted(ns[:6]), "x": ns[6]}
    return out


def parse_magayo(t):
    out = {}
    pat = r"(\d{1,2}) (" + "|".join(MONTHS) + r") (\d{4})\s+\w+day\s+((?:\d{2}\s+){6})\s*Extra\s+(\d{2})"
    for m in re.finditer(pat, t):
        d = "%s-%02d-%02d" % (m.group(3), MONTHS[m.group(2)], int(m.group(1)))
        out[d] = {"n": sorted(int(v) for v in m.group(4).split()), "x": int(m.group(5))}
    return out


def main():
    root = pathlib.Path(__file__).resolve().parents[1]
    page = root / "index.html"
    h = page.read_text(encoding="utf-8")
    cur = {}
    for no, d, n, x in re.findall(
            r'\["(\d{2}/\d{3})","(\d{4}-\d{2}-\d{2})",\[([\d,]+)\],(\d+)\]', h):
        cur[d] = {"no": no, "n": [int(v) for v in n.split(",")], "x": int(x)}

    merged = dict(cur)
    for url in SRC:
        try:
            t = fetch(url)
        except Exception as e:
            print("fetch failed", url, e)
            continue
        got = parse_lotteryhk(t) if "lottery.hk" in url else parse_magayo(t)
        new = [d for d in got if d not in merged]
        for d, v in got.items():
            merged.setdefault(d, v)
        print("%s -> %d rows (%d new: %s)" % (url.split("/")[2], len(got), len(new), sorted(new)[-3:]))

    dates = sorted(merged)
    anchor = next((d for d in dates if "no" in merged[d]), None)
    if anchor is None:
        sys.exit("no anchored draw number in current data")
    start = dates.index(anchor)
    counter = int(merged[anchor]["no"].split("/")[1])
    prefix = merged[anchor]["no"].split("/")[0]
    for d in dates[start + 1:]:
        counter += 1
        merged[d]["no"] = "%s/%03d" % (prefix, counter)
    down = int(merged[anchor]["no"].split("/")[1])
    for d in reversed(dates[:start]):
        down -= 1
        merged[d]["no"] = "%s/%03d" % (prefix, down)

    rows = [(merged[d]["no"], d, merged[d]["n"], merged[d]["x"]) for d in sorted(merged, reverse=True)][:KEEP]
    rows.sort(key=lambda r: r[1], reverse=True)
    literal = "const DRAWS = [\n" + "".join(
        '["%s","%s",[%s],%d],\n' % (no, d, ",".join(str(v) for v in n), x) for no, d, n, x in rows
    ) + "].map(([no,date,n,x])=>({no,date,n,x}));"
    h2 = re.sub(r"const DRAWS = \[.*?\]\.map\(\(\[no,date,n,x\]\)=>\(\{no,date,n,x\}\)\);", literal, h, flags=re.S)
    latest = rows[0]
    h2 = re.sub(r'(<div class="next">).*?(</div>)',
                r'\1下期攪珠<b>數據更新至 %s · %s</b>\2' % (latest[0], "-".join(reversed(latest[1].split("-")))),
                h2, count=1, flags=re.S)
    if h2 == h:
        print("no change")
        return
    page.write_text(h2, encoding="utf-8")
    print("updated: %d draws stored, newest %s %s" % (len(rows), latest[0], latest[1]))


if __name__ == "__main__":
    main()
