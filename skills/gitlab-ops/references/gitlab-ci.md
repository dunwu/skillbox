# CI/CD Pipelines

Covers the full lifecycle of GitLab CI/CD pipeline operations.

## Decision tree

```
What CI/CD operation do you need?
├── Check the current pipeline status → glab ci status / glab ci view
├── Inspect a specific pipeline → glab ci get <id>
├── View job logs → glab ci trace
├── Retry a failed job → glab ci retry
├── Cancel a running pipeline → glab ci cancel
├── Manually trigger a pipeline → glab ci trigger
├── Manage scheduled pipelines → glab schedule
└── Author/modify .gitlab-ci.yml → see the authoring guidelines section
```

## Viewing pipelines

```bash
# Real-time status dashboard (interactive)
glab ci status

# Visual view (browser)
glab ci view

# View a specific pipeline
glab ci get --pipeline-id <id>
glab ci get --pipeline-id <id> --output json

# List pipelines
glab ci list
glab ci list --scope finished
glab ci list --scope running
glab ci list --ref main

# JSON output (for Agent parsing)
glab ci list --output json
```

## Job operations

```bash
# View a job log (live tail)
glab ci trace

# View a specific job log
glab ci trace <job-id>

# List all jobs of a pipeline (glab has no ci list --pipeline-id; use the REST API)
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/pipelines/<id>/jobs" | jq .

# View job details (via the REST API)
curl -s --header "PRIVATE-TOKEN: $TOKEN" \
  "$GITLAB_URL/api/v4/projects/$PROJECT_ID/jobs/<job-id>" | jq .
```

## Pipeline control

```bash
# Retry a failed job (interactive selection)
glab ci retry

# Retry a specific job
glab ci retry <job-id>
glab ci retry <job-name> --branch main

# Cancel a running pipeline
glab ci cancel pipeline <pipeline-id>

# Cancel a running job
glab ci cancel job <job-id>

# Trigger a manual job
glab ci trigger <job-name> --branch main

# Trigger via a pipeline trigger (requires a trigger token created in GitLab beforehand)
glab ci run-trig

# Delete a pipeline
glab ci delete <pipeline-id>
```

## Scheduled pipelines

```bash
# List schedules
glab schedule list
glab schedule list --output json

# Create a schedule
glab schedule create \
  --description "Daily build" \
  --ref main \
  --cron "0 2 * * *"

# With variables
glab schedule create \
  --ref main \
  --cron "0 6 * * 1" \
  --variable "DEPLOY_ENV:staging"

# Update
glab schedule update <schedule-id> --cron "0 3 * * *"

# Delete
glab schedule delete <schedule-id>
```

### Notes on schedule variables

- Variable keys are validated before creation; an empty key is rejected
- Make sure the `--variable <key>:<value>` format is correct before executing

## .gitlab-ci.yml authoring guidelines

### Minimal structure

```yaml
stages:
  - build
  - test
  - deploy

build-job:
  stage: build
  script:
    - echo "Building..."
    - mvn clean package -DskipTests

test-job:
  stage: test
  script:
    - mvn test

deploy-job:
  stage: deploy
  script:
    - echo "Deploying..."
  environment: production
  when: manual
  only:
    - main
```

### Common patterns

```yaml
# Cache dependencies
cache:
  key: "${CI_COMMIT_REF_SLUG}"
  paths:
    - .m2/repository/
    - node_modules/

# Template reuse (include)
include:
  - template: Security/SAST.gitlab-ci.yml
  - project: 'group/ci-templates'
    file: '/templates/maven.yml'

# Rule control (replaces only/except)
rules:
  - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
    changes:
      - src/**/*
  - if: '$CI_COMMIT_BRANCH == "main"'

# Manual trigger
deploy-prod:
  stage: deploy
  script: ./deploy.sh
  when: manual
  environment:
    name: production
    url: https://app.example.com

# Parallel matrix
test:
  parallel:
    matrix:
      - JAVA_VERSION: ['17', '21']
        DB: ['mysql', 'postgres']
```

### Predefined variables (commonly used)

| Variable | Meaning |
|------|------|
| `$CI_COMMIT_SHA` | Current commit SHA |
| `$CI_COMMIT_BRANCH` | Branch name (outside MRs) |
| `$CI_MERGE_REQUEST_IID` | MR IID |
| `$CI_PIPELINE_ID` | Pipeline ID |
| `$CI_JOB_NAME` | Current job name |
| `$CI_PROJECT_PATH` | Project path (group/project) |
| `$CI_REGISTRY` | Container registry address |
| `$CI_DEFAULT_BRANCH` | Default branch name |

## CI gate orchestration

Wire CI into MR merging: use stage ordering to block "pre-compliance checks" ahead of the build,
and together with the project-level `only_allow_merge_if_pipeline_succeeds`, achieve the effect of
"any failure → pipeline fails → MR cannot be merged".

### Standard stage order

```yaml
stages:
  - check      # Compliance checks: branch naming, docs/artifacts presence, config drift, etc. (seconds-level, should fail fast)
  - build      # Compile/package
  - test       # Unit/integration tests
  - deploy     # Deploy (usually manual or trunk-only)
```

`check` and `build` run sequentially by default: as long as `build` doesn't declare `needs: []`,
GitLab only releases `build` once every `check` job has succeeded. Any failing check job →
pipeline `failed` → the merge is blocked by the gate.

### Check job design conventions

| Convention | How to write | Why |
|------|------|------|
| Use lightweight images | `image: python:3.11-slim` / `alpine` | Checks usually take seconds; avoid pulling heavy maven/node images that slow down feedback |
| One job per check | split `check:branch` / `check:docs` | Clear failure localization; the UI shows at a glance which gate blocked the merge |
| Script can be rerun locally | the same `.py` / `.sh` works both in CI and locally | CI and local runs share the same source; scripts accept `--branch`/argv and fall back to `CI_*` environment variables by default |
| Fail with `exit 1` | the script returns non-zero; the GitLab job turns `failed` | Don't use `echo + return 0`, or the gate becomes decoration |
| Explicit fail on missing credentials | check for missing key variables like `GITLAB_TOKEN` → `exit 2` | Distinguish "logic failure vs configuration failure": exit 1 for the former, exit 2 for the latter |
| Use a Project Access Token for cross-project API calls | scope=`read_api` is enough; store it masked in project Variables | A personal PAT is over-privileged; a leaked project token has a smaller blast radius and can be revoked independently |

### rules control: triggering and fallback

```yaml
# Run only on MR events from feature/* branches (avoid running on every push to develop)
.check-default:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event" && $CI_MERGE_REQUEST_SOURCE_BRANCH_NAME =~ /^feature\//'

# Fallback job (closing the MR / DingTalk notification): runs only when a preceding job failed (place at the end of the stage)
notify_on_failure:
  stage: .post
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
      when: on_failure
  script:
    - python3 scripts/ci/notify_mr_failure.py

# Upload artifacts only on failure to save storage
build:
  artifacts:
    when: on_failure
    paths: ["**/target/checkstyle-result.xml"]
```

`when: on_failure` has stage-level semantics: the job is only created when a preceding job in the
same stage has failed. To trigger on "any stage failing", place the fallback job in the last stage
(or use the built-in `.post` stage).

### Integration with MR merge gates

The CI side only determines the pipeline status. **Truly "no merge on failure"** also requires the
project to enable `only_allow_merge_if_pipeline_succeeds`:

```bash
# One-time setup (see gitlab-server-config.md §Project merge settings for details)
glab api "projects/:id" -X PUT -H "Content-Type: application/json" --input - <<'EOF'
{"only_allow_merge_if_pipeline_succeeds": true, "only_allow_merge_if_all_discussions_are_resolved": true}
EOF
```

CI failure + the project switch = the MR merge button is greyed out. Missing either one degrades
the gate:
- CI failure only: the UI shows red ❌ but the author can still force the merge
- Project switch only: CI performs no real checks and the gate spins idle

### Troubleshooting (gates)

| Symptom | Cause | Fix |
|------|------|------|
| check job stays pending, never assigned | Runner concurrency saturated / image being pulled for the first time | Check runner status; cache the image or switch to a slim variant |
| retry job doesn't pick up new variables | GitLab project-level Variables are snapshotted at pipeline creation; retry doesn't refresh them | Push an empty commit to trigger a new pipeline |
| check succeeded but build never ran | The check used `allow_failure: true` (soft fail) | Change to `allow_failure: false` (the default) |
| `when: on_failure` not triggered | No preceding job in the same stage failed, or the job isn't in the last stage | Put the fallback job in `.post` or the final stage |
| pipeline `canceled` but the MR still shows blocked | The previous push canceled the old pipeline; the new one hasn't finished | Wait for head_pipeline to reach a final state |

## Troubleshooting

| Symptom | Cause | Fix |
|------|------|------|
| pipeline stuck | Waiting for a manually triggered job | `glab ci view` to find the manual job and trigger it |
| job failed but the log is empty | Runner issue | Check the Runner status; retry the job |
| "no matching job" | rules don't match | Check the rules conditions and variables |
| schedule doesn't run | Not enabled or Runner unavailable | `glab schedule list` to check the active state |
| cache miss | Key mismatch | Unify the cache key strategy |
| include template not found | Wrong path or insufficient permissions | Confirm the template path and token permissions |
