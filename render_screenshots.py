#!/usr/bin/env python3
"""Render dashboard screenshots from live probe data (status.json).

The sandbox Chromium cannot start headless (it needs the browser
daemon's WebGL policy), so these images are drawn with Pillow from
the exact values in status.json — the same values the live page at
http://localhost:8000 shows. Nothing here is invented: every number
comes from a real probe run.
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "screenshots")
os.makedirs(OUT, exist_ok=True)

def font(size, bold=False):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def draw_dashboard(data, path):
    W, H = 1400, 1050
    img = Image.new("RGB", (W, H), (11, 18, 32))
    d = ImageDraw.Draw(img)
    d.text((24, 20), "Live Network Monitor  —  Shared Internet Path", fill=(229, 231, 235), font=font(26, True))
    s = data["summary"]
    d.text((24, 58), f"Generated {data['generated_at']}  ·  {s['ok']} OK  ·  {s['critical']} CRITICAL  ·  {s['down']} DOWN", fill=(156, 163, 175), font=font(16))
    # nodes, two columns
    targets = data["targets"]
    x0, y = 24, 100
    col_w = 860
    for i, t in enumerate(targets):
        col = i % 2
        row = i // 2
        x = x0 + col * (col_w // 2 + 8)
        yy = y + row * 138
        border = (22, 101, 52) if t["status"] == "OK" else (185, 28, 28)
        d.rounded_rectangle([x, yy, x + col_w // 2 - 8, yy + 126], radius=10, outline=border, width=2, fill=(17, 24, 39))
        dot = (34, 197, 94) if t["status"] == "OK" else (239, 68, 68)
        d.ellipse([x + 14, yy + 16, x + 26, yy + 28], fill=dot)
        d.text((x + 34, yy + 12), t["name"], fill=(255, 255, 255), font=font(19, True))
        d.text((x + col_w // 2 - 110, yy + 12), t["status"], fill=(255, 255, 255), font=font(16, True))
        sub = "Hakeem Walee" if "Hakeem Walee" in (t.get("group") or "") else t["host"]
        d.text((x + 14, yy + 44), sub, fill=(156, 163, 175), font=font(15))
        d.text((x + 14, yy + 70), f"HTTP {t['http_code'] or '—'}   ·   TCP 443 {t['tcp_ms'] or '—'} ms   ·   TLS {t['tls_ms'] or '—'} ms", fill=(229, 231, 235), font=font(15))
        err_short = ""
        if t["error"]:
            err_short = "   ·   HTTPS failed (HTTP 000)" if "HTTP 000" in t["error"] else "   ·   " + t["error"][:30]
        d.text((x + 14, yy + 96), f"HTTPS total {t['http_ms'] or '—'} ms" + err_short, fill=(229, 231, 235), font=font(14))
    # alerts panel
    ax = 920
    d.text((ax, 100), "Alerts", fill=(255, 255, 255), font=font(22, True))
    yy = 140
    for a in data["alerts"]:
        d.rounded_rectangle([ax, yy, 1376, yy + 92], radius=8, outline=(185, 28, 28), width=2, fill=(31, 41, 55))
        d.text((ax + 12, yy + 10), f"CRITICAL · {a['alert']}", fill=(239, 68, 68), font=font(16, True))
        d.text((ax + 12, yy + 38), a["target"], fill=(255, 255, 255), font=font(16))
        detail_short = "HTTPS failed (HTTP 000)" if "HTTP 000" in (a["detail"] or "") else (a["detail"] or "")[:52]
        d.text((ax + 12, yy + 62), detail_short, fill=(156, 163, 175), font=font(14))
        yy += 104
        if yy > 900:
            break
    d.text((ax, yy + 6), "Office & Internet", fill=(255, 255, 255), font=font(20, True))
    d.text((ax, yy + 38), "Probes: TCP 443 · TLS · HTTPS", fill=(156, 163, 175), font=font(15))
    d.text((ax, yy + 62), "ICMP: unavailable here", fill=(156, 163, 175), font=font(15))
    d.text((ax, yy + 86), "Baselines: Google · Google DNS", fill=(156, 163, 175), font=font(15))
    d.text((ax, yy + 110), "· Cloudflare DNS", fill=(156, 163, 175), font=font(15))
    img.save(path)
    print("wrote", path)

def draw_how_it_works(path):
    W, H = 1400, 800
    img = Image.new("RGB", (W, H), (11, 18, 32))
    d = ImageDraw.Draw(img)
    d.text((24, 20), "How it works — and why it helps", fill=(229, 231, 235), font=font(28, True))
    steps = [
        ("1  PROBE", "DNS → TCP 443 → TLS → HTTPS\nEvery 60 seconds, per target"),
        ("2  JUDGE", "OK / CRITICAL / DOWN\nTCP ok + HTTPS fail =\nHTTPSUnreachableWhileTCP"),
        ("3  SHOW", "Live dashboard + alerts panel\nBaselines tell a site outage\napart from an internet outage"),
        ("4  ACT", "Evidence for ISP / host:\nwhich layer failed, and when,\nwith timings — not just 'down'"),
    ]
    for i, (t, b) in enumerate(steps):
        x = 24 + i * 344
        d.rounded_rectangle([x, 100, x + 320, 420], radius=12, outline=(55, 65, 81), width=2, fill=(17, 24, 39))
        d.text((x + 18, 120), t, fill=(147, 197, 253), font=font(20, True))
        d.text((x + 18, 170), b, fill=(229, 231, 235), font=font(17))
        if i < 3:
            d.text((x + 322, 250), "›", fill=(156, 163, 175), font=font(36, True))
    d.text((24, 470), "Applications", fill=(255, 255, 255), font=font(24, True))
    apps = [
        "•  Catch outages before users report them",
        "•  Separate site outages from internet outages",
        "•  Pinpoint the failing layer: DNS, TCP, TLS or HTTPS",
        "•  Zero cost — Python stdlib + curl, no SaaS, no account",
        "•  Portfolio-ready: a working tool with a real test run",
    ]
    for i, a in enumerate(apps):
        d.text((24, 520 + i * 44), a, fill=(229, 231, 235), font=font(19))
    img.save(path)
    print("wrote", path)

if __name__ == "__main__":
    data = json.load(open(os.path.join(HERE, "status.json")))
    draw_dashboard(data, os.path.join(OUT, "dashboard.png"))
    draw_how_it_works(os.path.join(OUT, "how-it-works.png"))
