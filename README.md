# Multi-Agent-Text-to-SQL-System-Spider-Benchmark-

# Multi-Agent Text-to-SQL System
### Spider Benchmark · Groq-powered · 4-Agent Pipeline

---

## Architecture

```
Natural Language Question
         │
         ▼
┌─────────────────┐
│ Agent 1         │  → Intent, Entities, Operations, Complexity
│ Query Planner   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent 2         │  → Tables, Columns, JOINs, Filters, Aggregations
│ Schema Reasoner │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent 3         │  → Raw SQL Query
│ SQL Generator   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Agent 4         │  → Validated + Corrected Final SQL
│ SQL Validator   │
└─────────────────┘
```

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure .env
```bash
cp .env .env.local   # optional backup
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=gsk_your_actual_key_here
```

Get your free key at: https://console.groq.com

### 3. Run

**Interactive mode:**
```bash
python main.py
```

**Single query:**
```bash
python main.py --schema concert_singer --query "How many singers are there?"
```

**Batch mode (all sample queries for a schema):**
```bash
python main.py --schema world_1 --batch
```

**Batch all schemas:**
```bash
python main.py --batch
```

---

## Available Schemas (Spider Benchmark)

| Schema | Description | Tables |
|--------|-------------|--------|
| `concert_singer` | Concerts, singers, stadiums | 4 |
| `employee_hire_evaluation` | HR & hiring | 4 |
| `world_1` | Countries, cities, languages | 3 |
| `student_transcripts` | Students, courses, grades | 8 |

---

## Project Structure

```
text2sql/
├── .env                        # API keys (DO NOT commit)
├── main.py                     # Entry point + pipeline orchestrator
├── requirements.txt
├── README.md
├── agents/
│   ├── query_planner.py        # Agent 1: NL → Query plan
│   ├── schema_reasoner.py      # Agent 2: Plan → Schema analysis
│   ├── sql_generator.py        # Agent 3: Analysis → SQL
│   └── sql_validator.py        # Agent 4: SQL → Validated SQL
├── schemas/
│   └── spider_schemas.py       # Spider benchmark schema definitions
├── utils/
│   └── groq_client.py          # Groq API wrapper
└── outputs/                    # Auto-created, stores JSON results
```

---

## Groq Models

Set `GROQ_MODEL` in `.env`:

| Model | Speed | Quality |
|-------|-------|---------|
| `llama3-70b-8192` | Fast | Best (recommended) |
| `llama3-8b-8192` | Ultra-fast | Good |
| `mixtral-8x7b-32768` | Fast | Good, longer context |
| `gemma2-9b-it` | Fast | Good |

---

## Output

Each run saves a JSON file in `./outputs/`:
```json
{
  "question": "How many singers are there?",
  "schema": "concert_singer",
  "final_sql": "SELECT count(*) FROM singer",
  "verdict": "APPROVED",
  "score": "7/7",
  "elapsed": 3.2,
  "agents": { ... }
}
```
