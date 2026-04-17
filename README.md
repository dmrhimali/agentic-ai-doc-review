# Agentic AI Document Review

Domain-agnostic agentic AI system for document review. An orchestrator agent breaks jobs into steps, delegates to specialized worker agents, and runs quality-check loops before persisting results. Two workers ship out-of-the-box:

- **Relevancy review** (`RelevancyWorker`) — classify each document as RELEVANT or NOT_RELEVANT against user-defined criteria, with matched criteria + explanation.
- **Entity extraction** (`EntityExtractionWorker`) — pull structured entities (people, organizations, dates, amounts, clauses, etc.) with context snippets.

All workers return confidence scores, token usage, and automatically escalate to stronger models when confidence is low. Additional job types plug into the `JobTypeRegistry` without touching the orchestrator. Works on any text corpus (research paper screening, compliance review, support-ticket triage, contract review, etc.).

> **Note:** This project was developed in collaboration with [Claude](https://www.anthropic.com/claude) (Anthropic's AI assistant), integrated into the development workflow via Claude Code.

## Architecture

```
API Request
    │
    ▼
┌──────────────┐
│ Orchestrator  │  Plans, delegates, aggregates
└──────┬───────┘
       │ looks up job_type in Registry
       ▼
┌──────────────┐
│   Worker      │  RelevancyWorker | EntityExtractionWorker | ...
│   Agent       │──────► Azure AI Foundry / OpenAI
└──────┬───────┘
       │ confidence < threshold?
       │ yes → escalate to fallback model
       ▼
┌──────────────┐
│ Quality Check │  Stronger model reviews the result
└──────────────┘
       │
       ▼
   MySQL (results)
```

**Key patterns:** job type registry for pluggable workers, protocol-based worker interface, two-pass LLM review with model escalation, versioned prompts stored in DB, structured output via JSON schema, token tracking for cost visibility.

## Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Docker (for MySQL)
- Azure AI Foundry or OpenAI API key

### Install and Run

```bash
# 1. Start MySQL
docker-compose up -d

# 2. Install dependencies
uv sync

# 3. Configure environment
cp .env.example .env
# Edit .env — set your provider and API keys

# 4. Seed prompt templates into database
uv run python scripts/seed_prompts.py

# 5. Start the API server
uv run uvicorn ediscovery.main:app --reload
```

Server runs at `http://localhost:8000`. API docs at `http://localhost:8000/docs`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `azure` | LLM provider: `azure` or `openai` |
| `AZURE_API_KEY` | (required for azure) | Azure AI Foundry API key |
| `AZURE_ENDPOINT` | (required for azure) | Azure endpoint URL |
| `AZURE_API_VERSION` | `2024-12-01-preview` | Azure API version |
| `OPENAI_API_KEY` | (required for openai) | OpenAI API key |
| `RELEVANCY_REVIEW_MODEL` | `gpt-5-nano` | Relevancy primary model (cheap, runs first) |
| `RELEVANCY_REVIEW_FALLBACK_MODEL` | `gpt-5-mini` | Relevancy fallback model (escalate if low confidence) |
| `RELEVANCY_REVIEW_CONFIDENCE_THRESHOLD` | `0.7` | Relevancy — below this → escalate to fallback |
| `ENTITY_EXTRACTION_MODEL` | `gpt-5-nano` | Entity-extraction primary model |
| `ENTITY_EXTRACTION_FALLBACK_MODEL` | `gpt-5-mini` | Entity-extraction fallback model |
| `ENTITY_EXTRACTION_CONFIDENCE_THRESHOLD` | `0.7` | Entity-extraction — below this → escalate to fallback |
| `DATABASE_URL` | `mysql+pymysql://docreview:docreview@localhost:3306/docreview` | MySQL connection |
| `UPLOAD_DIR` | `./uploads` | File upload storage |
| `LOG_LEVEL` | `INFO` | Logging level |

**Note:** When using Azure AI Foundry, set model values to your **Azure deployment names** (e.g. `my-gpt5-nano-deployment`).

Retries handle transient API errors (429, 500, timeouts) using the same model — they do not escalate.

## API Endpoints

### Jobs

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/jobs` | Create a job |
| `GET` | `/api/v1/jobs` | List all jobs |
| `GET` | `/api/v1/jobs/{job_id}` | Get job status |
| `POST` | `/api/v1/jobs/{job_id}/documents` | Upload documents (multipart) |
| `POST` | `/api/v1/jobs/{job_id}/run` | Trigger job execution |
| `POST` | `/api/v1/jobs/run-directory` | Create + run from local directory |

### Results and Prompts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/jobs/{job_id}/results` | Get all results for a job |
| `GET` | `/api/v1/prompts/{job_type}` | Get active prompt templates |
| `PUT` | `/api/v1/prompts/{prompt_id}` | Update a prompt template |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |

## Test Data

Generate test documents **before** running any jobs.

### Generate sample documents

Generate 10 sample research-paper abstracts (systematic-review screening scenario — "effective psychological interventions for adult PTSD") into a `test-docs-ptsd/` folder:

```bash
uv run python scripts/generate_test_docs.py ./test-docs-ptsd
```

This creates `./test-docs-ptsd/` with 5 relevant abstracts (RCTs and meta-analyses of CBT, EMDR, prolonged exposure, trauma-focused CBT, and group CPT for PTSD) and 5 not-relevant abstracts (type 2 diabetes, pediatric asthma, survey methodology, cold-chain logistics, a mental-health funding editorial).

## Usage

### Option A: Local directory (simplest)

Point at a folder of `.pdf`, `.docx`, or `.txt` files. The `criteria` shape depends on `job_type` — examples for both job types below.

**Relevancy review** — classify each document as RELEVANT / NOT_RELEVANT:

```powershell
@'
{
  "job_type": "relevancy_review",
  "criteria": {
    "relevant": ["psychological intervention for PTSD in adults", "randomized trial or meta-analysis of PTSD therapy", "trauma-focused CBT, EMDR, prolonged exposure, or CPT"],
    "not_relevant": ["studies of other conditions (diabetes, asthma, anxiety without PTSD focus)", "methodology or simulation papers", "editorials, opinion pieces, or policy commentary"]
  },
  "document_directory": "./test-docs-ptsd"
}
'@ | Out-File -Encoding utf8 body.json

# Capture the response so we can pull the job ID for later
$response = curl.exe -X POST "http://localhost:8000/api/v1/jobs/run-directory" `
  -H "Content-Type: application/json" `
  -d "@body.json"
$jobId = ($response | ConvertFrom-Json).id
Write-Host "Job ID: $jobId"
```

**Entity extraction** — pull structured entities (people, orgs, dates, amounts, clauses, etc.):

```powershell
@'
{
  "job_type": "entity_extraction",
  "criteria": {
    "entity_types": ["person", "organization", "date", "amount"]
  },
  "document_directory": "./test-docs-ptsd"
}
'@ | Out-File -Encoding utf8 body.json

$response = curl.exe -X POST "http://localhost:8000/api/v1/jobs/run-directory" `
  -H "Content-Type: application/json" `
  -d "@body.json"
$jobId = ($response | ConvertFrom-Json).id
Write-Host "Job ID: $jobId"
```

`entity_types` can be empty (`[]`) to use the defaults: `person`, `organization`, `location`, `date`, `amount`, `reference`, `clause`.

**Example output — entity extraction** (real response, 2 of 6 documents shown):

```json
{
  "job_id": "27cae000-c73e-4767-acd1-ab6974e68150",
  "job_type": "entity_extraction",
  "total": 6,
  "results": [
    {
      "id": "0a5c01d3-08a2-4c79-a405-a9b0434a7d35",
      "job_id": "27cae000-c73e-4767-acd1-ab6974e68150",
      "document_id": "0184022f-2271-419a-b6d9-d958016a2daa",
      "job_type": "entity_extraction",
      "result": {
        "entities": [
          { "type": "organization", "value": "Veterans Affairs medical centers", "context": "Pragmatic trial at four Veterans Affairs medical centers." },
          { "type": "amount", "value": "4", "context": "Pragmatic trial at four Veterans Affairs medical centers." },
          { "type": "amount", "value": "183", "context": "Veterans (N=183) with chronic combat-related PTSD were randomized..." },
          { "type": "amount", "value": "12 sessions", "context": "randomized to 12 sessions of EMDR or to present-centered therapy." },
          { "type": "amount", "value": "-9.4 points", "context": "mean difference -9.4 points, 95% CI -13.1 to -5.7" },
          { "type": "amount", "value": "58%", "context": "achieved by 58% in the EMDR arm" },
          { "type": "amount", "value": "34%", "context": "versus 34% in the control arm" }
        ],
        "entity_counts": { "organization": 1, "amount": 8 }
      },
      "confidence": 0.9,
      "explanation": "Added missing amount entities: number of centers, sample size, session count, effect size, CI, and outcome percentages. Organization entity was correct.",
      "model_used": "gpt-5-nano",
      "prompt_tokens": 579,
      "completion_tokens": 1415,
      "created_at": "2026-04-17T17:26:49"
    },
    {
      "id": "82969623-d8a8-437e-bdc9-8fdf07c6df18",
      "job_id": "27cae000-c73e-4767-acd1-ab6974e68150",
      "document_id": "0aee7243-2868-4948-948f-2458a73715f2",
      "job_type": "entity_extraction",
      "result": {
        "entities": [
          { "type": "organization", "value": "OECD", "context": "We review trends in mental health spending across OECD countries" },
          { "type": "date", "value": "past decade", "context": "across OECD countries over the past decade" }
        ],
        "entity_counts": { "organization": 1, "date": 1 }
      },
      "confidence": 0.92,
      "explanation": "Identified one organization (OECD) and one date-like expression (past decade); no person or monetary amount entities detected.",
      "model_used": "gpt-5-nano",
      "prompt_tokens": 536,
      "completion_tokens": 2084,
      "created_at": "2026-04-17T17:29:18"
    }
  ]
}
```

**Observations from a real 6-document run:**

- The model correctly skips entity types not present in a document (the OECD editorial has no `amount` or `person` entries)
- It extracts entities even in documents outside the prompt's domain (diabetes cohort, pediatric asthma) because the criteria specified only entity types, not subject matter
- Confidence calibration is reasonable: verbose / dense documents tend to score lower (~0.55–0.80) than sparse ones (~0.9+), reflecting extraction uncertainty
- `context` snippets make every entity trivially verifiable against the source text

> **Notes:**
> - Use `curl.exe` explicitly — the bare `curl` in PowerShell is an alias for `Invoke-WebRequest`.
> - Write the JSON to `body.json` then reference it with `-d "@body.json"`. This avoids a Windows PowerShell bug that strips double quotes when passing strings to native `.exe` programs.

### Option B: Step-by-step via API

```powershell
# 1. Create job — capture response and extract job ID
@'
{
  "job_type": "relevancy_review",
  "criteria": {
    "relevant": ["psychological intervention for PTSD in adults", "randomized trial of PTSD therapy"],
    "not_relevant": ["studies of unrelated conditions", "editorials or opinion pieces"]
  }
}
'@ | Out-File -Encoding utf8 body.json

$response = curl.exe -X POST "http://localhost:8000/api/v1/jobs" `
  -H "Content-Type: application/json" `
  -d "@body.json"
$jobId = ($response | ConvertFrom-Json).id
# $jobId now holds something like: abc-123-...

# 2. Upload documents
curl.exe -X POST "http://localhost:8000/api/v1/jobs/$jobId/documents" `
  -F "files=@./test-docs-ptsd/cbt_ptsd_rct.txt" `
  -F "files=@./test-docs-ptsd/emdr_veterans_study.txt" `
  -F "files=@./test-docs-ptsd/prolonged_exposure_meta.txt"

# 3. Run the job
curl.exe -X POST "http://localhost:8000/api/v1/jobs/$jobId/run"
```

### Fetch results (after Option A or Option B)

If you ran the Option A or Option B block above in the same shell, `$jobId` is already set — just run:

```powershell
curl.exe "http://localhost:8000/api/v1/jobs/$jobId/results" |
  ConvertFrom-Json |
  ConvertTo-Json -Depth 10
```

**Lost `$jobId` (new shell, etc.)?** Find the UUID in the original response (the `"id": "..."` field at the top) and set it manually:

```powershell
$jobId = "PASTE-UUID-HERE"

curl.exe "http://localhost:8000/api/v1/jobs/$jobId/results" |
  ConvertFrom-Json |
  ConvertTo-Json -Depth 10
```

**Forgot to capture it entirely?** List recent jobs and grab the most recent `id`:

```powershell
curl.exe "http://localhost:8000/api/v1/jobs" | ConvertFrom-Json | Select-Object -First 1
```

### Result Format

The `/results` endpoint returns a wrapper object with per-document classifications in the `results` array. Each element contains the AI's tag, matched criteria, plain-text explanation, confidence, and token usage.

**Example response** (abbreviated — 2 of 10 documents shown):

```json
{
  "job_id": "57366bf4-073c-4d12-ac0c-2d0873dba468",
  "job_type": "relevancy_review",
  "total": 10,
  "results": [
    {
      "id": "c1f23924-3a89-4f4a-a8c5-d91f1725c644",
      "job_id": "57366bf4-073c-4d12-ac0c-2d0873dba468",
      "document_id": "17653b3d-ed51-46b7-9d47-bcb4d059848d",
      "job_type": "relevancy_review",
      "result": {
        "is_relevant": true,
        "tag": "RELEVANT",
        "matched_criteria": [
          "psychological intervention for PTSD in adults",
          "randomized trial",
          "trauma-focused CBT"
        ]
      },
      "confidence": 0.92,
      "explanation": "The document reports a randomized controlled trial evaluating trauma-focused cognitive behavioral therapy (CBT) for PTSD in adults. It directly examines a psychological intervention for PTSD, uses a randomized design, and evaluates a trauma-focused therapy explicitly (CBT), fulfilling all relevant criteria.",
      "model_used": "gpt-5-nano",
      "prompt_tokens": 580,
      "completion_tokens": 625,
      "created_at": "2026-04-16T20:31:04"
    },
    {
      "id": "c6f3a620-d5e0-4ddf-922b-0a17b0365f66",
      "job_id": "57366bf4-073c-4d12-ac0c-2d0873dba468",
      "document_id": "ae348968-dfbe-453b-9c70-d92b7e57b0e5",
      "job_type": "relevancy_review",
      "result": {
        "is_relevant": false,
        "tag": "NOT_RELEVANT",
        "matched_criteria": []
      },
      "confidence": 0.92,
      "explanation": "The document discusses predictive maintenance in cold-chain logistics using reinforcement learning. It has no focus on PTSD, psychological interventions, trauma-focused therapies, or randomized trials/meta-analyses of PTSD treatment.",
      "model_used": "gpt-5-nano",
      "prompt_tokens": 516,
      "completion_tokens": 403,
      "created_at": "2026-04-16T20:32:33"
    }
  ]
}
```

**Sample classification summary** (10-doc PTSD test run):

| Document | Tag | Confidence |
|----------|-----|-----------:|
| `cbt_ptsd_rct.txt` | RELEVANT | 0.92 |
| `emdr_veterans_study.txt` | RELEVANT | 0.88 |
| `prolonged_exposure_meta.txt` | RELEVANT | 0.92 |
| `tf_cbt_refugees.txt` | RELEVANT | 0.92 |
| `group_cpt_sexual_assault.txt` | RELEVANT | 0.86 |
| `type2_diabetes_metformin.txt` | NOT_RELEVANT | 0.85 |
| `childhood_asthma_inhaler.txt` | NOT_RELEVANT | 0.88 |
| `survey_methodology_nonresponse.txt` | NOT_RELEVANT | 0.92 |
| `supply_chain_logistics.txt` | NOT_RELEVANT | 0.92 |
| `editorial_mental_health_funding.txt` | NOT_RELEVANT | 0.85 |

Against the expected ground truth (5 relevant + 5 not-relevant), `gpt-5-nano` classified all 10 documents correctly with confidence ≥ 0.85.

## Job Types

Workers are pluggable via the `JobTypeRegistry`. Two job types ship out-of-the-box:

| `job_type` | Purpose | Criteria shape |
|------------|---------|----------------|
| `relevancy_review` | Classify each document as RELEVANT or NOT_RELEVANT against user-defined criteria | `{ "relevant": [...], "not_relevant": [...] }` |
| `entity_extraction` | Pull structured entities (people, orgs, dates, amounts, clauses, etc.) from each document | `{ "entity_types": [...] }` (empty = all defaults) |

For concrete input/output examples of each, see **Option A** under Usage above. See **Adding a New Job Type** below for the scaffold recipe.

## Execution Flow

```
1. Job created (status: pending)
2. Documents registered (uploaded or scanned from directory)
3. Job triggered (status: running)
4. Orchestrator:
   a. Loads criteria + prompt templates from DB
   b. Resolves worker from registry with per-job-type ModelConfig
   c. For each document:
      ├─ Extract text from file (PDF/DOCX/TXT → plain text, cached in DB)
      ├─ Worker: call cheap model (e.g. gpt-5-nano) with structured output schema
      ├─ If confidence < threshold → escalate to fallback model (e.g. gpt-5-mini)
      ├─ Quality check: fallback model reviews the result
      │  ├─ Approved → keep original result
      │  └─ Rejected → use revised result
      └─ Save ReviewResult to DB
   d. Update progress counter after each document
5. Job completed (status: completed | completed_with_errors)
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `jobs` | Job metadata — type, status, criteria, progress, timestamps |
| `job_documents` | Documents in a job — filename, file path, cached extracted text, status |
| `review_results` | Per-document AI results — structured JSON, confidence, explanation, token usage |
| `prompt_templates` | Versioned prompt templates per job type — editable via API |

### Inspecting the Database

Connect to MySQL inside the Docker container:

```bash
docker exec -it docreview-mysql mysql -u docreview -pdocreview docreview
```

Useful queries:

```sql
-- List all tables
SHOW TABLES;

-- Check seeded prompts
SELECT id, job_type, name, version, is_active FROM prompt_templates;

-- View prompt text
SELECT id, job_type, name, version, content FROM prompt_templates;

-- View a specific prompt
SELECT content FROM prompt_templates WHERE job_type = 'relevancy_review' AND name = 'system_prompt';

-- List jobs and their status
SELECT id, job_type, status, total_documents, processed_documents, created_at FROM jobs;

-- View documents for a job
SELECT id, job_id, filename, status FROM job_documents WHERE job_id = '<job-id>';

-- View results with relevancy tags
SELECT r.id, d.filename, r.confidence, r.model_used,
       JSON_EXTRACT(r.result, '$.tag') AS tag,
       JSON_EXTRACT(r.result, '$.is_relevant') AS is_relevant
FROM review_results r
JOIN job_documents d ON r.document_id = d.id
WHERE r.job_id = '<job-id>';

-- Token usage summary for a job
SELECT model_used, COUNT(*) AS docs,
       SUM(prompt_tokens) AS total_prompt_tokens,
       SUM(completion_tokens) AS total_completion_tokens
FROM review_results
WHERE job_id = '<job-id>'
GROUP BY model_used;
```

## Adding a New Job Type

1. Add env var overrides to `Settings` and a `ModelConfig` entry in `_build_model_configs()` in `src/ediscovery/config.py`
2. Create `src/ediscovery/agents/<type>/worker.py`
3. Implement the `JobWorker` protocol (`process_document` + `quality_check`)
4. Decorate with `@JobTypeRegistry.register("your_type")`
5. Import the module in `main.py` to trigger registration
6. Add the job type to the schema regex in `src/ediscovery/schemas/job.py`
7. Add prompt templates via `seed_prompts.py` or the API

## Development

```bash
uv run ruff check src/                # Lint
uv run ruff format src/               # Format
uv run mypy src/                      # Type check
uv run pytest                         # Tests
uv run pytest --cov                   # Coverage
```
