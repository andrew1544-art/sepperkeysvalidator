# test_serper_keys.py
# Place your keys in a file called "keys.txt" in the same folder (one per line, or comma-separated)
# Run: python test_serper_keys.py

import requests
import os
import time
from datetime import datetime
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# ─── Config ───────────────────────────────────────────────────────────────────
KEYS_FILE   = "keys.txt"       # File with API keys (one per line or comma-separated)
TEST_QUERY  = "test school"    # Light query to check if key works
TIMEOUT     = 10               # Seconds per request
MAX_WORKERS = 5                # Parallel threads (Serper allows up to 5 req/sec free tier)
EXPORT_FILE = "working_keys.txt"  # Written at the end if any valid keys found

# ANSI colors
GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"


# ─── Load keys ────────────────────────────────────────────────────────────────
def load_keys(filepath):
    if not os.path.exists(filepath):
        print(f"{RED}File '{filepath}' not found!{RESET}")
        print(f"Create a {CYAN}keys.txt{RESET} file with one API key per line.")
        return []

    keys = []
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            for k in line.split(","):
                k = k.strip()
                if k and len(k) >= 20:
                    keys.append(k)
    return keys


# ─── Test a single key ────────────────────────────────────────────────────────
def test_key(key, retry_on_rate_limit=True):
    """
    Returns dict:
      status   : 'valid' | 'no_credits' | 'invalid' | 'rate_limited' | 'timeout' | 'dead' | 'error'
      detail   : human-readable string
      credits  : int or None  (remaining credits from header)
      limit    : int or None  (total credit limit from header)
    """
    url     = "https://google.serper.dev/search"
    headers = {"X-API-KEY": key, "Content-Type": "application/json"}
    body    = {"q": TEST_QUERY}

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=TIMEOUT)

        # ── Pull credit info from headers ──────────────────────────────────
        credits_remaining = None
        credits_limit     = None
        try:
            credits_remaining = int(resp.headers.get("X-RateLimit-Remaining",
                                    resp.headers.get("x-ratelimit-remaining", -1)))
            credits_limit     = int(resp.headers.get("X-RateLimit-Limit",
                                    resp.headers.get("x-ratelimit-limit", -1)))
            if credits_remaining == -1: credits_remaining = None
            if credits_limit     == -1: credits_limit     = None
        except (ValueError, TypeError):
            pass

        if resp.status_code == 200:
            data  = resp.json()
            count = len(data.get("organic", []))

            # Build detail string with credit info if available
            if credits_remaining is not None and credits_limit is not None:
                pct    = int((credits_remaining / credits_limit) * 100) if credits_limit else 0
                detail = f"{count} results | {credits_remaining:,}/{credits_limit:,} credits ({pct}% left)"
            elif credits_remaining is not None:
                detail = f"{count} results | {credits_remaining:,} credits remaining"
            else:
                detail = f"{count} results"

            return {"status": "valid", "detail": detail,
                    "credits": credits_remaining, "limit": credits_limit}

        elif resp.status_code == 429:
            if retry_on_rate_limit:
                time.sleep(2)
                return test_key(key, retry_on_rate_limit=False)
            return {"status": "rate_limited", "detail": "Rate limited (429) — try again later",
                    "credits": None, "limit": None}

        elif resp.status_code in (400, 402, 403):
            msg = ""
            try:
                msg = resp.json().get("message", "")
            except Exception:
                msg = resp.text[:100]

            lower = msg.lower()

            # Check body message FIRST (Serper sends "Not enough credits" as 400)
            if "not enough credits" in lower or "no credits" in lower:
                detail = "Out of credits"
                if credits_remaining is not None:
                    detail += f" ({credits_remaining:,} remaining)"
                return {"status": "no_credits", "detail": detail,
                        "credits": credits_remaining, "limit": credits_limit}

            if "invalid" in lower or "unauthorized" in lower or "expired" in lower:
                return {"status": "invalid", "detail": f"Invalid/expired key — {msg}",
                        "credits": None, "limit": None}

            if "rate" in lower or "too many" in lower:
                if retry_on_rate_limit:
                    time.sleep(2)
                    return test_key(key, retry_on_rate_limit=False)
                return {"status": "rate_limited", "detail": "Rate limited",
                        "credits": None, "limit": None}

            return {"status": "dead", "detail": f"HTTP {resp.status_code}: {msg}",
                    "credits": None, "limit": None}

        else:
            return {"status": "dead", "detail": f"HTTP {resp.status_code}",
                    "credits": None, "limit": None}

    except requests.Timeout:
        return {"status": "timeout", "detail": "Request timed out",
                "credits": None, "limit": None}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:80],
                "credits": None, "limit": None}


# ─── Credit bar ───────────────────────────────────────────────────────────────
def credit_bar(remaining, limit, width=20):
    if remaining is None or limit is None or limit == 0:
        return ""
    filled = int((remaining / limit) * width)
    pct    = int((remaining / limit) * 100)
    bar    = "█" * filled + "░" * (width - filled)
    color  = GREEN if pct > 50 else YELLOW if pct > 20 else RED
    return f" {color}[{bar}]{RESET} {pct}%"


# ─── Estimate credit reset ────────────────────────────────────────────────────
def estimate_reset():
    now        = datetime.now()
    next_month = now.month + 1 if now.month < 12 else 1
    next_year  = now.year if now.month < 12 else now.year + 1
    reset_date = datetime(next_year, next_month, 1)
    days_left  = (reset_date - now).days
    return f"~{days_left} days (estimated 1st of next month)"


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print(f"\n{BOLD}{'═'*62}{RESET}")
    print(f"{BOLD}  SERPER API KEY TESTER{RESET}")
    print(f"{BOLD}{'═'*62}{RESET}\n")

    keys = load_keys(KEYS_FILE)
    if not keys:
        return

    key_counts = Counter(keys)
    duplicates = {k: v for k, v in key_counts.items() if v > 1}
    unique_keys = list(dict.fromkeys(keys))

    print(f"  File:         {CYAN}{KEYS_FILE}{RESET}")
    print(f"  Total read:   {len(keys)}")
    print(f"  Unique keys:  {len(unique_keys)}")
    if duplicates:
        dup_total = sum(v - 1 for v in duplicates.values())
        print(f"  {MAGENTA}Duplicates:   {dup_total} extra copies found{RESET}")
        for k, count in duplicates.items():
            print(f"    {DIM}{k[:16]}...{RESET} appears {count}x")
    print(f"\n{BOLD}Testing {len(unique_keys)} keys (parallel, {MAX_WORKERS} threads)...{RESET}\n")

    # ── Parallel testing ──────────────────────────────────────────────────────
    ordered_results = [None] * len(unique_keys)

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_idx = {executor.submit(test_key, key): i
                         for i, key in enumerate(unique_keys)}

        completed = 0
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            key = unique_keys[idx]
            res = future.result()
            ordered_results[idx] = (key, res)
            completed += 1
            # Live progress tick
            short  = key[:12] + "..."
            status = res["status"]
            detail = res["detail"]
            bar    = credit_bar(res["credits"], res["limit"])

            if status == "valid":
                print(f"  [{completed:3d}/{len(unique_keys)}] {GREEN}✅ VALID{RESET}        {short}{bar}")
                print(f"           {DIM}{detail}{RESET}")
            elif status == "no_credits":
                print(f"  [{completed:3d}/{len(unique_keys)}] {RED}💀 NO CREDITS{RESET}   {short}{bar}")
                print(f"           {DIM}{detail}{RESET}")
            elif status == "invalid":
                print(f"  [{completed:3d}/{len(unique_keys)}] {RED}🚫 INVALID{RESET}      {short}")
                print(f"           {DIM}{detail}{RESET}")
            elif status == "rate_limited":
                print(f"  [{completed:3d}/{len(unique_keys)}] {YELLOW}⏳ RATE LIMITED{RESET} {short}")
                print(f"           {DIM}{detail}{RESET}")
            elif status == "timeout":
                print(f"  [{completed:3d}/{len(unique_keys)}] {YELLOW}⏱️  TIMEOUT{RESET}     {short}")
            else:
                print(f"  [{completed:3d}/{len(unique_keys)}] {RED}❌ DEAD{RESET}         {short}")
                print(f"           {DIM}{detail}{RESET}")

    # ── Bucket results ────────────────────────────────────────────────────────
    buckets = {s: [] for s in ["valid","no_credits","invalid","rate_limited","timeout","dead","error"]}
    for key, res in ordered_results:
        buckets[res["status"]].append((key, res))

    valid_keys    = [k for k, _ in buckets["valid"]]
    no_credit_cnt = len(buckets["no_credits"])
    invalid_cnt   = len(buckets["invalid"])
    rate_cnt      = len(buckets["rate_limited"])
    timeout_cnt   = len(buckets["timeout"])
    dead_cnt      = len(buckets["dead"]) + len(buckets["error"])
    dup_cnt       = sum(v - 1 for v in duplicates.values())

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'═'*62}{RESET}")
    print(f"{BOLD}  RESULTS SUMMARY{RESET}")
    print(f"{BOLD}{'═'*62}{RESET}\n")
    print(f"  {GREEN}✅ Valid:          {len(valid_keys):3d}{RESET}")
    print(f"  {RED}💀 No Credits:     {no_credit_cnt:3d}{RESET}")
    print(f"  {RED}🚫 Invalid/Expired:{invalid_cnt:3d}{RESET}")
    print(f"  {YELLOW}⏳ Rate Limited:   {rate_cnt:3d}{RESET}  (may still work — retry later)")
    print(f"  {YELLOW}⏱️  Timeouts:       {timeout_cnt:3d}{RESET}  (network issue — retry later)")
    print(f"  {RED}❌ Dead/Error:     {dead_cnt:3d}{RESET}")
    print(f"  {DIM}{'─'*32}{RESET}")
    print(f"  {BOLD}Total tested:     {len(unique_keys):3d}{RESET}")
    if dup_cnt:
        print(f"  {MAGENTA}Duplicates skipped:{dup_cnt:2d}{RESET}")

    if no_credit_cnt > 0:
        print(f"\n  {YELLOW}💡 No-credit keys reset: {estimate_reset()}{RESET}")
        print(f"     Free tier = 2,500 searches/month. Paid plans check serper.dev.")

    # ── Working keys ──────────────────────────────────────────────────────────
    if valid_keys:
        csv = ",".join(valid_keys)
        print(f"\n{BOLD}  Working keys — paste into .env:{RESET}")
        print(f"  {GREEN}SERPER_API_KEYS={csv}{RESET}\n")

        with open(EXPORT_FILE, "w") as f:
            f.write("# Working Serper API keys\n")
            f.write(f"# Tested: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"# Keys: {len(valid_keys)}\n\n")
            f.write(f"SERPER_API_KEYS={csv}\n\n")
            f.write("# One per line:\n")
            for k in valid_keys:
                f.write(f"{k}\n")
        print(f"  {CYAN}Also saved to: {EXPORT_FILE}{RESET}")
    else:
        print(f"\n  {RED}No working keys found.{RESET}")
        print(f"  Get free keys at: {CYAN}https://serper.dev{RESET}")

    # ── Dead keys ──────────────────────────────────────────────────────────────
    all_dead_keys = [k for k, _ in buckets["no_credits"] + buckets["invalid"] +
                     buckets["dead"] + buckets["error"]]
    if all_dead_keys:
        print(f"\n{BOLD}  Dead keys (remove from .env):{RESET}")
        for k in all_dead_keys:
            print(f"  {RED}{k[:16]}...{RESET}")

    print(f"\n{BOLD}{'═'*62}{RESET}\n")


if __name__ == "__main__":
    main()