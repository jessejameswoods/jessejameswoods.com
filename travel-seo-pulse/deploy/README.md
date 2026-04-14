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
