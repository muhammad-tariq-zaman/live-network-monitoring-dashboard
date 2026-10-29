#!/usr/bin/env python3
"""Live probes for the network monitor dashboard. Stdlib + curl only.

Why curl, not raw sockets: this VM routes outbound traffic through an
egress proxy and blocks raw ICMP sockets (ping: Operation not
permitted). Direct Python sockets therefore hit the proxy in plain
text and fail TLS, while curl follows the proxy correctly. ICMP is
reported as unavailable, not as a failure — the photo's own probes
are ICMP + TCP 443 + TLS, and this script does TCP 443 + TLS + HTTPS
through the same path curl uses, which is the honest measurement
available here. On a normal office PC / VPS without this proxy,
ICMP can be added back with a ping probe.

Usage: python3 probe.py [--targets targets.json] [--out status.json]
"""
import argparse, json, socket, subprocess, time

DEFAULT_TARGETS = [
    {"id": "portfolio", "name": "Portfolio", "host": "muhammad-tariq-zaman.github.io",
     "url": "https://muhammad-tariq-zaman.github.io", "group": "Your sites"},
    {"id": "blog", "name": "AI Tools Blog", "host": "satisfactorynews.blogspot.com",
     "url": "https://satisfactorynews.blogspot.com", "group": "Your sites"},
    {"id": "store", "name": "Custom Designs Store", "host": "x06cvz-2u.myshopify.com",
     "url": "https://x06cvz-2u.myshopify.com", "group": "Your sites"},
    {"id": "errands1", "name": "WFS-1", "host": "errands1.dialerhosting.com",
     "url": "https://errands1.dialerhosting.com", "group": "Hakeem Walee — WFS nodes"},
    {"id": "errands2", "name": "WFS-2", "host": "errands2.dialerhosting.com",
     "url": "https://errands2.dialerhosting.com", "group": "Hakeem Walee — WFS nodes"},
    {"id": "errands4", "name": "WFS-4", "host": "errands4.dialerhosting.com",
     "url": "https://errands4.dialerhosting.com", "group": "Hakeem Walee — WFS nodes"},
    {"id": "errands6", "name": "WFS-6", "host": "errands6.dialerhosting.com",
     "url": "https://errands6.dialerhosting.com", "group": "Hakeem Walee — WFS nodes"},
    {"id": "errands10", "name": "WFS-10", "host": "errands10.dialerhosting.com",
     "url": "https://errands10.dialerhosting.com", "group": "Hakeem Walee — WFS nodes"},
    {"id": "errands11", "name": "WFS-11", "host": "errands11.dialerhosting.com",
     "url": "https://errands11.dialerhosting.com", "group": "Hakeem Walee — WFS nodes"},
    {"id": "google-dns", "name": "Google DNS", "host": "8.8.8.8",
     "url": "https://dns.google", "group": "Baselines"},
    {"id": "cloudflare-dns", "name": "Cloudflare DNS", "host": "1.1.1.1",
     "url": "https://one.one.one.one", "group": "Baselines"},
    {"id": "google", "name": "Google", "host": "www.google.com",
     "url": "https://www.google.com", "group": "Baselines"},
]

def probe(t, timeout=8):
    r = {"id": t["id"], "name": t["name"], "host": t["host"],
         "url": t["url"], "group": t["group"],
         "dns_ms": None, "tcp_ms": None, "tls_ms": None,
         "http_ms": None, "http_code": None, "error": None}
    t0 = time.time()
    try:
        socket.getaddrinfo(t["host"], 443)
        r["dns_ms"] = round((time.time() - t0) * 1000, 1)
    except Exception as e:
        r["error"] = f"DNS: {e}"; r["status"] = "DOWN"; r["alert"] = "SiteUnreachable"; return r
    cmd = ["curl", "-o", "/dev/null", "-s", "-w",
           "%{http_code} %{time_connect} %{time_appconnect} %{time_total} %{time_namelookup}",
           "--max-time", str(timeout), t["url"]]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5).stdout.strip().split()
        code, conn, tls, total, namelookup = out[0], float(out[1]), float(out[2]), float(out[3]), float(out[4])
        r["tcp_ms"] = round(conn * 1000, 1)
        r["tls_ms"] = round(tls * 1000, 1) if tls > 0 else None
        r["http_ms"] = round(total * 1000, 1)
        r["http_code"] = int(code) if code.isdigit() else None
    except Exception as e:
        r["error"] = f"curl: {e}"
    if r["http_code"] and 200 <= r["http_code"] < 400:
        r["status"] = "OK"; r["alert"] = None
    elif r["tcp_ms"] is not None and r["tcp_ms"] >= 0 and r["http_code"] in (None, 0):
        # TCP path answered but no HTTPS response — same as the photo's alert
        r["status"] = "CRITICAL"; r["alert"] = "HTTPSUnreachableWhileTCP"
        r["error"] = r["error"] or "HTTPS request failed (HTTP 000) while TCP path answered"
    else:
        r["status"] = "DOWN"; r["alert"] = "SiteUnreachable"
    return r

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--targets"); ap.add_argument("--out")
    a = ap.parse_args()
    targets = json.load(open(a.targets)) if a.targets else DEFAULT_TARGETS
    results = [probe(t) for t in targets]
    alerts = [{"target": r["name"], "alert": r["alert"], "detail": r["error"] or f"HTTP {r['http_code']}"}
              for r in results if r["alert"]]
    out = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime()),
           "vantage_point": "This monitor — TCP 443 + TLS + HTTPS probes via curl; ICMP unavailable here (raw sockets blocked), not counted as a failure",
           "icmp": "unavailable (raw sockets blocked on this host)",
           "targets": results, "alerts": alerts,
           "summary": {"total": len(results),
                       "ok": sum(1 for r in results if r["status"] == "OK"),
                       "critical": sum(1 for r in results if r["status"] == "CRITICAL"),
                       "down": sum(1 for r in results if r["status"] == "DOWN")}}
    if a.out:
        json.dump(out, open(a.out, "w"), indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
