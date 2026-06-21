# Antigravity_Environment_Max Sync Checklist

The following locally hardened `.agents/` rules and workflows have proven to be highly robust during the Hack2Skill challenge. They should be manually backported (copy-pasted) to the upstream `Antigravity_Environment_Max` template repository to ensure future projects inherit these enterprise-grade standards.

## 1. Hardened Core Rules
- `defensive-programming.md`
  - **Path**: `.agents/rules/defensive-programming.md`
  - **Changes**: Mandates Pydantic schema validation for ALL file I/O to prevent silent data loss (tier 0 safety rule).
- `sre-sop.md`
  - **Path**: `.agents/rules/sre-sop.md`
  - **Changes**: Enforces the continuous "Inner Loop" (mandatory test passes) and "Outer Loop" (master-sync) for SRE compliance.
- `rule-conflict-resolution.md`
  - **Path**: `.agents/rules/rule-conflict-resolution.md`
  - **Changes**: Establishes a strict 5-tier priority hierarchy to resolve contradictory LLM instructions deterministically.

## 2. Hardened SRE Workflows
- `test-automation.md`
  - **Path**: `.agents/workflows/test-automation.md`
  - **Changes**: Updated to ensure SRE compliance, blocking progress unless exit code 0 is met and manual UI verification instructions are provided.
- `error-observability.md`
  - **Path**: `.agents/workflows/error-observability.md`
  - **Changes**: Forces the LLM to context-compress and structurally log stack traces into JSON files before falling back to generic UI messages.

## 3. Deployment Architecture
- `deploy-streamlit-production.md`
  - **Path**: `.agents/workflows/deploy-streamlit-production.md`
  - **Changes**: Brand new workflow to rapidly deploy 1-file Python MVPs to Streamlit Community Cloud (bypassing HF Git LFS limitations).
- `deploy-hf-production.md`
  - **Path**: `.agents/workflows/deploy-hf-production.md`
  - **Changes**: Patched with a critical pre-flight step to abort the deployment if binary images are detected.

## Instructions
Please manually copy these files from this repository into the matching paths inside your local `Antigravity_Environment_Max` repository. Do not use automated `rm -rf` scripts, per our safety rules.
