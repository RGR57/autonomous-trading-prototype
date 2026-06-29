#!/usr/bin/env python3
"""
Main orchestrator: iterative prompt-loop (generate -> evaluate -> critic -> rewrite)
Objective is set to 'maximize profit' in context.
"""
import os
import time
import json
from dotenv import load_dotenv
from copy import deepcopy

from llm_client import LLMClient
from data_client import DataClient
from backtester import Backtester
from risk_manager import RiskManager
from execution_adapter import ExecutionAdapter
from audit import AuditLogger

load_dotenv()

MAX_ITERS = int(os.getenv("MAX_ITERS", 6))
NUM_CANDIDATES = int(os.getenv("NUM_CANDIDATES", 3))
MODE = os.getenv("MODE", "PAPER").upper()

def fingerprint(candidate_json, critic_text):
    return hash(json.dumps(candidate_json, sort_keys=True) + critic_text)

def pick_best(results):
    # results: list of (candidate_json, metrics)
    # ranking: prefer higher net_return then sharpe
    def score(m):
        return m.get("net_return", -999) * 1000 + m.get("sharpe", -999)
    best = max(results, key=lambda cr: score(cr[1]))
    return best

def run_cycle(assets=["BTC-USD"], lookback_minutes=120, objective="maximize profit"):
    llm = LLMClient()
    data = DataClient(csv_path="data/btc_1m_sample.csv")
    backtester = Backtester()
    risk = RiskManager()
    exec_adapter = ExecutionAdapter(mode=MODE)
    audit = AuditLogger()

    snapshot = data.get_snapshot(assets, lookback_minutes)
    context = {
        "assets": assets,
        "snapshot_meta": snapshot.meta_summary(),
        "objective": objective
    }
    seen = set()
    best_so_far = (None, {"sharpe": -999, "net_return": -999})

    for it in range(MAX_ITERS):
        print(f"[orchestrator] iteration {it+1}/{MAX_ITERS}")
        # Use the strategy prompt for reference; mock LLM will ignore textual prompt and use context
        strategy_prompt = open("prompts/strategy_prompt.txt").read().format(**context, N=NUM_CANDIDATES)
        candidates = llm.generate_strategy(strategy_prompt, n=NUM_CANDIDATES, context=context)

        results = []
        for c in candidates:
            metrics = backtester.run(c, snapshot)
            results.append((c, metrics))
            audit.log_candidate(c, metrics, iteration=it)
            # Check acceptance + risk
            if metrics.get("PASS") and risk.approve(c, metrics):
                # Execute in PAPER or LIVE depending on MODE (paper by default)
                exec_adapter.execute(c, metrics, dry_run=(MODE != "LIVE"))
                audit.log_execution(c, metrics, mode=MODE.lower(), iteration=it)
                print("[orchestrator] Executed candidate (PAPER mode or dry_run).")
                return {"status": "executed", "candidate": c, "metrics": metrics}

        # pick best by ranking
        best_candidate, best_metrics = pick_best(results)
        if best_metrics.get("sharpe", -999) > best_so_far[1].get("sharpe", -999):
            best_so_far = (deepcopy(best_candidate), deepcopy(best_metrics))

        # Critic evaluates best candidate and returns feedback
        critic_prompt = open("prompts/critic_prompt.txt").read().format(candidate=json.dumps(best_candidate), metrics=json.dumps(best_metrics))
        critic_response = llm.run_critic(critic_prompt, context=context)
        sig = fingerprint(best_candidate, critic_response)
        if sig in seen:
            print("[orchestrator] no-change detected; stopping iterations.")
            break
        seen.add(sig)

        # Rewrite step: ask LLM to produce a revised candidate(s) following critic feedback
        rewrite_prompt = open("prompts/strategy_prompt.txt").read() + "\n\nCRITIC_FEEDBACK:\n" + critic_response
        revised = llm.generate_strategy(rewrite_prompt, n=1, context=context, revise_from=best_candidate)
        # Put revised candidate as the first candidate in the next loop implicitly (mock generator uses it)
        llm.seed_revised_candidate(revised[0])

        time.sleep(0.5)

    # fallback: return best for human review
    print("[orchestrator] Exiting; best candidate returned for review.")
    audit.log_for_review(best_so_far[0], best_so_far[1])
    return {"status": "review", "best": best_so_far}

if __name__ == "__main__":
    res = run_cycle()
    print("Result:", json.dumps(res, indent=2))
