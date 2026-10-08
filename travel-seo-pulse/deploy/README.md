# travel-seo-pulse deploy

Scripts to build the Hetzner VPS that runs the daily newsletter publisher.

## Current production host
- Provider: Hetzner Cloud, CAX11 (ARM), Helsinki (hel1)
- Server name: `travel-seo-pulse`
- OS: Debian/Ubuntu
- User: `pulse` (non-login service user)
- Schedule: systemd timer, `Mon..Fri 06:00 Europe/Berlin` (04:00 UTC)
- Monitoring: healthchecks.io (email alerts on missed run or failure)

## Files
- `setup.sh` - idempotent installer (run once on a fresh VPS)
- `travel-seo-pulse-run.sh` - wrapper executed by systemd on each run
- `travel-seo-pulse.service` - systemd unit (oneshot)
- `travel-seo-pulse.timer` - systemd timer (weekday schedule)
- `env.example` - template for `/etc/travel-seo-pulse.env`

## Rebuild from scratch
```bash
# 1. Provision fresh VPS, get its IP
# 2. Copy deploy dir + run setup
scp -r deploy/ root@<vps>:/root/
ssh root@<vps> "bash /root/deploy/setup.sh"

# 3. Create secrets file (uses values from env.example)
ssh root@<vps> "nano /etc/travel-seo-pulse.env && chmod 600 /etc/travel-seo-pulse.env"

# 4. Test
ssh root@<vps> "systemctl start travel-seo-pulse.service && journalctl -u travel-seo-pulse.service -n 100 --no-pager"
```

## Common ops
```bash
# Check next scheduled run
systemctl list-timers travel-seo-pulse.timer

# Force a run now
systemctl start travel-seo-pulse.service

# Tail latest log
tail -f /var/log/travel-seo-pulse/run-*.log

# Update code on VPS (the wrapper also does this on each run)
sudo -u pulse git -C /opt/travel-seo-pulse pull
```

## Refreshing the Substack cookie

**Fast path (no DevTools), on the VPS as root:**
```bash
tsp-substack-login --request          # Substack emails "Sign in to Substack" to the owner address
tsp-substack-login 'https://substack.com/sign-in?...'   # paste the link from that email
```
The second command signs in server-side, writes the fresh cookie into
/etc/travel-seo-pulse.env (backup kept) and runs the read-only auth check.
Links are single-use and expire within minutes; if it says no session was set,
run --request again and use the newest email.

**Manual path (DevTools), if the fast path ever stops working:**

`SUBSTACK_COOKIE` eventually expires, and Substack separately refuses the
publish+send call on sessions it considers too old ("For your security, please
sign out and sign back in", HTTP 403) even while reads and draft creation still
work (seen 2026-10-08 on a 177-day-old cookie). Either way the fix is the same:

1. Log in to Substack in Chrome (the account that owns the publication). If the
   failure was the 403 above, sign out and sign back in first so the session is fresh.
2. Open DevTools (F12) → **Network** tab → refresh the page.
3. Find any request to `substack.com` (e.g. `subscription/unread/subscriptions`).
4. Right-click → **Copy** → **Copy as fetch (Node.js)**.
5. Paste somewhere scratch and copy the full string assigned to the `cookie`
   header (everything between the quotes after `"cookie":`). The code accepts
   either this full header or the bare `substack.sid` value.
6. Update the VPS env:
   ```bash
   ssh root@<vps> "nano /etc/travel-seo-pulse.env"
   # Replace the SUBSTACK_COOKIE=... line, save, chmod 600
   ```
7. Test WITHOUT publishing anything:
   ```bash
   ssh root@<vps> "set -a; . /etc/travel-seo-pulse.env; set +a; \
     /opt/travel-seo-pulse/.venv/bin/python /opt/travel-seo-pulse/travel-seo-pulse/deploy/substack_auth_check.py"
   ```
   Do NOT re-run `travel-seo-pulse.service` to test on a day the pipeline already
   created a draft: it builds a second draft and can send the issue twice.
   If today's issue is sitting unsent, open the draft in Substack and publish it by hand.

No restart of the timer is needed — the wrapper re-sources the env on every run.

## Secrets inventory

| Key | Where it comes from | Expires? |
|---|---|---|
| `ANTHROPIC_API_KEY` | platform.claude.com → API keys | No, but balance runs out |
| `SUBSTACK_USER_ID` | Your Substack user ID (numeric) | No |
| `SUBSTACK_COOKIE` | Chrome DevTools (see above) | Yes, periodically |
| `HEALTHCHECK_URL` | healthchecks.io dashboard | No |

