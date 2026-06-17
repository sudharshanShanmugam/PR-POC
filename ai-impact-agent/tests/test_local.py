"""
Local smoke test — no real GitHub repo needed.
Simulates the full pipeline: webhook payload → analyze → report.

Run:  python test_local.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models import ChangedFile, PRDetails
from impact_analyzer import analyze_pr, rule_based_analysis

# --- Fake PR ---
pr = PRDetails(
    number=42,
    title="Add payment retry logic and fix order timeout",
    author="dev-alice",
    base_branch="main",
    head_branch="feature/payment-retry",
    repo="payment-service",
    owner="acme-corp",
)

# --- Fake changed files (mimicking GitHub API response) ---
files = [
    ChangedFile(
        filename="src/PaymentService.java",
        status="modified",
        additions=45,
        deletions=12,
        patch=(
            "@@ -101,6 +101,15 @@\n"
            "-        if (payment.isExpired()) throw new PaymentException();\n"
            "+        int retries = 0;\n"
            "+        while (retries < 3) {\n"
            "+            try {\n"
            "+                processPayment(payment);\n"
            "+                break;\n"
            "+            } catch (TransientException e) {\n"
            "+                retries++;\n"
            "+            }\n"
            "+        }\n"
        ),
    ),
    ChangedFile(
        filename="src/OrderController.java",
        status="modified",
        additions=8,
        deletions=3,
        patch=(
            "@@ -55,7 +55,12 @@\n"
            "-        order.setTimeout(5000);\n"
            "+        order.setTimeout(ORDER_TIMEOUT_MS);\n"
        ),
    ),
    ChangedFile(
        filename="src/config/AppConfig.java",
        status="modified",
        additions=2,
        deletions=0,
        patch="@@ -20,0 +21 @@\n+    public static final int ORDER_TIMEOUT_MS = 10_000;\n",
    ),
    ChangedFile(
        filename="test/PaymentServiceTest.java",
        status="added",
        additions=60,
        deletions=0,
        patch="@@ -0,0 +1,60 @@\n+// new retry test cases\n",
    ),
]

# ---- Run rule-based analysis (no API key needed) ----
print("=" * 60)
print("RULE-BASED ANALYSIS (no API key required)")
print("=" * 60)
result = rule_based_analysis(files)
for k, v in result.items():
    print(f"  {k}: {v}")

# ---- Run full pipeline (AI if key present, rule-based fallback) ----
print()
print("=" * 60)
print("FULL PIPELINE (AI if DEEPINFRA_API_KEY set, else rules)")
print("=" * 60)
report = analyze_pr(pr, files)
print(f"  PR:                  #{report.pr_number} — {pr.title}")
print(f"  Repo:                {report.repo}")
print(f"  Affected Components: {report.affected_components}")
print(f"  Change Type:         {report.change_type}")
print(f"  Risk:                {report.risk}")
print(f"  Summary:             {report.summary}")
print(f"  Changed Files:       {report.changed_files}")

# ---- Render the PR comment exactly as it would appear on GitHub ----
risk_emoji = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}.get(report.risk, "⚪")
components_md = "\n".join(f"- {c}" for c in report.affected_components)
files_md = "\n".join(f"- `{f}`" for f in report.changed_files)

comment = f"""\
## 🤖 AI Impact Analysis

| Field | Value |
|-------|-------|
| **Change Type** | {report.change_type} |
| **Risk** | {risk_emoji} {report.risk} |

### Affected Components
{components_md}

### Summary
{report.summary}

### Changed Files ({len(report.changed_files)})
{files_md}

---
*Generated automatically by AI Impact Agent*
"""

print()
print("=" * 60)
print("GITHUB PR COMMENT PREVIEW")
print("=" * 60)
print(comment)
