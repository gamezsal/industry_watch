# Industry Watch — Institutional Semiconductor Sector Intelligence

[![ADK](https://img.shields.io/badge/ADK-v0.5.0-blue.svg)](https://adk.dev/)
[![Model](https://img.shields.io/badge/Model-Gemini%202.5%20Flash-4285F4.svg)](https://cloud.google.com/vertex-ai)
[![Runtime](https://img.shields.io/badge/Runtime-Vertex%20AI%20Agent%20Engine-34A853.svg)](https://cloud.google.com/vertex-ai/docs/agent-engine/overview)
[![Security](https://img.shields.io/badge/Security-Model%20Armor%20Screened-EA4335.svg)](https://cloud.google.com/security/model-armor)
[![Evaluation](https://img.shields.io/badge/Verbatim%20Citations-100%25%20Pass-brightgreen.svg)](tests/eval/)

**Industry Watch** is an institutional-grade sector intelligence agent designed for semiconductor equity research and corporate governance monitoring. Tracking leading semiconductor enterprises—**NVIDIA (NVDA)**, **Advanced Micro Devices (AMD)**, **Intel (INTC)**, **Micron Technology (MU)**, and **Broadcom (AVGO)**—it deterministically reconciles unverified public news claims against authoritative SEC Form 8-K filings, scores corporate materiality, executes joins inside a sandboxed Python runtime, and persists analyst preferences across sessions.

---

## 🏛️ Architecture Overview

```mermaid
graph TD
    Analyst["Analyst / Client (CLI Playground / Gemini Enterprise)"] --> Security["Google Cloud Model Armor Screening"]
    Security --> Agent["Industry Watch Root Agent (Gemini 2.5 Flash)"]
    
    subgraph State & Persistence
        Agent <--> Sessions["Agent Platform AI Sessions (Multi-Turn State)"]
        Agent <--> Memory["Agent Platform Memory Bank (Watch-list & Preferences)"]
    end

    subgraph Deterministic Tooling Layer (No Internal LLM)
        Agent --> ToolSEC["fetch_company_disclosures (SEC EDGAR 8-K)"]
        Agent --> ToolGDELT["fetch_public_claims (GDELT & IR Feeds)"]
        Agent --> ToolArmor["screen_with_model_armor (Prompt Injection / Jailbreak)"]
    end

    subgraph Secure Execution Sandbox
        Agent --> Sandbox["AgentEngineSandboxCodeExecutor (Vertex AI Reasoning Engine)"]
        Sandbox --> ToolReconcile["reconcile_claims_vs_disclosures (Join & Item Taxonomy Scoring)"]
    end

    ToolSEC --> SECAPI["SEC EDGAR Submissions API (Compliant User-Agent)"]
    ToolGDELT --> GDELTAPI["GDELT DOC 2.0 API (Throttled & Fallback Cache)"]
```

---

## ✨ Core Capabilities

1. **Deterministic Function Tools (Zero Model Hallucination)**:
   - **`fetch_company_disclosures`**: Queries official SEC EDGAR submissions API with compliant User-Agent headers (`IndustryWatchSectorIntelligence/1.0`), extracting accession numbers, items, and dates.
   - **`fetch_public_claims`**: Ingests GDELT news and corporate IR feeds, treating all media as strictly untrusted. Enforces rate throttling (0.2s minimum spacing) and local caching.
   - **`reconcile_claims_vs_disclosures`**: Joins filings and media claims within a rolling date window, classifying into **Matched**, **Filing-Only**, and **Claim-Only** buckets.
2. **SEC Form 8-K Materiality Taxonomy Scoring**:
   - Deterministic materiality scoring across 8-K item codes:
     - **Critical (Score 90–100)**: Items 1.03 (Bankruptcy), 1.05 (Cybersecurity), 2.02 (Results of Operations/Earnings), 4.01/4.02 (Accountant changes/Restatements), 5.01 (Change in Control).
     - **High (Score 70–80)**: Items 1.01 (Material Agreements), 1.02 (Termination), 2.01 (Acquisitions/Dispositions), 2.05 (Restructuring/Layoffs), 5.02 (Executive/Director Departures).
     - **Medium (Score 40–60)**: Items 2.03 (Financial Obligations), 7.01 (Reg FD), 8.01 (Other Events).
     - **Low (Score 10–30)**: Items 5.07 (Shareholder Votes), 9.01 (Exhibits).
3. **Sandboxed Code Execution**:
   - Reconciliation joins and materiality computations execute inside the Vertex AI Agent Engine code-execution sandbox (`AgentEngineSandboxCodeExecutor`).
4. **Multi-Turn State & Cross-Session Memory Bank**:
   - In-session multi-turn dialogue state powered by **Agent Platform AI Sessions**.
   - Long-term memory persisted via **Agent Platform Memory Bank**, remembering custom watch-lists, sector coverage, and briefing format preferences.
5. **Model Armor Security Integration**:
   - Screens user prompts, model responses, and external news claims against prompt injection and jailbreak attacks using Google Cloud Model Armor template `projects/<PROJECT_ID>/locations/<LOCATION>/templates/<MODEL_ARMOR_TEMPLATE_ID>`.
6. **Least-Privilege Agent Identity**:
   - Deployed with dedicated service account `<SERVICE_ACCOUNT_NAME>@<PROJECT_ID>.iam.gserviceaccount.com` restricted strictly to `roles/agentplatform.expressUser`, `roles/serviceusage.serviceUsageConsumer`, `roles/browser`, and `roles/modelarmor.user`.
7. **Deterministic Evaluation & Groundedness Metric**:
   - 100% verified citation constraint: every accession number and 8-K item code cited by the agent must appear verbatim in tool outputs. Zero hallucination tolerance.

---

## 📁 Project Structure

```
industry-watch/
├── app/
│   ├── __init__.py
│   ├── agent.py                        # Root agent definition & sector analyst instructions
│   ├── agent_runtime_app.py            # Vertex AI Agent Runtime entrypoint
│   └── tools/
│       ├── __init__.py                 # Exported tools & ADK FunctionTool wrappers
│       ├── memory.py                   # Memory Bank preference persistence tools
│       ├── model_armor.py              # Google Cloud Model Armor screening tool
│       ├── public_claims.py            # GDELT & IR feeds claims collector (throttled)
│       ├── reconcile.py                # Sandbox-executed reconciliation & join logic
│       ├── sec_edgar.py                # SEC EDGAR Form 8-K disclosure collector
│       └── taxonomy.py                 # 8-K item codes, weights, and ticker mapping
├── tests/
│   ├── eval/
│   │   ├── datasets/
│   │   │   ├── curated_analyst_scenarios.json   # 3 curated multi-turn evaluation cases
│   │   │   └── multi_turn_analyst_eval.json     # Synthesized multi-turn conversation traces
│   │   ├── metrics/
│   │   │   └── deterministic_citations.py       # Verbatim accession & 8-K item citation grader
│   │   ├── baseline_results.json                # Pre-optimization evaluation baseline
│   │   ├── candidate_results.json               # Post-optimization candidate evaluation results
│   │   ├── eval_config.yaml                     # Evaluator configuration
│   │   └── run_multi_turn_eval.py               # Multi-turn evaluation benchmark runner
│   ├── unit/
│   │   ├── test_eval_metrics.py                 # Tests for deterministic citation metrics
│   │   ├── test_model_armor.py                  # Unit tests for Model Armor screening
│   │   └── test_tools.py                        # Unit tests for SEC, GDELT, and reconcile tools
├── deployment/
│   └── iam_bindings.json               # Least-privilege IAM bindings specification
├── deployment_metadata.json            # Deployed Reasoning Engine resource metadata
├── pyproject.toml                      # Project dependencies and tool configurations
└── README.md                           # Project documentation
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python**: `>= 3.10`
- **uv**: Astral's Python package manager ([Installation Guide](https://docs.astral.sh/uv/getting-started/installation/))
- **Google Cloud SDK**: Authenticated via `gcloud auth application-default login`

### 2. Dependency Installation
```bash
# Install dependencies using uv
uv sync

# Or using the agents-cli
agents-cli install
```

### 3. Local Development Playground
Launch the local interactive development playground to test multi-turn conversations and inspect tool calls:
```bash
agents-cli playground
```

---

## 🛠️ CLI Commands & Workflows

| Command | Purpose |
| :--- | :--- |
| `agents-cli playground` | Starts local web-based testing UI with live hot-reloading |
| `uv run pytest tests/unit/` | Executes all 21 unit tests across tools, security, and metrics |
| `agents-cli deploy` | Deploys agent to Vertex AI Agent Runtime (Reasoning Engine) |
| `agents-cli publish gemini-enterprise` | Registers deployed agent with Gemini Enterprise |
| `agents-cli eval compare BASE CAND` | Evaluates regression diff between baseline and candidate runs |

---

## 🧪 Evaluation Framework & Regression Testing

The project includes an evaluation suite specifically designed for financial and compliance applications where regulatory grounding is critical:

### Benchmark Metrics
1. **Multi-Turn Task Success (1–5)**: Topic and entity coverage across sequential corporate pivots.
2. **Tool-Use Quality (1–5)**: Invocation fidelity, parameter targeting, and query accuracy.
3. **Hallucination Freedom (1–5)**: Factual alignment and demarcation of untrusted news claims.
4. **Deterministic Verbatim Groundedness (Pass / Fail)**: Deterministically verifies that **every** cited SEC accession number (`XXXXXX-YY-ZZZZZZ`) and Form 8-K item code (`X.YY`) was present verbatim in the tool output.

### Running Evaluations
```bash
# Run multi-turn benchmark against curated analyst scenarios
uv run python tests/eval/run_multi_turn_eval.py tests/eval/datasets/curated_analyst_scenarios.json tests/eval/candidate_results.json

# Compare results against baseline to verify zero regression
agents-cli eval compare tests/eval/baseline_results.json tests/eval/candidate_results.json
```

### Evaluation Results (Baseline vs. Candidate)

| Metric | Baseline | Candidate | Delta | Status |
| :--- | :---: | :---: | :---: | :---: |
| **Multi-Turn Task Success** | **4.00 / 5.00** | **4.67 / 5.00** | **+0.67** | **Improved** |
| **Tool-Use Quality** | **5.00 / 5.00** | **5.00 / 5.00** | `0.00` | **Zero Regression** |
| **Hallucination Freedom** | **5.00 / 5.00** | **5.00 / 5.00** | `0.00` | **Zero Regression** |
| **Verbatim Citations Pass Rate** | **100.0%** | **100.0%** | `0.0%` | **100% Deterministic Pass** |

---

## ☁️ Cloud Deployment & Production Publishing

### 1. Active Reasoning Engine Deployment
The agent is deployed to Vertex AI Reasoning Engine:
- **Resource Name**: `projects/<PROJECT_NUMBER>/locations/<LOCATION>/reasoningEngines/<REASONING_ENGINE_ID>`
- **Location**: `<LOCATION>` (e.g. `us-central1`)
- **Dedicated Service Account**: `<SERVICE_ACCOUNT_NAME>@<PROJECT_ID>.iam.gserviceaccount.com`

### 2. Publishing to Gemini Enterprise
Publish the deployed agent directly to a Gemini Enterprise App with auto-detected metadata:
```bash
agents-cli publish gemini-enterprise \
  --registration-type adk \
  --gemini-enterprise-app-id projects/<PROJECT_NUMBER>/locations/global/collections/default_collection/engines/<APP_ID> \
  --project-id <PROJECT_ID> \
  --display-name "Industry Watch Sector Intelligence" \
  --description "Institutional semiconductor sector-intelligence analyst tracking NVDA, AMD, INTC, MU, AVGO with SEC Form 8-K reconciliation."
```
*Note: The CLI automatically reads `remote_agent_runtime_id` and `deployment_target` from [`deployment_metadata.json`](deployment_metadata.json).*

---

## 🔒 Security & Compliance

- **Model Armor Prompt Screening**: All prompts, responses, and unverified news texts are inspected by Model Armor template `projects/<PROJECT_ID>/locations/<LOCATION>/templates/<MODEL_ARMOR_TEMPLATE_ID>`.
- **SEC EDGAR Compliance**: Requests include user-agent attribution adhering strictly to SEC Fair Access guidelines.
- **Untrusted Media Quarantine**: News articles and third-party commentary from GDELT are tagged as untrusted and quarantined from regulatory facts unless corroborated by an official SEC 8-K accession number.
