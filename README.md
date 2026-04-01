# Zeta IMA — AI Marketing Agency

A full-stack autonomous marketing agency built on FastAPI, LangGraph, Next.js, and Microsoft Teams. Multi-agent workflows generate, review, and publish marketing content with human-in-the-loop approval, brand voice consistency, and learning from every interaction.

## Features

| Category | What it does |
|---|---|
| **Multi-Agent Workflows** | Copy, review, research, approval, design, Jira, Confluence agents chained via LangGraph |
| **Brand Memory** | Qdrant-backed semantic search over approved outputs — every draft is informed by brand voice |
| **Agency Brain** | Shared knowledge base with conflict resolution (latest-wins, role-weight, manual review) |
| **Skills & Prompts** | 16 built-in skills with 50+ prompts, plus user-created codable skills in a RestrictedPython sandbox |
| **Learning System** | Tracks LLM outcomes; auto-selects the best-performing LLM per skill from historical data |
| **Scheduling** | Cron-based recurring workflow triggers (e.g., weekly LinkedIn posts) |
| **A/B Testing** | Create variant experiments, run them with different LLMs/prompts, score and pick winners |
| **Cost & Rate Limiting** | Per-user daily/monthly LLM spend tracking with Redis sliding windows |
| **Team Collaboration** | Teams with roles (admin, manager, strategist, copywriter, designer, member) |
| **Analytics** | LLM performance, pipeline bottlenecks, quality trends, skill leaderboard, campaign efficiency |
| **Orchestrator** | Intent-based task routing → automatic pipeline selection → workflow creation |
| **Document Ingestion** | Extract → chunk (300 tokens) → embed → Qdrant; supports PDF, DOCX, URLs, Confluence, Teams chat |
| **Notifications** | Real-time WebSocket push + notification bell UI |
| **Escalation Engine** | Auto-detects stuck workflow stages (4h threshold) and creates Jira tickets |
| **Audit Trail** | Compliance-ready logging of every action, approval, and integration call |
| **Multi-LLM** | OpenAI, Claude, Gemini with automatic fallback chains |
| **Teams Bot** | Microsoft Teams integration with SSO, Adaptive Cards, and proactive messaging |

## Quick Start

### 1. Start dependencies

```bash
docker compose up -d
```

This starts Redis (sessions), Qdrant (brand memory), and PostgreSQL (campaigns).

### 2. Install Python dependencies

```bash
cd zeta_ima
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp zeta_ima/.env.template zeta_ima/.env
# Edit .env and fill in OPENAI_API_KEY + Teams bot credentials
```

### 4. Seed brand memory (required for 80/20 learned context)

Copy your past approved copy into JSONL format (see `brand_seeds/approved_copy.jsonl.example`):

```bash
cp brand_seeds/approved_copy.jsonl.example brand_seeds/approved_copy.jsonl
# Edit the file with your real approved copy

python -m scripts.seed_brand_memory --input brand_seeds/approved_copy.jsonl
```

### 5. Start the server

```bash
uvicorn zeta_ima.api.app:app --reload --port 8000
```

### 6. Test without Teams (smoke test)

```bash
python -c "
import asyncio
from zeta_ima.agents.graph import graph
from zeta_ima.memory.session import make_thread_config

async def test():
    config = make_thread_config('test-session-001')
    result = await graph.ainvoke(
        {
            'messages': [],
            'user_id': 'test-user',
            'user_teams_id': 'test-user',
            'current_brief': 'Write a LinkedIn post about our Series A funding round',
            'stage': 'drafting',
            'iteration_count': 0,
            'drafts': [],
            'current_draft': {},
            'review_result': {},
            'brand_examples': [],
            'active_campaign_id': None,
            'approval_decision': None,
            'approval_comment': None,
        },
        config=config
    )
    print('Stage:', result['stage'])
    print('Draft:', result['current_draft']['text'])
    print('Review passed:', result['review_result']['passed'])

asyncio.run(test())
"
```

Then simulate approval:

```bash
python -c "
import asyncio
from langgraph.types import Command
from zeta_ima.agents.graph import graph
from zeta_ima.memory.session import make_thread_config

async def approve():
    config = make_thread_config('test-session-001')
    result = await graph.ainvoke(
        Command(resume={'decision': 'approve', 'comment': ''}),
        config=config
    )
    print('Final stage:', result['stage'])

asyncio.run(approve())
"
```

---

## Teams Bot Setup (Azure Bot Service Registration)

1. Go to [Azure Portal](https://portal.azure.com) → Create Resource → **Azure Bot**
2. Bot handle: `zeta-marketing-bot`
3. Pricing tier: **F0** (free) for dev
4. App type: **Multi-tenant**
5. After creation → **Configuration** → copy **Microsoft App ID**
6. Click **Manage Password** → New client secret → copy value
7. Paste both into `.env` as `MICROSOFT_APP_ID` and `MICROSOFT_APP_PASSWORD`
8. Set **Messaging endpoint**: `https://<your-domain>/api/messages`
   - For local dev: use [ngrok](https://ngrok.com) — `ngrok http 8000` → copy the HTTPS URL
9. Go to **Channels** → Add **Microsoft Teams** channel → Save

---

## Architecture

```
User (Teams / Web UI)
    │
    ▼
FastAPI (14+ routers)  ──────────────────────  Next.js Frontend
    │                                                │
    ├── Bot Framework (Teams webhook)                ├── Chat, Workflows, Skills
    ├── WebSocket (real-time updates)                ├── Dashboard, Analytics
    ├── Orchestrator (intent → pipeline → workflow)  ├── Brain, Programs, Settings
    │                                                └── Ingest, Experiments, Teams
    ▼
LangGraph StateGraph
    ├── copy_node       GPT-4o + Qdrant brand context
    ├── review_node     GPT-4o-mini quality gate
    ├── research_node   Knowledge base retrieval
    ├── approval_node   interrupt() — human gate
    ├── canva_node      Gemini image generation
    ├── jira_node       Jira integration
    ├── confluence_node Confluence publishing
    └── memory_node     Persist → Qdrant + PostgreSQL
    │
    ├── Redis           Session state (48h TTL), rate limit counters
    ├── Qdrant          brand_voice, knowledge_base, learning_memory,
    │                   directional_memory, agency_brain
    └── PostgreSQL      workflows, campaigns, schedules, experiments,
                        teams, llm_usage, audit_log, brain_contributions
```

## File Structure

```
zeta_ima/
├── agents/                   Multi-agent system
│   ├── graph.py              LangGraph StateGraph (8 nodes)
│   ├── llm_router.py         Multi-LLM dispatcher with fallback + cost tracking
│   ├── cost_tracker.py       Per-call cost tracking + Redis rate limits
│   ├── pool.py               Agent executor (skill + prompt + LLM)
│   ├── router.py             Intent classifier
│   ├── state.py              AgentState TypedDict (16 fields)
│   └── nodes/                copy, review, research, approval, canva, jira, confluence, memory
├── memory/
│   ├── brain.py              Agency Brain — shared knowledge with conflict resolution
│   ├── brand.py              Qdrant brand voice search
│   ├── campaign.py           Campaign + approved outputs (PostgreSQL)
│   ├── learning.py           Outcome tracking + best-LLM selection
│   ├── distiller.py          Conversation → persistent knowledge extraction
│   ├── audit.py              Compliance audit trail
│   └── session.py            Redis checkpointer + shared DB helpers
├── analytics/                LLM perf, bottlenecks, quality trends, campaign ROI
├── experiments/              A/B testing engine (create, run, score, conclude)
├── teams_collab/             Team management with roles
├── orchestrator/
│   ├── scheduler.py          Cron-based recurring workflow triggers
│   ├── dispatcher.py         Background task dispatch loop
│   ├── queue.py              PostgreSQL + Redis priority queue
│   └── router.py             Intent → pipeline routing
├── workflows/
│   ├── engine.py             Stage-by-stage executor
│   ├── escalation.py         Stuck detection → Jira escalation
│   ├── templates.py          8 built-in workflow templates
│   └── models.py             Workflow + stage DB models
├── skills/                   16 skills, 50+ prompts, user codable skills
├── ingest/                   PDF, DOCX, URL, Confluence, Teams chat → Qdrant
├── integrations/             Buffer, Canva, Confluence, DALL-E, Gemini, GitHub,
│                             Jira, LinkedIn, Mailchimp, SEMrush, SendGrid, Vault
├── api/
│   ├── app.py                FastAPI factory (20+ routers)
│   ├── auth.py               Teams SSO + role enrichment
│   └── routes/               analytics, brain, campaigns, chat, costs, dashboard,
│                             experiments, health, ingest, notifications, programs,
│                             schedules, settings, skills, tasks, teams_collab,
│                             user_skills, workflows, workflow_ws
├── bot/                      Teams bot (Adaptive Cards, proactive messaging)
├── notify/                   Graph API notifications + WebSocket push
├── prompts/                  Agent system prompts (markdown)
└── config.py                 Pydantic settings (50+ env vars)

frontend/                     Next.js app
├── app/                      Pages: chat, workflows, skills, dashboard, analytics,
│                             brain, programs, settings, ingest
├── components/               Sidebar, PreviewPanel, AuditTimeline, NotificationBell
└── lib/api.ts                API client

scripts/                      Brand memory seeding
docker-compose.yml            Redis + Qdrant + PostgreSQL
```

## API Endpoints

| Group | Endpoints |
|---|---|
| **Chat** | WebSocket `/chat` — real-time agent conversations |
| **Workflows** | CRUD + advance + approve/reject + retry |
| **Skills** | List built-in skills, CRUD user-created skills |
| **Brain** | Query, contribute, batch contribute, conflicts, compact, stats |
| **Campaigns** | CRUD + active campaign management |
| **Analytics** | Summary, LLM performance, bottlenecks, quality trends, skill leaderboard, campaign ROI |
| **Schedules** | CRUD for cron-based recurring workflows |
| **Experiments** | A/B test create, run, score, conclude |
| **Costs** | Usage report, daily breakdown, rate limit status |
| **Teams** | Team CRUD, member management, role assignment |
| **Ingest** | File upload, URL scrape, Confluence sync, Teams chat import |
| **Dashboard** | KPI summary, activity feed, stuck workflows |
| **Programs** | Multi-workflow program management |
| **Notifications** | WebSocket push + notification history |
| **Audit** | Compliance audit log |
| **Tasks** | Orchestrator task queue |
| **Health** | Redis, Qdrant, PostgreSQL connectivity checks |

Full API docs at `http://localhost:8000/docs` (Swagger UI).

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, LangGraph, SQLAlchemy (async), asyncpg
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **LLMs**: OpenAI GPT-4o/4o-mini, Anthropic Claude, Google Gemini (fallback chains)
- **Vector DB**: Qdrant (5 collections)
- **Database**: PostgreSQL (12+ tables)
- **Cache**: Redis (sessions, rate limits, notifications)
- **Integrations**: Teams Bot Framework, Jira, Confluence, Buffer, Canva, LinkedIn, Mailchimp, SendGrid, SEMrush
- **Security**: Teams SSO JWT, Azure Key Vault, Fernet encryption, RestrictedPython sandbox

## License

MIT
