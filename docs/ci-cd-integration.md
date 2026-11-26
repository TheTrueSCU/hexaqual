# 🔄 CI/CD & GitHub Actions Integration

Hexaqual powers automated quality gates, tiered CI pipelines, and reproducible supply-chain-secure release workflows across GitHub Actions.

---

## 🚀 Composite GitHub Actions (`TheTrueSCU/hexaqual`)

### Turnkey Quality Gate Action (`action.yml`)
Use the composite action to install Python and `uv`, restore `~/.cache/pre-commit`, and run either `pre-commit` or `hexaqual sanity`:

```yaml
jobs:
  quality-gate:
    name: Pre-Commit Quality Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
      - uses: TheTrueSCU/hexaqual@6117ce25b1d39768f22396a55d13103abee88926 # v0.12.1
        with:
          mode: pre-commit          # 'pre-commit', 'sanity', or 'setup'
          python-version: "3.13"
          uv-version: "latest"
          sync-args: "--all-extras --dev"
          sanity-args: "-a --skip-tests"
          cache-pre-commit: "true"
          skip-hooks: "hexaqual-agents"
```

### LPT Mutation Matrix Planner (`.github/actions/mutate-plan/action.yml`)
Plans AST-weighted, capacity-capped Longest-Processing-Time-first (LPT) shards for parallel `pytest-gremlins` / `mutmut` matrix jobs via `hexaqual mutate plan`:

- **Inputs**: `mode` (`affected`, `all`, `slices`, or `changed-slices`; default `affected`), `base-ref` (`""`), `packages-root` (`"packages"`), `root` (`"src"`), `slices` (`"12"`), `max-weight` (`"450"`).
- **Outputs**: `matrix` (JSON payload for `strategy.matrix`) and `has_affected` (`'true'` / `'false'`).

---

## 🏗️ Tiered CI Pipeline Architecture

To minimize CI cycle time while maximizing rigor, Hexaqual organizes GitHub Actions workflows into four sequential stages:

```mermaid
graph TD
    PR[Pull Request Opened / Updated] --> S1[Stage 1: Pre-Commit Quality Gate\nStatic Checks, Ty, Complexipy, Ruff]
    S1 --> S2[Stage 2: Unit & Integration Tests\nPytest with dynamic xdist & coverage.xml]
    S2 --> S3{Event == pull_request?}
    S3 -- Yes --> S4[Stage 3: Property-Based Fuzzing\nHypothesis state machine fuzzing]
    S3 -- No (push to main) --> S5[Stage 4: Unified CI Success Gate]
    S4 --> S5
    S5 --> MERGE[Branch Protection Passed\nAuto-Merge Allowed]
```

### Stage 1: Fast Quality Gate (Pre-Commit)
Fails fast in under 15 seconds if any code style, typing, cognitive complexity, or structural parity violation exists:

```yaml
jobs:
  quality-gate:
    name: Pre-Commit Quality Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@1db35dd8eee11c5894872e0b383ae6c406cf738d # v10.4.0
        with:
          enable-cache: true
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.13"
      - run: uv sync --all-extras --dev
      - run: uv run pre-commit run --all-files
```

### Stage 2: Unit & Integration Tests with Coverage
Executes pytest with automated worker scaling and generates JUnit and XML coverage reports:

```yaml
  test-suite:
    name: Unit & Integration Tests
    needs: [quality-gate]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@1db35dd8eee11c5894872e0b383ae6c406cf738d # v10.4.0
        with:
          enable-cache: true
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.13"
      - run: uv sync --all-extras --dev
      - run: uv run hexaqual test run -U --cov=src --cov-report=xml --junitxml=junit.xml
      - uses: codecov/codecov-action@303a32d7a59b442fa8d48b6a1cc6825c09c847a5 # v7
        with:
          files: coverage.xml
          fail_ci_if_error: false
```

### Stage 3: Property-Based State Machine Fuzzing
Executes generative adversarial property tests on PR branches to catch edge cases that unit tests miss:

```yaml
  hypothesis-fuzzing:
    name: Property-Based State Machine Fuzzing
    needs: [test-suite]
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@1db35dd8eee11c5894872e0b383ae6c406cf738d # v10.4.0
        with:
          enable-cache: true
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.13"
      - run: uv sync --all-extras --dev
      - run: uv run hexaqual test run -P
```

### Stage 4: Unified Aggregator Status Check
Aggregates upstream results, ensuring conditional steps (like PR-only fuzzing) don't block branch protection when merging to `main`:

```yaml
  ci-success:
    name: CI Success (All Required Checks)
    needs:
      - quality-gate
      - test-suite
      - hypothesis-fuzzing
    if: ${{ always() }}
    runs-on: ubuntu-latest
    steps:
      - name: Verify All Upstream Jobs Succeeded or Skipped
        run: |
          results=(
            "${{ needs.quality-gate.result }}"
            "${{ needs.test-suite.result }}"
            "${{ needs.hypothesis-fuzzing.result }}"
          )
          for res in "${results[@]}"; do
            if [ "$res" = "failure" ] || [ "$res" = "cancelled" ]; then
              echo "::error::One or more upstream CI jobs failed."
              exit 1
            fi
          done
          echo "🎉 All required CI jobs completed successfully."
```

---

## 🔒 Reproducible Releases & OpenSSF Gold Security

Hexaqual includes built-in verification for byte-for-byte reproducible wheel builds and cryptographic supply-chain attestations:

```bash
# Verify byte-for-byte build reproducibility
uv run hexaqual release reproducible
```

In your `release.yml` workflow:

```yaml
  publish:
    name: Build & Publish to PyPI
    needs: [resolve-version, quality-gate, test-suite]
    runs-on: ubuntu-latest
    environment:
      name: pypi
      url: https://pypi.org/p/my-package
    permissions:
      id-token: write
      attestations: write
      contents: write
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7
        with:
          fetch-depth: 0
      - uses: astral-sh/setup-uv@1db35dd8eee11c5894872e0b383ae6c406cf738d # v10.4.0
        with:
          enable-cache: true
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.13"
      - run: uv sync --all-extras --dev
      - run: uv run hexaqual release reproducible
      - run: uv build --out-dir dist/
      - uses: actions/attest-build-provenance@4d101475d8b20a2381f78447822ac1eab6504dd8 # v4.2.2
        with:
          subject-path: 'dist/*'
      - uses: pypa/gh-action-pypi-publish@7245906fb61fa33a13554f9d5fb856fe61758086 # release/v1
        with:
          packages-dir: dist/
          skip-existing: true
          attestations: true
```
