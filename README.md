# Zeta IMA — AI Marketing Agency

A full-stack autonomous marketing agency built on **FastAPI, LangGraph, Next.js, and Microsoft Teams**. Multi-agent workflows generate, review, and publish marketing content with human-in-the-loop approval, brand voice consistency, and learning from every interaction.

---

## Core Platform

- 🤖 **Multi-Agent Workflows** — Copy, review, research, approval, design, SEO, competitive intel, and product marketing agents chained via LangGraph
- 🎯 **Orchestrator & Ticket Routing** — Intent-based task routing → pipeline selection → automatic agent assignment. Tickets flow through a structured queue with priority, dependencies, and SLA tracking
- 🧠 **Agency Brain (Aggregated Memory)** — Shared knowledge base across all team members. Every input from every user feeds a combined brain with conflict resolution (latest-wins, role-weight, manual review)
- 🔄 **Agent-to-Agent Workflows** — A2A protocol with 8 message types (delegate, result, consult, inform, escalate, broadcast, vote_request, vote_response). Agents hand off work, consult each other, and escalate — emulating real agency flow (PM → Copy → Design → Review)
- 🪞 **Actor-Critic Reflection Loops** — Maker-checker system with recursive review. The creator agent passes work to a reviewer agent; feedback loops back through the system until quality gates are met
- 🛠️ **Codable Skills** — 16 built-in skills + user-created skills in a RestrictedPython sandbox. If one team member builds a visiting card skill, it's available to everyone
- 🔗 **LLM Integrations** — Azure OpenAI (GPT-4o/4o-mini), Anthropic Claude, Google Gemini, and Gemini image generation (Nano Banana 2) with automatic fallback chains

## Learning & Memory Moat

- 📚 **Dual-Track Learning Engine** — Directional learning (brand direction, strategy, positioning) + tactical learning (execution skills, techniques). Both tracks feed guidance into every future task
- 🏢 **Per-Team Learning Profiles** — Scoped per-team, not per-user. Aggregated preferences, score distributions, top feedback tags, and edit patterns build a team-specific guidance layer
- 💡 **Proactive Recognition ("You've Done This Before")** — Before every task, the system searches past briefs, campaign scores, and approved outputs. Surfaces similar work ranked by `similarity × score × recency` with Reuse / Modify / Start Fresh options
- 📝 **Structured Feedback Collection** — Star ratings (1-5) + multi-select feedback tags (10 categories) + free text on every approval/rejection. Patterns feed directly into learning
- 📊 **Campaign Score Ingestion** — Import real-world KPIs via Excel upload, manual entry, or API pull (Mailchimp, GA4, LinkedIn). Scores feed into recall ranking and prompt guidance
- 🧬 **Prompt Evolution Engine** — Versioned prompts with auto-evolution. Minor changes apply automatically; major changes queue for human approval. Triggers: repeated feedback tags, low approval rates, score drops
- 🗄️ **Conversation Archive** — Every completed session archived to blob storage with vector embeddings for semantic search. Full conversation history retrievable for context

## Infrastructure & Storage

- 🔀 **Azure-Ready Abstraction Layer** — Toggleable backends: Qdrant ↔ Azure AI Search (vectors), PostgreSQL ↔ Cosmos DB (documents), Local FS ↔ Azure Blob (files). Local dev with OSS tools, production on Azure
- 🗃️ **18+ Database Tables** — Workflows, campaigns, schedules, experiments, teams, audit logs, conversation archives, team profiles, feedback entries, campaign scores, prompt versions, evolution queue, and more
- 🔍 **5 Vector Collections** — brand_voice, knowledge_base, learning_memory, directional_memory, agency_brain

## Agent System

- 👥 **13 Agent Roles, 5 Departments** — Chief Marketing Officer, Creative Director, Senior Copywriter, SEO Specialist, Competitive Analyst, Product Marketer, and more — organized into Creative, Strategy, Intelligence, Production, and Design departments
- 🗣️ **Meeting Engine** — Multi-agent meetings with structured agendas, threaded discussion, voting, and consensus tracking before plan execution
- 📋 **14+ Graph Nodes** — recall → await_recall → meeting → await_plan_approval → copy/research/SEO/competitive intel → review → approval → canva/jira/confluence → memory

## Teams & Collaboration

- 💬 **Microsoft Teams Bot** — Adaptive Cards v1.5, SSO authentication, proactive messaging, approval/rejection flows, meeting stage routing
- 👨‍👩‍👧‍👦 **Team Roles** — Admin, manager, strategist, copywriter, designer, member — with scoped permissions
- 🔔 **Real-Time Notifications** — WebSocket push + Teams proactive messages + notification bell UI

## Content & Integrations

- 📄 **Document Ingestion** — PDF, DOCX, URLs, Confluence pages, Teams chat → extract → chunk (300 tokens) → embed → vector store. Progress tracking with granular stage updates
- 🎨 **Creative Tools** — Canva, DALL-E, Gemini image generation
- 📮 **Publishing** — Buffer, LinkedIn, Mailchimp, SendGrid
- 🔧 **DevOps** — Jira (task + escalation), Confluence (publishing), GitHub
- 🔑 **Security** — Teams SSO JWT, Azure Key Vault, Fernet encryption, RestrictedPython sandbox

## Analytics & Operations

- 📈 **Analytics Dashboard** — LLM performance, pipeline bottlenecks, quality trends, skill leaderboard, campaign ROI
- 💰 **Cost & Rate Limiting** — Per-user daily/monthly LLM spend tracking with Redis sliding windows
- 🧪 **A/B Testing** — Create variant experiments, run with different LLMs/prompts, score and pick winners
- ⏰ **Scheduling** — Cron-based recurring workflow triggers
- ⚠️ **Escalation Engine** — Auto-detects stuck stages (4h threshold), creates Jira tickets
- 📜 **Audit Trail** — Compliance-ready logging of every action, approval, and integration call

---

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
FastAPI (20+ routers)  ──────────────────────  Next.js Frontend
    │                                                │
    ├── Bot Framework (Teams webhook)                ├── Chat, Workflows, Skills
    ├── WebSocket (real-time updates)                ├── Dashboard, Analytics
    ├── Orchestrator (intent → pipeline → workflow)  ├── Brain, Programs, Settings
    │                                                └── Ingest, Experiments, Teams
    ▼
LangGraph StateGraph (14+ nodes)
    ├── recall_node          Search prior work, proactive suggestions
    ├── await_recall_node    interrupt() — user picks Reuse/Modify/Fresh
    ├── meeting_node         Multi-agent structured meeting
    ├── await_plan_approval  interrupt() — human reviews plan
    ├── copy_node            GPT-4o + brand context + evolved prompts
    ├── review_node          GPT-4o-mini quality gate (actor-critic)
    ├── research_node        Knowledge base retrieval
    ├── seo_node             SEO optimization agent
    ├── competitive_intel    Competitive intelligence agent
    ├── product_marketing    Product marketing agent
    ├── approval_node        interrupt() — human approve/reject + feedback
    ├── canva_node           Gemini image generation
    ├── jira_node / confluence_node   DevOps integrations
    └── memory_node          Archive + persist + learn
    │
    ├── Infra Abstraction    Toggleable backends (local ↔ Azure)
    │   ├── Vector Store     Qdrant ↔ Azure AI Search
    │   ├── Document Store   PostgreSQL ↔ Cosmos DB
    │   └── Blob Store       Local FS ↔ Azure Blob
    │
    ├── Redis                Session state (48h TTL), rate limit counters
    ├── Vector Store          brand_voice, knowledge_base, learning_memory,
    │                         directional_memory, agency_brain
    └── PostgreSQL            18+ tables: workflows, campaigns, schedules,
                              experiments, teams, audit_log, conversation_archive,
                              team_profiles, feedback, scores, prompt_versions, ...
```

## File Structure

```
zeta_ima/
├── agents/                   Multi-agent system
│   ├── graph.py              LangGraph StateGraph (14+ nodes)
│   ├── llm_router.py         Multi-LLM dispatcher with fallback + cost tracking
│   ├── cost_tracker.py       Per-call cost tracking + Redis rate limits
│   ├── pool.py               Agent executor (skill + prompt + LLM)
│   ├── router.py             Intent classifier
│   ├── roles.py              13 agent roles registry
│   ├── meeting.py            Multi-agent meeting engine
│   ├── agency_manifest.yaml  Role definitions + department structure
│   ├── state.py              AgentState TypedDict (19+ fields)
│   └── nodes/                copy, review, research, approval, canva, jira,
│                             confluence, memory, recall, seo, competitive_intel,
│                             product_marketing
├── infra/                    Azure-ready abstraction layer
│   ├── vector_store.py       Qdrant ↔ Azure AI Search toggle
│   ├── document_store.py     PostgreSQL ↔ Cosmos DB toggle
│   └── blob_store.py         Local FS ↔ Azure Blob toggle
├── memory/
│   ├── brain.py              Agency Brain — aggregated knowledge + conflict resolution
│   ├── brand.py              Brand voice semantic search
│   ├── campaign.py           Campaign + approved outputs (PostgreSQL)
│   ├── learning.py           Dual-track learning (directional + tactical) + per-team
│   ├── recall.py             Proactive "You've Done This Before" engine
│   ├── conversation_archive.py  Session archive (blob + vector embeddings)
│   ├── feedback.py           Structured feedback (star ratings + tags)
│   ├── scores.py             Campaign score ingestion (Excel, API, manual)
│   ├── team_profile.py       Per-team aggregated learning profiles
│   ├── distiller.py          Conversation → persistent knowledge extraction
│   ├── audit.py              Compliance audit trail
│   └── session.py            Redis checkpointer + shared DB helpers
├── prompts/
│   ├── engine.py             Versioned prompt management (team → global → file fallback)
│   ├── evolution.py          Auto-evolution engine (signal analysis + LLM patching)
│   └── *.md                  Agent system prompts (copy, review, SEO, competitive, PM, ...)
├── analytics/                LLM perf, bottlenecks, quality trends, campaign ROI
├── experiments/              A/B testing engine (create, run, score, conclude)
├── teams_collab/             Team management with roles
├── orchestrator/
│   ├── scheduler.py          Cron-based recurring workflow triggers
│   ├── dispatcher.py         Background task dispatch loop
│   ├── queue.py              PostgreSQL + Redis priority queue
│   ├── a2a.py                Agent-to-Agent protocol (8 message types)
│   └── router.py             Intent → pipeline routing
├── workflows/
│   ├── engine.py             Stage-by-stage executor
│   ├── escalation.py         Stuck detection → Jira escalation
│   ├── templates.py          8+ workflow templates
│   └── models.py             Workflow + stage DB models
├── skills/                   16 skills, 50+ prompts, user codable skills
├── ingest/                   PDF, DOCX, URL, Confluence, Teams chat → vector store
├── integrations/             Buffer, Canva, Confluence, DALL-E, Gemini, GitHub,
│                             Jira, LinkedIn, Mailchimp, SEMrush, SendGrid, Vault,
│                             analytics_pull (Mailchimp, GA4, LinkedIn connectors)
├── api/
│   ├── app.py                FastAPI factory (20+ routers)
│   ├── auth.py               Teams SSO + role enrichment
│   └── routes/               analytics, brain, campaigns, chat, costs, dashboard,
│                             experiments, health, history, ingest, notifications,
│                             programs, prompts, schedules, scores, settings, skills,
│                             tasks, teams_collab, user_skills, workflows, workflow_ws
├── bot/                      Teams bot (Adaptive Cards, proactive messaging)
├── notify/                   Graph API notifications + WebSocket push
└── config.py                 Pydantic settings (60+ env vars)

frontend/                     Next.js app
├── app/                      Pages: chat, workflows, skills, dashboard, analytics,
│                             brain, programs, settings, ingest, experiments
├── components/               Sidebar, PreviewPanel, AuditTimeline, NotificationBell,
│                             AgentTimeline, MeetingTranscript, IngestProgress
└── lib/                      api.ts, useNotifications.ts

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
| **History** | Conversation archive search, session detail, similar sessions |
| **Scores** | Campaign score upload (Excel/manual/API), trends, per-campaign view |
| **Prompts** | Prompt version management, evolution queue, approve/reject changes |
| **Health** | Redis, vector store, PostgreSQL connectivity checks |

Full API docs at `http://localhost:8000/docs` (Swagger UI).

## Tech Stack

- **Backend** — Python 3.11+, FastAPI, LangGraph, SQLAlchemy (async), asyncpg
- **Frontend** — Next.js, TypeScript, Tailwind CSS
- **LLMs** — Azure OpenAI GPT-4o/4o-mini, Anthropic Claude, Google Gemini / Nano Banana 2 (fallback chains)
- **Vector DB** — Qdrant (dev) ↔ Azure AI Search (prod) — 5 collections
- **Database** — PostgreSQL (dev) ↔ Cosmos DB (prod) — 18+ tables
- **Blob Storage** — Local filesystem (dev) ↔ Azure Blob (prod)
- **Cache** — Redis (sessions, rate limits, notifications)
- **Integrations** — Teams Bot Framework, Jira, Confluence, Buffer, Canva, LinkedIn, Mailchimp, SendGrid, SEMrush, GA4
- **Security** — Teams SSO JWT, Azure Key Vault, Fernet encryption, RestrictedPython sandbox

## License

MIT
