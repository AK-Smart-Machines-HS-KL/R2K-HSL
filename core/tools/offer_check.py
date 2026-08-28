#!/usr/bin/env python3
"""Periodic OpenRouter special-offer check for the ROS2K model selection strategy.

Detects free and discounted OpenRouter models and diffs them against the
curated whitelist. Designed to run BEFORE an opencode TUI starts (bash
wrapper) and from cron (daily backstop).

Modes:
  default         fetch offers, write report, AUTO-ADD eligible candidates
                  to whitelist + favorites (slot-limited, quality-gated)
  --no-auto-add   report only, no config changes
  --force         ignore the 24h interval guard (never bypasses the TUI guard)
  --verbose       print skip reasons
  --cron          log to file instead of stdout, exit silently on skip

Auto-add quality gate (all must pass):
  - tool calling ("tools" in supported_parameters)
  - context >= MIN_CONTEXT_TOKENS
  - no roleplay/translation vendor or slug keyword
  - free or cheap pricing (same thresholds as detection)
Only MAX_OFFER_ENTRIES offer entries exist; reviewed offers (mnemonic
"offer:") are eviction-proof, auto ones ("offer (auto, unreviewed)")
evict each other FIFO when the cap is exceeded (D1b).
Candidates not added (no free slot) stay un-seen and retry next check;
only added slugs enter the seen-ledger (D3: free first, then cheapest
output price).

Safety guards (always active):
  - skips if any opencode TUI process is running (state-file flush race,
    see model_selection_strategy.md gotcha #1/#2)
  - skips if last run < CHECK_INTERVAL_S ago (implements the 1d timeout)

Docs: core/docs/model_selection_strategy.md (v1.5, gotchas #1-#5).
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

CHECK_INTERVAL_S = 24 * 3600
API_URL = "https://openrouter.ai/api/v1/models"
MODELS_PAGE_URL = "https://openrouter.ai/models"
HTTP_TIMEOUT_S = 30

FREE_PRICE = 0.0
CHEAP_INPUT_MAX_USD = 0.10   # per 1M tokens
CHEAP_OUTPUT_MAX_USD = 0.30  # per 1M tokens
TOKENS_PER_MILLION = 1_000_000  # API prices are per-token strings

MAX_OFFER_ENTRIES = 3  # offer favorites cap — oldest auto offer is evicted
OFFER_NAME_PREFIXES = ("offer:", "offer (auto, unreviewed)")
REVIEWED_PREFIX = "offer:"

# auto-add quality gate (unreviewed adds must clear ALL of these)
MIN_CONTEXT_TOKENS = 256_000          # D2: 256K+
AUTO_EXCLUDED_KEYWORDS = ("hy-mt", "-rp-")          # translation / roleplay slugs
AUTO_EXCLUDED_VENDORS = ("sao10k", "gryphe", "anthracite-org")  # RP/fiction vendors

NON_TEXT_KEYWORDS = [
    "image", "video", "audio", "tts", "embed", "translat", "voice",
    "upscale", "music", "lyria", "veo", "avatar", "vision-exp", "recraft",
    "flux", "wan-", "heygen", "safeguard", "content-safety",
]

# not interactive offers: bulk API variants and OpenRouter meta-routers
EXCLUDED_SUFFIXES = [":batch"]
EXCLUDED_PREFIXES = ["openrouter/", "~"]

HOME = os.path.expanduser("~")
LIVE_CONFIG_PATH = f"{HOME}/.config/opencode/opencode.json"
LIVE_STATE_PATH = f"{HOME}/.local/state/opencode/model.json"
PKG_CONFIG_PATH = f"{HOME}/R2K-HSL/core/docs/opencode-team-package/config/opencode.json"
PKG_STATE_PATH = f"{HOME}/R2K-HSL/core/docs/opencode-team-package/share/model.json"
RUN_STATE_PATH = f"{HOME}/.local/state/opencode/offer_check.json"
REPORT_PATH = f"{HOME}/.local/state/opencode/offer_report.md"
PROVIDER_KEY = "openrouter"
AUTO_MNEMONIC = "offer (auto, unreviewed)"


def tui_running():
    result = subprocess.run(
        ["pgrep", "-x", "opencode"], capture_output=True
    )
    return result.returncode == 0


def load_run_state():
    try:
        with open(RUN_STATE_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_run": 0.0, "seen": []}


def mark_run(seen_new):
    state = load_run_state()
    state["last_run"] = time.time()
    seen = set(state.get("seen", []))
    seen.update(seen_new)
    state["seen"] = sorted(seen)
    os.makedirs(os.path.dirname(RUN_STATE_PATH), exist_ok=True)
    with open(RUN_STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ros2k-offer-check/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
        return json.loads(resp.read().decode())


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ros2k-offer-check/1.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S) as resp:
        return resp.read().decode(errors="replace")


def is_text_model(slug):
    lowered = slug.lower()
    if any(kw in lowered for kw in NON_TEXT_KEYWORDS):
        return False
    if any(lowered.endswith(sfx) for sfx in EXCLUDED_SUFFIXES):
        return False
    return not any(lowered.startswith(pfx) for pfx in EXCLUDED_PREFIXES)


def build_pricing_map(models):
    pricing = {}
    for m in models:
        slug = m.get("id", "")
        if not slug:
            continue
        pr = m.get("pricing", {})
        try:
            pin = float(pr.get("prompt", "1")) * TOKENS_PER_MILLION
            pout = float(pr.get("completion", "1")) * TOKENS_PER_MILLION
        except (TypeError, ValueError):
            continue
        pricing[slug] = (pin, pout)
    return pricing


def build_candidates(models, pricing):
    candidates = {}
    for m in models:
        slug = m.get("id", "")
        if not slug or not is_text_model(slug) or slug not in pricing:
            continue
        pin, pout = pricing[slug]
        reason = None
        if pin == FREE_PRICE and pout == FREE_PRICE:
            reason = "free"
        elif pin <= CHEAP_INPUT_MAX_USD and pout <= CHEAP_OUTPUT_MAX_USD:
            reason = f"cheap (${pin:.3g}/${pout:.3g} per 1M)"
        if reason:
            candidates[slug] = {
                "name": m.get("name", slug),
                "context": m.get("context_length", "?"),
                "tools_ok": "tools" in (m.get("supported_parameters") or []),
                "reason": reason,
                "url": f"https://openrouter.ai/{slug}",
            }

    try:
        page = fetch_text(MODELS_PAGE_URL)
        for pct, slug in re.findall(
            r"(\d+)%\s*off[^a-z]{0,80}?([a-z0-9_.~-]+/[a-z0-9_.:~-]+)", page
        ):
            if slug in candidates or not is_text_model(slug):
                continue
            candidates[slug] = {
                "name": slug,
                "context": "?",
                "tools_ok": False,  # unverifiable from badge scrape
                "reason": f"promo {pct}% off",
                "url": f"https://openrouter.ai/{slug}",
            }
    except Exception:
        pass

    return candidates


def is_auto_eligible(slug, info):
    """Auto-add quality gate: tools + min context + no RP/translation."""
    if not info["tools_ok"]:
        return False
    if not isinstance(info["context"], int) or info["context"] < MIN_CONTEXT_TOKENS:
        return False
    vendor = slug.split("/")[0].lower()
    if vendor in AUTO_EXCLUDED_VENDORS:
        return False
    return not any(kw in slug.lower() for kw in AUTO_EXCLUDED_KEYWORDS)


def rank_for_add(new, pricing):
    """D3: free first, then cheapest output price."""
    def sort_key(item):
        slug, info = item
        is_free = info["reason"] == "free"
        pout = pricing.get(slug, (float("inf"), float("inf")))[1]
        return (0 if is_free else 1, pout, slug)

    return sorted(new.items(), key=sort_key)


def write_report(new, known):
    lines = [
        "# OpenRouter offer check",
        f"_generated: {time.strftime('%Y-%m-%d %H:%M %Z')} | "
        f"known in whitelist: {len(known)} | new candidates: {len(new)}_",
        "",
    ]
    if new:
        lines += [
            "| Model | Why | Context | Link |",
            "|---|---|---|---|",
        ]
        for slug, info in sorted(new.items()):
            lines.append(
                f"| `{slug}` | {info['reason']} | {info['context']} | {info['url']} |"
            )
        lines += [
            "",
            "Verify tool-calling + benchmarks on the model page before promoting",
            "to a reviewed favorite (see strategy doc v1.5 changelog).",
        ]
    else:
        lines.append("No new free/cheap/promo text models outside the whitelist.")
    with open(REPORT_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")


def evaluate_offers(offer_slugs, pricing):
    """Split offer slugs into (active, [(slug, why_expired), ...]).

    An offer is expired when the model is delisted or its price no longer
    meets the free/cheap thresholds (e.g. a promo discount ended). Unknown
    billing (negative prices) is kept.
    """
    active, expired = [], []
    for slug in offer_slugs:
        prices = pricing.get(slug)
        if prices is None:
            expired.append((slug, "delisted from OpenRouter"))
            continue
        pin, pout = prices
        if pin < 0 or pout < 0:
            active.append(slug)
        elif (pin == FREE_PRICE and pout == FREE_PRICE) or (
            pin <= CHEAP_INPUT_MAX_USD and pout <= CHEAP_OUTPUT_MAX_USD
        ):
            active.append(slug)
        else:
            expired.append((slug, f"price now ${pin:.3g}/${pout:.3g} per 1M"))
    return active, expired


def remove_entries(slugs, cfgs, states):
    slug_set = set(slugs)
    for cfg in cfgs:
        p = cfg["provider"][PROVIDER_KEY]
        p["whitelist"] = [s for s in p["whitelist"] if s not in slug_set]
        for s in slug_set:
            p["models"].pop(s, None)
    for state in states:
        for key in ("favorite", "recent"):
            state[key] = [
                e for e in state[key]
                if not (e["providerID"] == "openrouter" and e["modelID"] in slug_set)
            ]


def maintain_offers(pricing, live_cfg, live_state):
    """Expire stale offers, then enforce MAX_OFFER_ENTRIES (D1b).

    Expiry removes any offer (reviewed or auto) that is delisted or priced
    above the thresholds. The cap evicts only AUTO offers, oldest first;
    reviewed offers ("offer:") are eviction-proof. Offers are identified by
    the mnemonic prefix in the live config models block; order follows the
    live favorites list (bottom = oldest).
    """
    offer_named = {
        slug for slug, meta in live_cfg["provider"][PROVIDER_KEY]["models"].items()
        if str(meta.get("name", "")).startswith(OFFER_NAME_PREFIXES)
    }
    in_order = [
        e["modelID"] for e in live_state["favorite"]
        if e["providerID"] == "openrouter" and e["modelID"] in offer_named
    ]

    _, expired = evaluate_offers(in_order, pricing)
    evictions = list(expired)
    expired_slugs = {s for s, _ in expired}

    surviving = [s for s in in_order if s not in expired_slugs]
    auto = [s for s in surviving if s not in reviewed_offers(live_cfg)]
    overflow = max(0, len(surviving) - MAX_OFFER_ENTRIES)
    evictions += [(s, f"offer cap {MAX_OFFER_ENTRIES} exceeded") for s in auto[:overflow]]

    if not evictions:
        return []

    evict_slugs = [s for s, _ in evictions]
    with open(PKG_CONFIG_PATH) as f:
        pkg_cfg = json.load(f)
    with open(PKG_STATE_PATH) as f:
        pkg_state = json.load(f)
    remove_entries(evict_slugs, [live_cfg, pkg_cfg], [live_state, pkg_state])
    for path, data in (
        (LIVE_CONFIG_PATH, live_cfg),
        (PKG_CONFIG_PATH, pkg_cfg),
        (LIVE_STATE_PATH, live_state),
        (PKG_STATE_PATH, pkg_state),
    ):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    return evictions


def reviewed_offers(cfg):
    """Slugs whose config mnemonic marks them as human-reviewed offers."""
    return {
        slug for slug, meta in cfg["provider"][PROVIDER_KEY]["models"].items()
        if str(meta.get("name", "")).startswith(REVIEWED_PREFIX)
    }


def auto_add(new):
    with open(LIVE_CONFIG_PATH) as f:
        live_cfg = json.load(f)
    with open(PKG_CONFIG_PATH) as f:
        pkg_cfg = json.load(f)
    with open(LIVE_STATE_PATH) as f:
        live_state = json.load(f)
    with open(PKG_STATE_PATH) as f:
        pkg_state = json.load(f)

    for cfg in (live_cfg, pkg_cfg):
        provider = cfg["provider"][PROVIDER_KEY]
        for slug, info in new.items():
            if slug not in provider["whitelist"]:
                provider["whitelist"].append(slug)
            provider["models"].setdefault(slug, {})[
                "name"
            ] = f"{AUTO_MNEMONIC} - {info['name']} - OpenRouter"

    entry = [{"providerID": "openrouter", "modelID": slug} for slug in new]
    for state in (live_state, pkg_state):
        for key in ("favorite", "recent"):
            existing = {(e["providerID"], e["modelID"]) for e in state[key]}
            state[key].extend(e for e in entry if (e["providerID"], e["modelID"]) not in existing)

    for path, data in (
        (LIVE_CONFIG_PATH, live_cfg),
        (PKG_CONFIG_PATH, pkg_cfg),
        (LIVE_STATE_PATH, live_state),
        (PKG_STATE_PATH, pkg_state),
    ):
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")


def main():
    args = set(sys.argv[1:])
    cron_mode = "--cron" in args
    verbose = "--verbose" in args
    out = open(os.devnull, "w") if cron_mode else sys.stdout

    if tui_running():
        if verbose:
            print("skip: opencode TUI running (state-file flush race)", file=out)
        return 0
    run_state = load_run_state()
    if "--force" not in args and (time.time() - run_state["last_run"]) < CHECK_INTERVAL_S:
        if verbose:
            print("skip: checked within the last 24h", file=out)
        return 0

    print("looking for special offers ...", file=out)
    try:
        models = fetch_json(API_URL).get("data", [])
        pricing = build_pricing_map(models)
        candidates = build_candidates(models, pricing)
        with open(LIVE_CONFIG_PATH) as f:
            live_cfg = json.load(f)
        with open(LIVE_STATE_PATH) as f:
            live_state = json.load(f)
    except Exception as exc:
        print(f"error: {exc}", file=out)
        return 1
    known = live_cfg["provider"][PROVIDER_KEY]["whitelist"]

    reported_before = set(run_state.get("seen", []))
    new = {
        s: i for s, i in candidates.items()
        if s not in known and s not in reported_before
    }
    write_report(new, known)

    removals = maintain_offers(pricing, live_cfg, live_state)
    for slug, why in removals:
        print(f"expired/evicted: {slug} ({why})", file=out)

    if new:
        print(f"{len(new)} new offer candidate(s), report: {REPORT_PATH}", file=out)
        for slug, info in sorted(new.items()):
            print(f"  {slug}  [{info['reason']}]", file=out)
    elif not removals:
        print("no new offers", file=out)

    if "--no-auto-add" in args:
        mark_run(new.keys())
        return 0

    reviewed = reviewed_offers(live_cfg)
    offer_named = {
        slug for slug, meta in live_cfg["provider"][PROVIDER_KEY]["models"].items()
        if str(meta.get("name", "")).startswith(OFFER_NAME_PREFIXES)
    }
    in_order = [
        e["modelID"] for e in live_state["favorite"]
        if e["providerID"] == "openrouter" and e["modelID"] in offer_named
    ]
    expired_slugs = {s for s, _ in removals}
    live_offers = [s for s in in_order if s not in expired_slugs]
    available = max(0, MAX_OFFER_ENTRIES - len(live_offers))

    eligible = [
        (s, i) for s, i in rank_for_add(new, pricing)
        if is_auto_eligible(s, i)
    ]
    to_add = eligible[:available]
    blocked = eligible[available:]

    if to_add:
        auto_add(dict(to_add))
        for slug, info in to_add:
            print(f"auto-added: {slug}  [{info['reason']}] -> 'offer (auto, unreviewed)'", file=out)
    if blocked:
        print(f"{len(blocked)} eligible candidate(s) waiting for a free offer slot (retry next check)", file=out)
        for slug, info in blocked:
            print(f"  waiting: {slug}  [{info['reason']}]", file=out)
    if not to_add and not blocked and new:
        print("no candidate passed the auto-add quality gate", file=out)

    mark_run([s for s, _ in to_add])
    if to_add:
        print("restart opencode to see them", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
