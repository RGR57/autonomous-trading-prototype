# Autonomous Multi-Agent Trading Prototype (Paper Mode)

Purpose
- Minimal prototype that runs iterative prompt-loops (generate → evaluate → critic → rewrite) to propose and evaluate trade ideas.
- Main objective used by Strategy Agent: "maximize profit" (configured in orchestrator context).
- PAPER mode only by default — no real orders.

Contents
- orchestrator.py — main loop
- llm_client.py — mock LLM generator + optional OpenAI adapter
- data_client.py — loads CSV market data (data/btc_1m_sample.csv)
- backtester.py — simple bar-level backtester and metric calculator
- risk_manager.py — rule-based hard/soft gate
- execution_adapter.py — PAPER execution simulator
- audit.py — writes audit logs (logs/audit.log)
- prompts/*.txt — prompt templates (mostly for reference; mock LLM uses rule-based generator)
- data/btc_1m_sample.csv — synthetic 1-minute bars (sample)
- tests/test_backtester.py — basic unit test
- .env.example — environment variables

Quickstart (local)
1. Create a directory and paste files into it (preserve paths).
2. Create virtualenv and install deps:
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
3. Copy .env.example -> .env and edit if needed (MODE default PAPER)
   cp .env.example .env
4. Run tests:
   pytest
5. Run orchestrator:
   python orchestrator.py
   - The orchestrator runs up to MAX_ITERS and prints/logs cycles.
   - Executions are PAPER-only by default (dry_run). Audit logs are in logs/audit.log.

Safety and notes
- This is a prototype. Do not use live funds until you complete full validation and compliance checks.
- The system is tuned for "maximize profit" objective, but the RiskManager enforces conservative caps by default.
- The mock LLM is deterministic and safe for testing. To use a real LLM, replace the mock in `llm_client.py` with your provider (example adapter provided).

If you want:
- I can push this to a GitHub repo (you must provide owner/repo).
- I can generate a Dockerfile and CI config.
