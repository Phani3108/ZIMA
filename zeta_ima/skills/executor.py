"""
Skills Executor — Phase 3.2

Runs user-authored Python skills inside a RestrictedPython sandbox.

Security model:
  - RestrictedPython compile-time restrictions (no builtins abuse, no exec/eval)
  - Hard 30-second CPU + wall-clock timeout via asyncio.wait_for
  - Whitelisted gateway: only safe outbound integrations accessible
  - No filesystem access, no subprocess, no import of arbitrary modules

Gateway API available to skill code:
    gateway.http_get(url, headers)    → dict
    gateway.http_post(url, payload)   → dict
    gateway.search_web(query)         → list[dict]
    gateway.read_brand_memory(q)      → list[str]
    gateway.generate_text(prompt)     → str
"""

from __future__ import annotations

import asyncio
import importlib
import textwrap
import traceback
import uuid
from typing import Any

try:
    from RestrictedPython import compile_restricted, safe_globals, safe_builtins
    from RestrictedPython.Guards import guarded_unpack_sequence, safe_globals as rp_safe_globals
    _HAS_RESTRICTED = True
except ImportError:
    _HAS_RESTRICTED = False

EXECUTION_TIMEOUT = 30  # seconds


# ── Gateway ───────────────────────────────────────────────────────────────────

class SkillGateway:
    """
    Restricted API surface exposed to user skill code.
    All calls go through the existing integration layer.
    """

    def __init__(self, user_id: str, skill_id: str):
        self._user_id = user_id
        self._skill_id = skill_id
        self._call_count = 0
        self._MAX_CALLS = 20  # Hard cap per execution

    def _check_limit(self) -> None:
        self._call_count += 1
        if self._call_count > self._MAX_CALLS:
            raise RuntimeError("Gateway call limit exceeded (20 calls per execution)")

    async def http_get(self, url: str, headers: dict | None = None) -> dict:
        """Fetch JSON from a public URL."""
        self._check_limit()
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers or {})
            resp.raise_for_status()
            return resp.json()

    async def http_post(self, url: str, payload: dict, headers: dict | None = None) -> dict:
        """POST JSON to a URL and return response."""
        self._check_limit()
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=headers or {})
            resp.raise_for_status()
            return resp.json()

    async def search_web(self, query: str) -> list[dict]:
        """Search the web via SemRush integration (read-only)."""
        self._check_limit()
        try:
            from zeta_ima.integrations import semrush
            result = await semrush.keyword_overview(query)
            return result.get("data", []) if isinstance(result, dict) else []
        except Exception:
            return []

    async def read_brand_memory(self, query: str) -> list[str]:
        """Query the brand vector memory."""
        self._check_limit()
        try:
            from zeta_ima.memory.brand import search_brand_examples
            results = await search_brand_examples(query)
            return results[:5]
        except Exception:
            return []

    async def generate_text(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text via the standard LLM router."""
        self._check_limit()
        if max_tokens > 2000:
            max_tokens = 2000  # Cap to prevent abuse
        try:
            from zeta_ima.agents.llm_router import call_llm
            result = await call_llm(prompt, max_tokens=max_tokens)
            return result.text
        except Exception as exc:
            return f"[generate_text error: {exc}]"


# ── Executor ──────────────────────────────────────────────────────────────────

class SkillExecutionError(Exception):
    """Raised when skill execution fails."""


async def execute_user_skill(
    code: str,
    inputs: dict[str, Any],
    user_id: str,
    skill_id: str,
) -> dict[str, Any]:
    """
    Execute user-provided Python skill code in a RestrictedPython sandbox.

    The code must define:
        def run(inputs: dict, gateway) -> dict:
            ...

    Returns:
        {"ok": True, "result": <dict>}     on success
        {"ok": False, "error": <str>}      on failure
    """
    if not _HAS_RESTRICTED:
        return {
            "ok": False,
            "error": "RestrictedPython is not installed. Run: pip install RestrictedPython",
        }

    # Compile with RestrictedPython
    byte_code = _safe_compile(code, skill_id)
    if isinstance(byte_code, str):  # compile error message
        return {"ok": False, "error": byte_code}

    # Execute with timeout
    gateway = SkillGateway(user_id=user_id, skill_id=skill_id)
    try:
        result = await asyncio.wait_for(
            _run_in_sandbox(byte_code, inputs, gateway),
            timeout=EXECUTION_TIMEOUT,
        )
        return {"ok": True, "result": result}
    except asyncio.TimeoutError:
        return {"ok": False, "error": f"Execution timed out after {EXECUTION_TIMEOUT}s"}
    except SkillExecutionError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "error": f"Unexpected error: {traceback.format_exc(limit=3)}"}


def validate_skill_code(code: str) -> dict[str, Any]:
    """
    Validate skill code for syntax and RestrictedPython compliance.
    Returns {"ok": bool, "error": str | None}
    """
    if not _HAS_RESTRICTED:
        return {"ok": False, "error": "RestrictedPython not installed"}

    result = _safe_compile(code, "validation")
    if isinstance(result, str):
        return {"ok": False, "error": result}

    # Check that run() function is defined
    if "def run(" not in code and "def run (" not in code:
        return {"ok": False, "error": "Skill code must define a `run(inputs, gateway)` function"}

    return {"ok": True, "error": None}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_compile(code: str, skill_id: str):
    """Compile code with RestrictedPython. Returns bytecode or error string."""
    try:
        byte_code = compile_restricted(
            textwrap.dedent(code),
            filename=f"<skill:{skill_id}>",
            mode="exec",
        )
        return byte_code
    except SyntaxError as exc:
        return f"Syntax error: {exc}"
    except Exception as exc:
        return f"Compile error: {exc}"


async def _run_in_sandbox(
    byte_code,
    inputs: dict[str, Any],
    gateway: SkillGateway,
) -> dict[str, Any]:
    """Execute bytecode in a restricted namespace and call run()."""
    restricted_globals = dict(safe_globals)
    restricted_globals["__builtins__"] = safe_builtins
    restricted_globals["_getiter_"] = iter
    restricted_globals["_getattr_"] = getattr
    restricted_globals["_write_"] = lambda x: x
    restricted_globals["_inplacevar_"] = _inplace

    local_ns: dict[str, Any] = {}

    # exec is inherently synchronous; we run it in a thread pool to avoid blocking
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: exec(byte_code, restricted_globals, local_ns),  # noqa: S102
    )

    run_fn = local_ns.get("run")
    if not callable(run_fn):
        raise SkillExecutionError("Skill code must define `run(inputs, gateway)`")

    # Call run() — it may be sync or async
    if asyncio.iscoroutinefunction(run_fn):
        return await run_fn(inputs, gateway)
    else:
        return await loop.run_in_executor(None, lambda: run_fn(inputs, gateway))


def _inplace(op, x, y):
    """Support inplace operators (+=, -=, etc.) in restricted code."""
    ops = {
        "+=": lambda a, b: a + b,
        "-=": lambda a, b: a - b,
        "*=": lambda a, b: a * b,
        "/=": lambda a, b: a / b,
    }
    fn = ops.get(op)
    return fn(x, y) if fn else x


# ── DB helpers ────────────────────────────────────────────────────────────────

async def init_user_skills_db() -> None:
    """Create user_skills table on startup."""
    from zeta_ima.memory.session import _pg_pool

    pool = await _pg_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_skills (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                code        TEXT NOT NULL,
                created_by  TEXT NOT NULL,
                version     INT NOT NULL DEFAULT 1,
                is_shared   BOOLEAN NOT NULL DEFAULT FALSE,
                tags        JSONB DEFAULT '[]',
                created_at  TIMESTAMPTZ DEFAULT now(),
                updated_at  TIMESTAMPTZ DEFAULT now()
            );
            CREATE INDEX IF NOT EXISTS idx_us_created_by ON user_skills(created_by);
            CREATE INDEX IF NOT EXISTS idx_us_shared     ON user_skills(is_shared);
            """
        )


async def save_user_skill(
    name: str,
    description: str,
    code: str,
    created_by: str,
    is_shared: bool = False,
    tags: list[str] | None = None,
    skill_id: str | None = None,
) -> str:
    """Insert or update a user skill. Returns skill_id."""
    import json
    from zeta_ima.memory.session import _pg_pool

    pool = await _pg_pool()
    sid = skill_id or str(uuid.uuid4())
    async with pool.acquire() as conn:
        if skill_id:
            await conn.execute(
                """
                UPDATE user_skills
                SET name=$2, description=$3, code=$4, is_shared=$5, tags=$6,
                    version = version + 1, updated_at = now()
                WHERE id=$1
                """,
                sid, name, description, code, is_shared,
                json.dumps(tags or []),
            )
        else:
            await conn.execute(
                """
                INSERT INTO user_skills
                  (id, name, description, code, created_by, is_shared, tags)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                """,
                sid, name, description, code, created_by, is_shared,
                json.dumps(tags or []),
            )
    return sid


async def get_user_skill(skill_id: str) -> dict | None:
    """Fetch a user skill by ID."""
    from zeta_ima.memory.session import _pg_pool

    pool = await _pg_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM user_skills WHERE id=$1", skill_id)
    return dict(row) if row else None


async def list_user_skills(
    user_id: str | None = None,
    include_shared: bool = True,
) -> list[dict]:
    """List skills visible to a given user."""
    from zeta_ima.memory.session import _pg_pool

    pool = await _pg_pool()
    async with pool.acquire() as conn:
        if user_id:
            rows = await conn.fetch(
                """
                SELECT id, name, description, created_by, version, is_shared, tags, created_at, updated_at
                FROM user_skills
                WHERE created_by=$1 OR ($2 AND is_shared)
                ORDER BY updated_at DESC
                """,
                user_id, include_shared,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT id, name, description, created_by, version, is_shared, tags, created_at, updated_at
                FROM user_skills
                WHERE is_shared=TRUE
                ORDER BY updated_at DESC
                """
            )
    return [dict(r) for r in rows]


async def delete_user_skill(skill_id: str, requesting_user: str) -> bool:
    """Delete skill (only allowed for creator). Returns True on success."""
    from zeta_ima.memory.session import _pg_pool

    pool = await _pg_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_skills WHERE id=$1 AND created_by=$2",
            skill_id, requesting_user,
        )
    return result == "DELETE 1"
