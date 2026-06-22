#!/usr/bin/env python3

import json
import sys
import time

ORANGE = "\033[38;2;215;119;87m"   # #D77757
WHITE  = "\033[38;2;255;255;255m"
BLUE   = "\033[38;2;177;185;249m"  # #B1B9F9
EMPTY  = "\033[38;2;80;83;112m"    # #505370
RESET  = "\033[0m"
BLOCK  = "█"
DOT    = " · "


def makeProgressBar(pct: float, width: int = 10) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = round(pct * width / 100)
    unfilled = width - filled

    bar = ""
    if filled:
        bar += BLUE + BLOCK * filled + RESET
    if unfilled:
        bar += EMPTY + BLOCK * unfilled + RESET

    return f"{bar} {BLUE}{int(pct):3d}%{RESET}"


def fmtK(n: int) -> str:
    return f"{round(n / 1000)}k"


def formatTimeRemaining(epoch: float) -> str:
    remaining = epoch - time.time()
    if remaining <= 0:
        return ""
    totalMinutes = int(remaining / 60)
    totalHours, minutes = divmod(totalMinutes, 60)
    days, hours = divmod(totalHours, 24)
    if days:
        return f"({days}d {hours}h)"
    if totalHours:
        return f"({totalHours}h {minutes}m)"
    return f"({minutes}m)"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return

    model          = (data.get("model") or {}).get("display_name") or "Unknown model"
    effort         = (data.get("effort") or {}).get("level")
    ctx            = data.get("context_window") or {}
    ctxUsed        = ctx.get("used_percentage")
    ctxTokensTotal = ctx.get("context_window_size")
    ctxTokensUsed  = ctx.get("total_input_tokens") + ctx.get("total_output_tokens")

    rateLimits = data.get("rate_limits") or {}
    fiveHour   = rateLimits.get("five_hour") or {}
    sevenDay   = rateLimits.get("seven_day") or {}
    fivePct    = fiveHour.get("used_percentage")
    fiveReset  = fiveHour.get("resets_at")
    weekPct    = sevenDay.get("used_percentage")
    weekReset  = sevenDay.get("resets_at")

    # Line 1: Model [effort] · Context bar
    modelStr = f"{ORANGE}Claude {model}"
    if effort is not None:
        modelStr += f" [{effort}]"
    modelStr += RESET

    parts = [modelStr]
    if ctxUsed is not None:
        ctxSegment = f"{WHITE}Context{RESET}  {makeProgressBar(ctxUsed)}"
        if ctxTokensUsed is not None and ctxTokensTotal is not None:
            ctxSegment += f" ({fmtK(ctxTokensUsed)} / {fmtK(ctxTokensTotal)})"
        else:
            ctxSegment += f"  (" + str(ctxTokensUsed) + f" / " + str(ctxTokensTotal) + f")"
        parts.append(ctxSegment)

    print(DOT.join(parts))

    # Line 2: Session bar (time) · Weekly bar (time)
    rateParts = []

    if fivePct is not None:
        segment = f"{WHITE}Session{RESET}  {makeProgressBar(fivePct)}"
        if fiveReset:
            eta = formatTimeRemaining(fiveReset)
            if eta:
                segment += f" {eta}"
        rateParts.append(segment)

    if weekPct is not None:
        segment = f"{WHITE}Weekly{RESET}  {makeProgressBar(weekPct)}"
        if weekReset:
            eta = formatTimeRemaining(weekReset)
            if eta:
                segment += f" {eta}"
        rateParts.append(segment)

    if rateParts:
        print(DOT.join(rateParts))


if __name__ == "__main__":
    main()
