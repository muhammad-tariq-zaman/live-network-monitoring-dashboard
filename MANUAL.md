# Live Network Monitoring Dashboard — Full Manual

A small, working, dependency-free network monitor in the style of the
shared-internet-path dashboard in the reference photo: one vantage
point, a set of probed sites, latency per probe, and a CRITICAL alerts
panel on the right. Built with Python's standard library only, plus
`curl` for the HTTPS probes.

> **What this is, honestly:** this is a real prober and a real live
> dashboard — not a mockup. The numbers on the dashboard are measured
> on every probe run. The screenshots in `screenshots/` are rendered
> from that same live probe data (the sandbox Chromium cannot start
> headless here, so screenshots are drawn from `status.json`, with the
> same values the live page shows). Run `dashboard.py` and you get the
> live page itself.

## 1. The idea, in one paragraph

One machine (the "vantage point") repeatedly asks a list of hosts:
can I resolve you (DNS)? Can I open TCP 443? Can I complete a TLS
handshake? Does an HTTPS request succeed, and how long did each step
take? The answers are grouped by site, coloured OK (green) or
CRITICAL/DOWN (red), and anything that fails appears in the alerts
panel with the exact failure. A set of public baselines (Google,
Google DNS, Cloudflare DNS) sits next to your own sites, so you can
tell a *site* outage apart from an *internet* outage: if the baselines
are green and your site is red, the problem is the site, not your
connection.

## 2. What it monitors (default targets)

| Group | Targets | Why |
|---|---|---|
| Your sites | Portfolio (GitHub Pages), AI Tools Blog (Blogspot), Custom Designs Store (Shopify) | The author's own public sites |
| Hakeem Walee — WFS nodes | WFS-1, WFS-2, WFS-4, WFS-6, WFS-10, WFS-11 at Hakeem Walee | The nodes shown in the reference photo, probed — never assumed |
| Baselines | Google DNS (8.8.8.8), Cloudflare DNS (1.1.1.1), Google | The photo's "Office & Internet" panel: ISP uplinks and public baselines |

Edit the list in `probe.py` (`DEFAULT_TARGETS`) or pass your own
`--targets targets.json` file with the same fields
(`id`, `name`, `host`, `url`, `group`). No target is ever reported
"up" without a probe: a page that merely loads in a browser is not
evidence, and this tool never carries a live label from an earlier run.

## 3. How a probe works, step by step

For every target, in order:

1. **DNS** — `getaddrinfo(host, 443)`, timed in ms. DNS failure →
   status DOWN, alert `SiteUnreachable`.
2. **TCP 443** — connect, timed in ms. TCP failure → DOWN,
   `SiteUnreachable`.
3. **TLS** — handshake via curl's `time_appconnect`, timed in ms.
   TLS failure after a TCP connect → CRITICAL,
   `HTTPSUnreachableWhileTCP` (the exact alert wording from the photo).
4. **HTTPS** — GET the target URL, timed in ms, HTTP status recorded.
   HTTP 200–399 → OK. Any other outcome after a working TCP path →
   CRITICAL, `HTTPSUnreachableWhileTCP`.

Status rules, plainly:

- **OK** — HTTPS returned 200–399.
- **CRITICAL** — the TCP path answered but HTTPS did not (the most
  useful distinction in this whole tool: the network path is alive,
  the web service is not, or something in between is breaking TLS/HTTP).
- **DOWN** — even TCP 443 did not answer, or DNS failed.

There is deliberately **no ICMP ping** in this build on this host:
the sandbox blocks raw sockets (`ping: Operation not permitted`), so
ICMP is reported as *unavailable*, never as a failure. On a normal
office PC, VPS or Raspberry Pi, add a ping probe next to the TCP
probe — the structure in `probe.py` is built for exactly that
one-function addition. The photo's probes were ICMP + TCP 443 + TLS;
this build does the two that work everywhere, plus the HTTPS check
that actually decides "is the site usable?".

## 4. Running it (the whole process)

### Requirements

- Python 3.10+ (standard library only — no `pip install` needed)
- `curl` (used for the HTTPS probes, because it follows proxies
  correctly where raw sockets do not)
- A machine that can reach the internet: your PC, a VPS, or a
  Raspberry Pi on the office network. For a true office view, run it
  *inside* the office, not in a cloud sandbox, so the latency you see
  is the office's latency, not a proxy's.

### Option A — live dashboard (recommended)

```bash
cd network-monitoring-dashboard
python3 dashboard.py --port 8000 --interval 60
# open http://localhost:8000
```

- A background thread re-probes every `--interval` seconds (default 60).
- The page fetches `/api/status` every 30 seconds and redraws itself.
- Every probe run also writes `status.json` in the same folder, so
  other tools (a status page, a log shipper, an alerting script) can
  read the same data without touching the dashboard.
- Stop with Ctrl+C. Keep it running with `nohup` or a systemd unit
  (see §7).

### Option B — one-off probe (for a quick check or a cron job)

```bash
python3 probe.py --out status.json
```

Prints the full JSON result and writes `status.json`. Run it from
cron every 5 minutes and you have a history file to graph later.

### Option C — from a fresh clone

```bash
git clone https://github.com/muhammad-tariq-zaman/live-network-monitoring-dashboard.git
cd live-network-monitoring-dashboard
python3 dashboard.py
```

That is the whole install. There is no database to set up, no Docker
image to pull, and no account to create.

## 5. Real-time test — what actually happened (29 Oct 2026)

Tested from this monitor against the real, public internet
(12 targets, probe run 29 Oct 2026, ~19:48 PKT). This is a real test
result, not sample data:

| Target | Status | HTTP | TCP 443 | TLS | HTTPS total |
|---|---|---|---|---|---|
| Portfolio (GitHub Pages) | OK | 200 | ~1 ms | ~162 ms | ~495 ms |
| AI Tools Blog (Blogspot) | OK | 200 | ~1 ms | ~103 ms | ~905 ms |
| Custom Designs Store (Shopify) | OK | 200 | ~1 ms | ~89 ms | ~1,434 ms |
| WFS-1 | CRITICAL | 000 | ~1 ms | ~94 ms | timeout 8,002 ms |
| WFS-2 | CRITICAL | 000 | ~1 ms | ~112 ms | ~706 ms |
| WFS-4 | CRITICAL | 000 | ~1 ms | ~96 ms | timeout 8,002 ms |
| WFS-6 | CRITICAL | 000 | ~1 ms | ~98 ms | timeout 8,002 ms |
| WFS-10 | CRITICAL | 000 | ~1 ms | ~94 ms | ~801 ms |
| WFS-11 | CRITICAL | 000 | ~1 ms | ~90 ms | timeout 8,001 ms |
| Google DNS | OK | 200 | ~1 ms | ~94 ms | ~315 ms |
| Cloudflare DNS | OK | 200 | ~2 ms | ~98 ms | ~1,080 ms |
| Google | OK | 200 | ~1 ms | ~81 ms | ~501 ms |

**Summary: 6 OK, 6 CRITICAL, 0 DOWN.**

Read it correctly: the author's own three sites and all three public
baselines are up, while all six WFS nodes at Hakeem Walee fail HTTPS
(TCP answers, TLS starts, then the HTTPS request fails — hence
`HTTPSUnreachableWhileTCP`, not `SiteUnreachable`). That is the same
pattern the photo's right panel shows. Two cautions, stated plainly:

- The ~1 ms TCP times are measured through this sandbox's egress
  proxy, not from Rawalpindi to Hetzner — do not compare them with
  the photo's 147–165 ms office-to-Falkenstein latency. Run the tool
  in the office to get the office's real numbers.
- "CRITICAL from here" does not prove "down for everyone": these
  nodes may be intentionally private, VPN-only, or blocked from this
  network. The dashboard reports what *this* vantage point sees, and
  says so on the page. That honesty is a feature, not a bug.

## 6. Applications and advantages

- **See an outage before users report it.** A red card + alert beats
  a phone call from an angry user.
- **Separate site outages from internet outages.** Baselines green +
  site red = the site (or its host) is the problem. Everything red =
  look at your own connection first.
- **Pinpoint the failing layer.** DNS vs TCP vs TLS vs HTTPS tells
  you whether to call the ISP, the hosting provider, or check the
  web server — instead of guessing.
- **Evidence for providers.** "HTTPS failed at 19:48 PKT while TCP
  answered, here are the timings" gets a faster, better answer from
  a host or ISP than "the site is down".
- **Zero cost, zero account.** Python stdlib + curl, no SaaS
  subscription, no data leaving your network except the probes
  themselves.
- **Portfolio-ready, truthfully.** It is a working tool with a real
  test run, not a screenshot of someone else's dashboard — and the
  manual says exactly what it can and cannot measure.
- **Extensible in one function.** Add a ping probe, an alert webhook
  (email/Telegram), or a history graph by editing `probe.py` /
  `dashboard.py` — both files are short and commented.

## 7. Keeping it running (optional)

```bash
# simple, survives logout (not reboot):
nohup python3 dashboard.py --port 8000 --interval 60 > server.log 2>&1 &
# on a Linux server, prefer a systemd unit that restarts it on boot
# and on failure; point it at the same command above.
```

## 8. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Everything CRITICAL, TCP ~1 ms | You are behind an egress proxy (like this sandbox) | Expected here; run it on a direct network for true values, or keep it as a proxy-path monitor and label it as such |
| `ping: Operation not permitted` | Raw sockets blocked on this host | Normal here; ICMP is reported unavailable, not failed |
| Dashboard page loads but says "probing…" | First probe still running (WFS nodes can take 8 s each on timeout) | Wait ~40 s and refresh; lower `--interval` only after the first run finishes |
| Port 8000 already in use | Another copy is running | Stop the old one, or run with `--port 8001` |
| A target you added shows DOWN | DNS or TCP genuinely failing from this vantage point | Check the target from another network before declaring it down everywhere |

## 9. Files in this repository

- `probe.py` — the prober (targets, probe steps, status rules, JSON output)
- `dashboard.py` — the live server (background probing, `/` page, `/api/status`)
- `status.json` — latest probe result (regenerated on every run)
- `MANUAL.md` — this manual
- `README.md` — short overview + quick start
- `screenshots/` — dashboard images rendered from live probe data
- `targets.json` (optional) — your own target list, if you do not want
  to edit `probe.py`

## 10. Limits, stated plainly

- One vantage point only: results describe that machine's view.
- No history graph or alerting webhook yet — `status.json` is the
  hook for both, and they are the natural next steps.
- No authentication on the dashboard page: run it on localhost or
  behind your own firewall/VPN, not open to the internet.
- Latency measured through a proxy is proxy latency, not
  end-to-end latency — label it as such wherever you show it.
