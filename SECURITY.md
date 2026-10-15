# Security Policy

## Supported Versions

Only the **latest minor release** of Hexaqual receives security fixes.
Older minor versions are not backported.

| Package | Supported |
|---|---|
| `hexaqual` (latest minor) | ✅ |
| Any older minor version | ❌ |

## Reporting a Vulnerability

> [!CAUTION]
> **Do not open a public GitHub issue for security vulnerabilities.** Public disclosure before a fix is available puts all users at risk.

Please report vulnerabilities using **GitHub's private vulnerability reporting**:

👉 [Open a private security advisory](https://github.com/TheTrueSCU/hexaqual/security/advisories/new)

Your report will be visible only to repository maintainers until a coordinated disclosure is agreed upon. Provide as much detail as possible:

- Affected package(s) and version(s)
- A description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept (PoC)
- Any suggested mitigations you have identified

## Scope

### In scope

- The core `hexaqual` CLI and governance engine at their latest minor release
- Third-party dependencies **directly introduced into a user's environment by Hexaqual** (i.e. listed in Hexaqual's own `dependencies` in `pyproject.toml`)
- Git hooks orchestration, quality gating invariants, and GitHub API automation tools

### Out of scope

- Target code analyzed by Hexaqual linters or test harnesses
- Third-party libraries not in Hexaqual's direct dependency graph
- Denial-of-service issues requiring physical access to the host
- Reports against unsupported older minor versions

## Response Timeline & SLA

| Milestone | Target |
|---|---|
| Initial Acknowledgement of report | Within **48 hours** |
| Triage and severity assessment | Within **7 business days** of acknowledgement |
| Coordinated fix & CVE assignment | Agreed with reporter; typically within **30 to 60 days** for critical issues |

We will keep you informed of progress at each milestone. If you believe a critical issue warrants an accelerated timeline, please state so in your report.

## Credit & Vulnerability Acknowledgment

We believe in giving credit where credit is due. Unless you request to remain anonymous, we will publicly credit you in our:
1. Release notes and `CHANGELOG.md`
2. GitHub Security Advisory release page
3. CVE metadata / attribution records

## Safe Harbour

Hexaqual maintainers commit to working in **good faith** with security researchers who:

- Report vulnerabilities privately before any public disclosure
- Avoid accessing, modifying, or destroying data that does not belong to them
- Do not degrade the availability of Hexaqual services or infrastructure
- Do not violate the privacy of other users

Researchers who follow these principles will not be subject to legal action related to their research. We will work with you to understand and resolve the issue promptly.

## Security Assurance Case

Hexaqual maintains a formal security assurance case to demonstrate why its security requirements and architectural guarantees are met.

### 1. Threat Model & Asset Identification
* **Primary Assets**: Integrity of pre-commit and pre-push quality gates, reproducibility of wheel and sdist distributions, isolation of shell command executions, and authenticity of PyPI / GitHub API requests.
* **Threat Vectors**:
  * *Arbitrary Command Execution*: Unsanitized arguments passed to subprocess tools (`pytest`, `ruff`, `ty`, `gh`).
  * *Privilege Escalation / Token Leakage*: Subprocess environments inadvertently exposing GitHub tokens or ambient secrets.
  * *Supply Chain Compromise*: Untrusted PyPI dependencies or unpinned build tools.
  * *Denial of Service / Unbounded Hangs*: Headless CI environments blocking on interactive terminal prompts.

### 2. Trust Boundaries
* **CLI Parameter Boundary**: CLI options, PR identifiers, and file paths are sanitized and validated before invoking underlying system tools.
* **Subprocess Isolation Boundary**: Tool execution runs with controlled environment variables and bounded timeouts; TTY interactivity is checked (`is_interactive_terminal`) to prevent headless hanging.
* **Release Boundary**: Packaging builds enforce byte-for-byte reproducibility (`hexaqual release reproducible`) and generate verified SLSA provenance.

### 3. Secure Design Principles Applied
* **Fail-Safe Defaults**: Quality checks fail closed on any non-zero exit code or uncaught diagnostic.
* **Hermetic Execution**: Fuzz harnesses and boundary tests execute in isolated temp directories.
* **Zero Shell Execution**: Subprocess invocations avoid `shell=True` and pass structured argument lists directly.

### 4. Implementation Security Weakness Countermeasures
* **Automated Static Analysis (SAST)**: Enforced via `Ruff` (security rules `S`), `ty check`, and GitHub `CodeQL`.
* **Automated Dependency Auditing (SCA)**: Continuous `Dependabot` vulnerability monitoring and pre-commit `pip-audit` scans.
* **Secret Detection**: `detect-secrets` hook in pre-commit prevents accidental credential check-ins.

---

## Preferred Disclosure Language

Please submit all reports in **English** to ensure the fastest possible triage and response.

---

*This policy follows coordinated disclosure best practices and OpenSSF Gold standards. Last reviewed: 2026-10.*
