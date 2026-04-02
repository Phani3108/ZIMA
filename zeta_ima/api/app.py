"""
FastAPI application factory for Zeta IMA.

Startup sequence:
  1. Ensure Qdrant collections exist (brand_voice, knowledge_base, learning_memory, directional_memory, agency_brain)
  2. Create all PostgreSQL tables
  3. Initialize notification service
  4. Start background engines (escalation monitor, orchestrator dispatcher)
  5. Mount routers (Teams webhook + web app API + Genesis v2)

Pattern reused from RDT 6/orchestrator/app.py.
"""

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from zeta_ima.api.routes.activity import router as activity_router
from zeta_ima.api.routes.analytics import router as analytics_router
from zeta_ima.api.routes.audit import router as audit_router
from zeta_ima.api.routes.campaigns import router as campaigns_router
from zeta_ima.api.routes.chat import router as chat_router
from zeta_ima.api.routes.dashboard import router as dashboard_router
from zeta_ima.api.routes.health import router as health_router
from zeta_ima.api.routes.ingest import router as ingest_router
from zeta_ima.api.routes.notifications import router as notifications_router
from zeta_ima.api.routes.programs import router as programs_router
from zeta_ima.api.routes.settings import router as settings_router
from zeta_ima.api.routes.skills import router as skills_router
from zeta_ima.api.routes.workflow_ws import router as workflow_ws_router
from zeta_ima.api.routes.workflows import router as workflows_router
# Genesis v2 routes
from zeta_ima.api.routes.tasks import router as tasks_router
from zeta_ima.api.routes.brain import router as brain_router
from zeta_ima.api.routes.distill import router as distill_router
from zeta_ima.api.routes.user_skills import router as user_skills_router
# Phase 3 routes
from zeta_ima.api.routes.schedules import router as schedules_router
from zeta_ima.api.routes.experiments import router as experiments_router
from zeta_ima.api.routes.costs import router as costs_router
from zeta_ima.api.routes.teams_collab import router as teams_collab_router
from zeta_ima.api.routes.history import router as history_router
from zeta_ima.api.routes.scores import router as scores_router
from zeta_ima.api.routes.prompts import router as prompts_router
from zeta_ima.memory.brand import ensure_collection
from zeta_ima.memory.campaign import init_db
from zeta_ima.ingest.pipeline import init_ingest_db
from zeta_ima.integrations.vault import vault
from zeta_ima.workflows.models import init_workflow_db
from zeta_ima.workflows.escalation import escalation_engine
from zeta_ima.config import settings as cfg


def create_app() -> FastAPI:
    _log = logging.getLogger(__name__)

    app = FastAPI(
        title="Zeta IMA — AI Marketing Agency",
        version="0.7.0",
        docs_url="/docs",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[cfg.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    # ── Global exception handler — structured errors for the frontend ──
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        _log.error(f"Unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
        # Map known exception types to user-friendly messages
        error_type = type(exc).__name__
        detail = str(exc)

        # Connection errors
        if "Connection refused" in detail or "ConnectionRefusedError" in error_type:
            service = "unknown service"
            if "5432" in detail or "5433" in detail or "asyncpg" in detail.lower():
                service = "PostgreSQL"
            elif "6379" in detail:
                service = "Redis"
            elif "6333" in detail:
                service = "Qdrant"
            return JSONResponse(status_code=503, content={
                "error": f"Cannot connect to {service}",
                "detail": f"{service} is not reachable. Check that the service is running and the connection URL is correct.",
                "service": service,
                "type": "connection_error",
            })

        # Auth errors
        if "401" in detail or "Unauthorized" in detail or "authentication" in detail.lower():
            return JSONResponse(status_code=401, content={
                "error": "Authentication failed",
                "detail": "Your session may have expired. Please refresh and try again.",
                "type": "auth_error",
            })

        # Vault / credential errors
        if "Fernet" in detail or "vault" in detail.lower() or "decrypt" in detail.lower():
            return JSONResponse(status_code=500, content={
                "error": "Credential vault error",
                "detail": "The encryption key may have changed. Re-enter your API keys in Settings → Integrations.",
                "type": "vault_error",
            })

        # Integration API errors
        if "httpx" in error_type.lower() or "timeout" in detail.lower():
            return JSONResponse(status_code=502, content={
                "error": "External service error",
                "detail": f"An external API call failed: {detail[:200]}",
                "type": "integration_error",
            })

        # Default
        return JSONResponse(status_code=500, content={
            "error": "Internal server error",
            "detail": f"{error_type}: {detail[:300]}",
            "type": "server_error",
        })

    @app.on_event("startup")
    async def startup():
        ensure_collection()            # Vector store: brand_voice
        await init_db()                # PostgreSQL: campaigns, approved_outputs, conversation_refs
        await init_ingest_db()         # PostgreSQL: ingest_jobs + Vector store: knowledge_base
        await init_workflow_db()       # PostgreSQL: workflows, workflow_stages, workflow_escalations
        await vault.init()             # PostgreSQL: integration_keys

        # Learning document store (new tables for phases H-M)
        try:
            from zeta_ima.infra.document_store import get_document_store
            ds = get_document_store()
            await ds.init()            # 6 new tables: conversation_archive, team_learning_profiles, etc.
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Document store init: {e}")

        # Phase 3b/3c init
        try:
            from zeta_ima.memory.learning import init_learning_db
            await init_learning_db()   # PostgreSQL: workflow_outcomes + Vector store: learning_memory, directional_memory
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Learning memory init: {e}")

        try:
            from zeta_ima.memory.audit import init_audit_db
            await init_audit_db()      # PostgreSQL: audit_log
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Audit DB init: {e}")

        try:
            from zeta_ima.api.routes.programs import init_programs_db
            await init_programs_db()   # PostgreSQL: programs
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Programs DB init: {e}")

        # Genesis v2 init
        try:
            from zeta_ima.memory.brain import init_brain_db
            await init_brain_db()      # Vector store: agency_brain + PostgreSQL: brain_contributions
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Brain DB init: {e}")

        try:
            from zeta_ima.skills.executor import init_user_skills_db
            await init_user_skills_db()   # PostgreSQL: user_skills
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"User skills DB init: {e}")

        try:
            from zeta_ima.orchestrator.queue import init_task_db
            await init_task_db()          # PostgreSQL: tasks
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Task DB init: {e}")

        try:
            from zeta_ima.orchestrator.scheduler import init_scheduler_db, scheduler
            await init_scheduler_db()     # PostgreSQL: schedules
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Scheduler DB init: {e}")

        try:
            from zeta_ima.experiments import init_ab_db
            await init_ab_db()            # PostgreSQL: experiments, experiment_variants
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"A/B testing DB init: {e}")

        try:
            from zeta_ima.agents.cost_tracker import init_cost_db, cost_tracker
            await init_cost_db()          # PostgreSQL: llm_usage
            await cost_tracker.init(redis_url=cfg.redis_url)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Cost tracker DB init: {e}")

        try:
            from zeta_ima.teams_collab import init_teams_db
            await init_teams_db()         # PostgreSQL: teams, team_members
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Teams DB init: {e}")

        try:
            from zeta_ima.notify.service import notifications
            await notifications.init(redis_url=cfg.redis_url)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Notifications init: {e}")

        await escalation_engine.start()  # Background monitor for stuck stages

        # Start orchestrator dispatcher
        try:
            from zeta_ima.orchestrator.dispatcher import start_dispatcher
            await start_dispatcher()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Dispatcher start: {e}")

        # Start scheduler
        try:
            from zeta_ima.orchestrator.scheduler import scheduler
            await scheduler.start()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Scheduler start: {e}")

    # Teams bot webhook (no auth — authenticated by Bot Framework)
    app.include_router(activity_router)

    # Web app API (Teams SSO authenticated)
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(settings_router)
    app.include_router(ingest_router)
    app.include_router(analytics_router)
    app.include_router(campaigns_router)

    # Phase 3: Skills, Workflows, Dashboard, Programs
    app.include_router(skills_router)
    app.include_router(workflows_router)
    app.include_router(dashboard_router)
    app.include_router(programs_router)
    app.include_router(notifications_router)
    app.include_router(audit_router)

    # Genesis v2
    app.include_router(tasks_router)
    app.include_router(brain_router)
    app.include_router(distill_router)
    app.include_router(user_skills_router)

    # Phase 3: Scheduling, A/B testing, Costs, Teams
    app.include_router(schedules_router)
    app.include_router(experiments_router)
    app.include_router(costs_router)
    app.include_router(teams_collab_router)

    # Learning moat
    app.include_router(history_router)
    app.include_router(scores_router)
    app.include_router(prompts_router)

    # WebSocket endpoints
    app.include_router(workflow_ws_router)

    return app


app = create_app()
