# Skill Dispatch

Before starting any task, check whether an available skill matches the user's request. If a skill matches, read its `SKILL.md` and follow the documented process step by step. Do not improvise a workflow when a skill already defines one.

## Trigger keywords -> skill mapping

| If the request mentions...                                              | Use skill            |
|-------------------------------------------------------------------------|----------------------|
| review PR, PR feedback, analyze PR, back-port to rocMLIR                | `pr-review`          |
| build, compile, test, lint, check build, run tests.sh                   | `build-test-workflow`|
| profile, benchmark perf, kernel bottleneck                              | `kernel-profiling`   |
| run benchmarks, perfRunner, performance comparison                      | `perfrunner-usage`   |
| tune, tuning, perfConfig, tuningRunner                                  | `tuningrunner-usage` |
| release branch, cherry-pick, release patch                              | `release-management` |
| bump Triton, update Triton submodule, sync with Triton, add/refresh triton-patch | `triton-bump` |
