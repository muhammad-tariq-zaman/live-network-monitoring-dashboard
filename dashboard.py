#!/usr/bin/env python3
"""Live Network Monitoring Dashboard — stdlib only.

Run:  python3 dashboard.py [--port 8000] [--interval 60]
Open: http://localhost:8000

A background thread re-probes all targets every --interval seconds
(see probe.py) and the page refreshes its data from /api/status
every 30 seconds, so the dashboard is live, not a screenshot.
No database, no dependencies: latest results live in memory and are
also written to status.json on every probe run.
"""
import argparse, json, os, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import probe

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = {"data": None, "lock": threading.Lock()}

def run_probe():
    data = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S %Z", time.localtime()),
            "vantage_point": "This monitor — TCP 443 + TLS + HTTPS probes via curl; ICMP unavailable here (raw sockets blocked), not counted as a failure",
            "icmp": "unavailable (raw sockets blocked on this host)",
            "targets": [], "alerts": [], "summary": {}}
    results = [probe.probe(t) for t in probe.DEFAULT_TARGETS]
    data["targets"] = results
    data["alerts"] = [{"target": r["name"], "alert": r["alert"], "detail": r["error"] or f"HTTP {r['http_code']}"}
                      for r in results if r["alert"]]
    data["summary"] = {"total": len(results),
                       "ok": sum(1 for r in results if r["status"] == "OK"),
                       "critical": sum(1 for r in results if r["status"] == "CRITICAL"),
                       "down": sum(1 for r in results if r["status"] == "DOWN")}
    with STATE["lock"]:
        STATE["data"] = data
    with open(os.path.join(HERE, "status.json"), "w") as f:
        json.dump(data, f, indent=2)
    return data

def loop(interval):
    while True:
        try:
            run_probe()
        except Exception as e:
            print("probe error:", e)
        time.sleep(interval)

PAGE = """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Live Network Monitor</title><style>
body{background:#0b1220;color:#e5e7eb;font-family:system-ui,Arial,sans-serif;margin:0;padding:20px}
h1{font-size:22px;margin:0 0 4px}.sub{color:#9ca3af;font-size:13px;margin-bottom:16px}
.grid{display:grid;grid-template-columns:2fr 1fr;gap:16px}
.card{border:1px solid #374151;border-radius:10px;padding:12px;margin-bottom:12px;background:#111827}
.card.ok{border-color:#166534}.card.CRITICAL,.card.DOWN{border-color:#b91c1c}
h2{font-size:16px;margin:0 0 8px}h3{font-size:14px;margin:14px 0 6px;color:#93c5fd}
.row{display:flex;justify-content:space-between;font-size:13px;padding:3px 0}
.okdot{color:#22c55e}.critdot{color:#ef4444}.mono{font-variant-numeric:tabular-nums}
.alert{background:#1f2937;border-left:4px solid #ef4444;padding:8px;margin-bottom:8px;border-radius:4px;font-size:13px}
.badge{display:inline-block;padding:2px 8px;border-radius:12px;font-size:12px}
.badge.ok{background:#166534}.badge.CRITICAL,.badge.DOWN{background:#b91c1c}
@media(max-width:800px){.grid{grid-template-columns:1fr}}
</style></head><body>
<h1>🌐 Live Network Monitor — Shared Internet Path</h1>
<div class="sub" id="meta">Loading…</div>
<div class="grid"><div id="nodes"></div><div>
<h2>🚨 Alerts</h2><div id="alerts"></div>
<h2>Office &amp; Internet</h2><div class="card"><div class="row"><span>Vantage point</span><span>This monitor</span></div>
<div class="row"><span>Probes</span><span>TCP 443 · TLS · HTTPS</span></div>
<div class="row"><span>ICMP</span><span>Unavailable here (raw sockets blocked)</span></div>
<div class="row"><span>Refresh</span><span>Probe every <span id="interval">60</span>s · page every 30s</span></div></div>
<h2>Why this helps</h2><div class="card" style="font-size:13px;line-height:1.5">
See an outage before users report it · tell a site outage apart from an
internet outage (baselines) · prove with numbers whether it is TCP, TLS
or HTTPS that failed · keep a record for the ISP or hosting provider.
</div></div></div>
<script>
async function load(){const r=await fetch('/api/status');const d=await r.json();
document.getElementById('meta').textContent='Generated '+d.generated_at+' · '+d.summary.ok+' OK · '+d.summary.critical+' CRITICAL · '+d.summary.down+' DOWN · '+d.vantage_point;
const groups={};d.targets.forEach(t=>{(groups[t.group]=groups[t.group]||[]).push(t)});
let html='';for(const g of Object.keys(groups)){html+='<h3>'+g+'</h3>';groups[g].forEach(t=>{
const dot=t.status==='OK'?'okdot':'critdot';
html+='<div class="card '+t.status+'"><div class="row"><strong>● <span class="'+dot+'">'+t.name+'</span></strong><span class="badge '+t.status+'">'+t.status+'</span></div>'
+'<div class="row mono"><span>'+t.host+'</span><span>HTTP '+ (t.http_code||'—') +'</span></div>'
+'<div class="row mono"><span>TCP 443</span><span>'+(t.tcp_ms??'—')+' ms</span></div>'
+'<div class="row mono"><span>TLS</span><span>'+(t.tls_ms??'—')+' ms</span></div>'
+'<div class="row mono"><span>HTTPS total</span><span>'+(t.http_ms??'—')+' ms</span></div>'
+(t.error?'<div class="row"><span>'+t.error+'</span></div>':'')+'</div>';});}
document.getElementById('nodes').innerHTML=html;
document.getElementById('alerts').innerHTML=d.alerts.length?d.alerts.map(a=>'<div class="alert"><strong>CRITICAL · '+a.alert+'</strong><br>'+a.target+' — '+a.detail+'</div>').join(''):'<div class="card">No active alerts. All probed targets are responding.</div>';}
load();setInterval(load,30000);
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def _send(self, body, ctype):
        b = body.encode() if isinstance(body, str) else body
        self.send_response(200); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path == "/api/status":
            with STATE["lock"]:
                data = STATE["data"]
            self._send(json.dumps(data or {"status": "probing…"}), "application/json")
        elif self.path in ("/", "/index.html"):
            self._send(PAGE, "text/html")
        else:
            self.send_response(404); self.end_headers()
    def log_message(self, *a):
        pass

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--port", type=int, default=8000); ap.add_argument("--interval", type=int, default=60)
    a = ap.parse_args()
    print("First probe running…", flush=True); run_probe(); print("First probe done.", flush=True)
    threading.Thread(target=loop, args=(a.interval,), daemon=True).start()
    print(f"Dashboard live at http://localhost:{a.port} (Ctrl+C to stop)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()

if __name__ == "__main__":
    main()
