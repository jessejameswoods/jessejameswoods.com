#!/usr/bin/env python3
"""Refresh SUBSTACK_COOKIE on the VPS from a Substack sign-in (magic) link.

No DevTools, no copying cookies by hand. Flow:
  1. Request a sign-in email:   tsp_substack_login.py --request
     (Substack emails "Sign in to Substack" to the publication owner's address)
  2. Either paste the 6-digit code from that email:
     tsp_substack_login.py --code 123456
     or the sign-in link:
     tsp_substack_login.py 'https://substack.com/sign-in?...'
     The script completes the sign-in server-side, captures the fresh
     substack.sid that Substack sets, writes it into /etc/travel-seo-pulse.env
     (backup kept), and runs the read-only auth check. The cookie value is
     never printed.

  If --request does not produce an email (seen 2026-10-08: the API answered
  200 {} from the server but sent nothing), request the code from a browser
  instead: on travelsearchpulse.com, DevTools console:
    fetch('/api/v1/email-login',{method:'POST',credentials:'include',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email:'jjwoods3@gmail.com',for_pub:'jessejameswoods',redirect:'/'})})
  Substack then emails "<code> is your Substack verification code".

Why this exists: on 2026-10-08 Substack refused publish+send on a 177-day-old
session ("For your security, please sign out and sign back in"). A fresh
sign-in is the fix; this makes it a one-line job.
"""
import os
import re
import shutil
import subprocess
import sys
import time

ENV_PATH = "/etc/travel-seo-pulse.env"
EMAIL = "jjwoods3@gmail.com"
PUB = "jessejameswoods"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


def request_link():
    import requests
    r = requests.post(
        "https://substack.com/api/v1/email-login",
        headers={"User-Agent": UA, "Content-Type": "application/json",
                 "Origin": "https://substack.com", "Referer": "https://substack.com/sign-in"},
        json={"email": EMAIL, "for_pub": PUB, "redirect": "/", "captcha_response": None},
        timeout=20,
    )
    print(f"sign-in email requested -> HTTP {r.status_code}")
    return 0 if r.ok else 1


def _store_session(s) -> int:
    """Write the substack.* cookies from a logged-in session into the env and verify."""
    sid = s.cookies.get("substack.sid", domain="substack.com") or s.cookies.get("substack.sid")
    if not sid:
        print("ERROR: Substack did not set a session. Codes/links are single-use and expire "
              "within minutes; run --request again and use the newest email.")
        return 1
    # Store the bare session value, not a "substack.sid=..." header: every
    # script on the box (substack_publisher, tsp_unpublish, diag/probe tools)
    # builds its own header from the bare value, and tsp_unpublish prefixing
    # an already-prefixed value is exactly what broke the sweep on 2026-10-08.
    header = sid
    with open(ENV_PATH) as f:
        lines = f.read().splitlines()
    backup = f"{ENV_PATH}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(ENV_PATH, backup)
    out, replaced = [], False
    for line in lines:
        if line.startswith("SUBSTACK_COOKIE="):
            out.append(f"SUBSTACK_COOKIE={header}")
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(f"SUBSTACK_COOKIE={header}")
    with open(ENV_PATH, "w") as f:
        f.write("\n".join(out) + "\n")
    os.chmod(ENV_PATH, 0o640)
    print(f"SUBSTACK_COOKIE refreshed (session cookie length {len(sid)}). Backup: {backup}")
    env = dict(os.environ)
    for line in out:
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k] = v
    check = os.path.join(os.path.dirname(os.path.abspath(__file__)), "substack_auth_check.py")
    return subprocess.call([sys.executable, check], env=env)


def complete_code(code: str) -> int:
    """Exchange the 6-digit emailed code for a session (the endpoint Substack's own sign-in page uses)."""
    import requests
    code = re.sub(r"\D", "", code)
    if len(code) != 6:
        print("ERROR: the code is 6 digits")
        return 2
    s = requests.Session()
    s.headers["User-Agent"] = UA
    r = s.post(
        "https://substack.com/api/v1/email-otp-login/complete",
        headers={"Content-Type": "application/json", "Origin": "https://substack.com",
                 "Referer": "https://substack.com/sign-in"},
        json={"code": code, "email": EMAIL, "redirect": "/", "for_pub": PUB, "island_magic_signin": False},
        timeout=30,
    )
    print(f"otp complete -> HTTP {r.status_code}")
    if not r.ok:
        print(r.text[:200])
        return 1
    return _store_session(s)


def consume_link(url: str) -> int:
    import requests
    if not url.startswith("https://substack.com/") and not url.startswith("https://www.substack.com/"):
        print("ERROR: that is not a substack.com sign-in link")
        return 2
    s = requests.Session()
    s.headers["User-Agent"] = UA
    s.get(url, allow_redirects=True, timeout=30)
    return _store_session(s)


def main(argv):
    if len(argv) == 2 and argv[1] == "--request":
        return request_link()
    if len(argv) == 3 and argv[1] == "--code":
        return complete_code(argv[2])
    if len(argv) == 2 and argv[1].startswith("http"):
        return consume_link(argv[1].strip())
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
