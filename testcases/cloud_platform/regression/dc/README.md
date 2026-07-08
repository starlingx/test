# DC Orchestrator Test Cases

## Release Version Semantics

The `N` and `N-1` in test case names refer to **different things** depending on the operation:

### sw-deploy-strategy

- `N` or `N-1` refers to the **target release passed to the CLI** (`--release-id`)
- The subcloud picker does **not** filter by load — any online subcloud is eligible
- The operation outcome (minor vs major upgrade) depends on what the subcloud is currently running:
  - Subcloud on N + sw-deploy N → minor patch (e.g. 26.03.0 → 26.03.200)
  - Subcloud on N-1 + sw-deploy N → major upgrade (e.g. 25.09 → 26.03)
- Release resolution:
  - N release: highest **deployed** version matching N load (e.g. `WRCP-26.03.200`)
  - N-1 release: highest **unavailable** version matching N-1 load (e.g. `WRCP-25.09.300`)

### prestage-strategy

- `N` or `N-1` refers to the **load version passed via --release** (e.g. `25.09`, `26.03`)
- The subcloud picker does **not** filter by load — any online subcloud is eligible
- The `--for-sw-deploy` vs for-install distinction is a separate axis
- The operation outcome depends on what the subcloud is currently running:
  - Subcloud on N + prestage N → prestages the current release packages
  - Subcloud on N-1 + prestage N → prestages the major release packages for future upgrade
  - Subcloud on N + prestage N-1 → prestages the previous release (requires N-1 ISO on SC)
- The current subcloud state (its load) defines the real scenario being exercised — the test case itself is not limited to a specific subcloud version

### kube-rootca-update-strategy

- Fully **version-agnostic** — no release or load version is involved
- The `N` or `N-1` in the test name refers to the subcloud's current software version
- The subcloud picker filters by `load` to ensure we target subclouds on the expected version
- The strategy itself only takes `--expiry-date` and `--subject` — no version argument

### kube-upgrade-strategy

- The `N` or `N-1` in the test name refers to the subcloud's current software version
- The subcloud picker filters by `load` to target subclouds on the expected version
- If `--to-version` is not specified, dcmanager upgrades to the active K8s version from the system controller
- TODO: For N-2 release subclouds, we may need to specify an intermediate K8s version — this requires refactoring

## Software List Reference

```
software list
+----------------+------+-------------+
| Release        | RR   |    State    |
+----------------+------+-------------+
| WRCP-25.09.200 | True | unavailable |
| WRCP-25.09.300 | True | unavailable |
| WRCP-26.03.100 | True |  deployed   |
| WRCP-26.03.200 | True |  deployed   |
+----------------+------+-------------+
```

- **deployed**: currently active on the system controller
- **unavailable**: available for deployment to subclouds (typically N-1 releases)

For sw-deploy target resolution:
- Target N → `max(deployed releases matching N load)` → `WRCP-26.03.200`
- Target N-1 → `max(unavailable releases matching N-1 load)` → `WRCP-25.09.300`

For prestage release resolution:
- Uses the load identifier directly (e.g. `25.09`, `26.03`) for both `--for-sw-deploy` and for-install
