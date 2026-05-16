\# Serper API Key Validator



Python script to bulk-validate Serper.dev API keys. Reads keys from a text file, tests each one against the Serper API, and prints a clear summary showing valid, expired, rate-limited, and duplicate keys — with real credit counts from the API headers.



\## Features



\- ✅ Tests all keys in one run with a lightweight query

\- ⚡ \*\*Parallel testing\*\* — 5 threads run simultaneously (5× faster)

\- 📊 \*\*Real credit counts\*\* — shows remaining/total credits per key with a visual bar

\- 🎯 Smart error classification — body content checked before trusting HTTP status (catches Serper's quirk of sending "Not enough credits" as HTTP 400)

\- 🔁 \*\*Rate-limit retry\*\* — waits 2s and retries once on 429 before marking as rate-limited

\- 🔍 Detects and reports duplicate keys

\- 💾 \*\*Auto-exports\*\* working keys to `working\_keys.txt` pre-formatted for `.env`

\- 🕐 Estimates when free-tier credits will reset

\- 🎨 Color-coded terminal output with per-key credit progress bars



\## Quick Start



\### 1. Clone



```bash

git clone https://github.com/andrew1544-art/sepperkeysvalidator.git

cd sepperkeysvalidator

```



\### 2. Install dependencies



```bash

pip install requests

```



\### 3. Add your keys



Create a `keys.txt` file in the project folder. Paste your API keys — one per line, or comma-separated:



```

0cb6ada6c422944bb558b1fba0725bc57d820c64

be91589e61b034f4ab07b2207131e2719a4d6963

783993fe349e51f8a5ca75cb1f02984fe629c09f

```



Or all on one line:



```

key1,key2,key3,key4

```



Lines starting with `#` are treated as comments and ignored.



\### 4. Run



```bash

python test\_serper\_keys.py

```



\## Example Output



```

══════════════════════════════════════════════════════════════

&#x20; SERPER API KEY TESTER

══════════════════════════════════════════════════════════════



&#x20; File:         keys.txt

&#x20; Total read:   39

&#x20; Unique keys:  38

&#x20; Duplicates:   1 extra copy found



Testing 38 keys (parallel, 5 threads)...



&#x20; \[  1/38] ✅ VALID        0cb6ada6c422...

&#x20;          10 results | 1,847/2,500 credits \[████████████░░░░░░░░] 73%

&#x20; \[  2/38] ✅ VALID        be91589e61b0...

&#x20;          10 results | 412/2,500 credits  \[███░░░░░░░░░░░░░░░░░░] 16%

&#x20; \[  3/38] 💀 NO CREDITS   46d36666c4a1...

&#x20;          Out of credits (0 remaining)

&#x20; \[  4/38] 🚫 INVALID      deadbeef1234...

&#x20;          Invalid/expired key — Unauthorized

&#x20; \[  5/38] ⏳ RATE LIMITED  f9a12c3d8e00...

&#x20;          Rate limited (429) — try again later



══════════════════════════════════════════════════════════════

&#x20; RESULTS SUMMARY

══════════════════════════════════════════════════════════════



&#x20; ✅ Valid:           20

&#x20; 💀 No Credits:      15

&#x20; 🚫 Invalid/Expired:  2

&#x20; ⏳ Rate Limited:     1   (may still work — retry later)

&#x20; ⏱️  Timeouts:         0   (network issue — retry later)

&#x20; ❌ Dead/Error:        0

&#x20; ────────────────────────────────

&#x20; Total tested:       38

&#x20; Duplicates skipped:  1



&#x20; 💡 No-credit keys reset: \~15 days (estimated 1st of next month)

&#x20;    Free tier = 2,500 searches/month. Paid plans check serper.dev.



&#x20; Working keys — paste into .env:

&#x20; SERPER\_API\_KEYS=0cb6ada6...,be91589e...,783993fe...



&#x20; Also saved to: working\_keys.txt



&#x20; Dead keys (remove from .env):

&#x20; 46d36666...

&#x20; deadbeef...

══════════════════════════════════════════════════════════════

```



\## Output File



After each run, `working\_keys.txt` is written automatically:



```

\# Working Serper API keys

\# Tested: 2025-05-16 14:32

\# Keys: 20



SERPER\_API\_KEYS=key1,key2,key3,...



\# One per line:

key1

key2

key3

```



Copy the `SERPER\_API\_KEYS=` line straight into your `.env` file.



\## Key Status Guide



| Status | Meaning | Action |

|--------|---------|--------|

| ✅ Valid | Key works and has credits | Use it |

| 💀 No Credits | Key is valid but monthly credits exhausted | Wait for reset or upgrade |

| 🚫 Invalid | Key is malformed, revoked, or expired | Delete it |

| ⏳ Rate Limited | Hit the 5 req/sec limit during testing | Retry in a minute |

| ⏱️ Timeout | Network issue — key may still be valid | Retry later |

| ❌ Dead/Error | Unexpected HTTP error | Investigate or delete |



\## Notes



\- Free Serper.dev keys get \*\*2,500 searches/month\*\*, resetting on the 1st of each month

\- The test uses a single lightweight query per key to minimize credit usage

\- Parallel testing uses 5 threads — safe for free-tier rate limits (5 req/sec)

\- Serper sometimes returns `"Not enough credits"` with HTTP status `400` instead of `402` — the script handles this correctly by checking the response body before trusting the status code

