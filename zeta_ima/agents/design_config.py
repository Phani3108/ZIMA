"""
Design Agent engine configuration — tool routing, platform presets, and rules.

Manager configures via dashboard; designers execute via Teams prompts.
The config is read at execution time by design_node to decide which tool
(Gemini / DALL-E / Canva / etc.) and what dimensions to use.

Storage: PostgreSQL tables.  Falls back to sensible defaults when no rows exist.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from zeta_ima.config import settings

log = logging.getLogger(__name__)

# ── ORM base ────────────────────────────────────────────────────────────────

_engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
)
_Session = async_sessionmaker(_engine, expire_on_commit=False)


class _Base(DeclarativeBase):
    pass


# ── Tool routing table ──────────────────────────────────────────────────────

class ToolConfigRow(_Base):
    """Per-skill tool routing: primary tool, backup tool, enabled flag."""
    __tablename__ = "design_tool_config"

    skill_id = Column(String(64), primary_key=True)           # e.g. "social_visual"
    primary_tool = Column(String(32), nullable=False, default="gemini")  # gemini | dalle | canva | figma | midjourney
    backup_tool = Column(String(32), nullable=False, default="dalle")
    enabled = Column(Boolean, default=True)
    updated_by = Column(String(128), default="")              # user ID
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Platform presets table ──────────────────────────────────────────────────

class PresetRow(_Base):
    """Per-skill + platform image dimensions and format."""
    __tablename__ = "design_presets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_id = Column(String(64), nullable=False)             # e.g. "social_visual"
    platform = Column(String(64), nullable=False)             # e.g. "instagram_post"
    label = Column(String(128), nullable=False, default="")   # display: "Instagram Post"
    width = Column(Integer, nullable=False, default=1080)
    height = Column(Integer, nullable=False, default=1080)
    aspect_ratio = Column(String(16), nullable=False, default="1:1")
    resolution = Column(String(8), nullable=False, default="1K")  # 512 | 1K | 2K | 4K
    format = Column(String(8), nullable=False, default="png")     # png | jpg | webp
    updated_by = Column(String(128), default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── Rules table ─────────────────────────────────────────────────────────────

class DesignRulesRow(_Base):
    """Global design engine rules — one row, singleton."""
    __tablename__ = "design_rules"

    id = Column(Integer, primary_key=True, default=1)
    max_iterations = Column(Integer, default=3)
    default_quality = Column(String(16), default="hd")        # standard | hd
    auto_review = Column(Boolean, default=True)
    auto_approve_min_score = Column(Integer, default=8)
    style_prompt_prefix = Column(Text, default="")            # prepended to every prompt
    updated_by = Column(String(128), default="")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── DB init ─────────────────────────────────────────────────────────────────

async def init_design_config_db() -> None:
    """Create tables if they don't exist."""
    async with _engine.begin() as conn:
        await conn.run_sync(_Base.metadata.create_all)
    log.info("Design config tables ready")


# ── Dataclasses for runtime consumption ─────────────────────────────────────

@dataclass
class ToolConfig:
    skill_id: str
    primary_tool: str = "gemini"
    backup_tool: str = "dalle"
    enabled: bool = True


@dataclass
class Preset:
    skill_id: str
    platform: str
    label: str = ""
    width: int = 1080
    height: int = 1080
    aspect_ratio: str = "1:1"
    resolution: str = "1K"
    format: str = "png"


@dataclass
class DesignRules:
    max_iterations: int = 3
    default_quality: str = "hd"
    auto_review: bool = True
    auto_approve_min_score: int = 8
    style_prompt_prefix: str = ""


# ── Default presets (seeded on first load if DB empty) ──────────────────────

DEFAULT_PRESETS: list[dict] = [
    # Social media
    {"skill_id": "social_visual", "platform": "instagram_post",  "label": "Instagram Post",     "width": 1080, "height": 1080, "aspect_ratio": "1:1",  "resolution": "1K"},
    {"skill_id": "social_visual", "platform": "instagram_story", "label": "Instagram Story",    "width": 1080, "height": 1920, "aspect_ratio": "9:16", "resolution": "1K"},
    {"skill_id": "social_visual", "platform": "linkedin_post",   "label": "LinkedIn Post",      "width": 1200, "height": 1200, "aspect_ratio": "1:1",  "resolution": "1K"},
    {"skill_id": "social_visual", "platform": "linkedin_banner", "label": "LinkedIn Banner",    "width": 1584, "height": 396,  "aspect_ratio": "4:1",  "resolution": "1K"},
    {"skill_id": "social_visual", "platform": "twitter_post",    "label": "Twitter Post",       "width": 1200, "height": 675,  "aspect_ratio": "16:9", "resolution": "1K"},
    {"skill_id": "social_visual", "platform": "facebook_post",   "label": "Facebook Post",      "width": 1200, "height": 630,  "aspect_ratio": "16:9", "resolution": "1K"},
    {"skill_id": "social_visual", "platform": "facebook_cover",  "label": "Facebook Cover",     "width": 820,  "height": 312,  "aspect_ratio": "21:9", "resolution": "1K"},
    # Email
    {"skill_id": "email_header",  "platform": "email_600",       "label": "Email Header 600px", "width": 600,  "height": 200,  "aspect_ratio": "3:1",  "resolution": "1K"},
    {"skill_id": "email_header",  "platform": "email_700",       "label": "Email Header 700px", "width": 700,  "height": 233,  "aspect_ratio": "3:1",  "resolution": "1K"},
    # Ads
    {"skill_id": "ad_creative",   "platform": "facebook_ad",     "label": "Facebook Ad",        "width": 1200, "height": 628,  "aspect_ratio": "16:9", "resolution": "1K"},
    {"skill_id": "ad_creative",   "platform": "google_display",  "label": "Google Display",     "width": 1200, "height": 628,  "aspect_ratio": "16:9", "resolution": "1K"},
    {"skill_id": "ad_creative",   "platform": "linkedin_ad",     "label": "LinkedIn Ad",        "width": 1200, "height": 627,  "aspect_ratio": "16:9", "resolution": "1K"},
    {"skill_id": "ad_creative",   "platform": "instagram_ad",    "label": "Instagram Ad",       "width": 1080, "height": 1080, "aspect_ratio": "1:1",  "resolution": "1K"},
    # Presentation
    {"skill_id": "presentation_slide", "platform": "slide_16_9", "label": "Widescreen Slide",   "width": 1920, "height": 1080, "aspect_ratio": "16:9", "resolution": "2K"},
    {"skill_id": "presentation_slide", "platform": "slide_4_3",  "label": "Standard Slide",     "width": 1024, "height": 768,  "aspect_ratio": "4:3",  "resolution": "1K"},
    # Brand
    {"skill_id": "brand_asset",   "platform": "logo_square",     "label": "Logo (Square)",      "width": 512,  "height": 512,  "aspect_ratio": "1:1",  "resolution": "1K"},
    {"skill_id": "brand_asset",   "platform": "banner_wide",     "label": "Banner (Wide)",      "width": 1920, "height": 480,  "aspect_ratio": "4:1",  "resolution": "2K"},
    {"skill_id": "brand_asset",   "platform": "favicon",         "label": "Favicon",            "width": 64,   "height": 64,   "aspect_ratio": "1:1",  "resolution": "512"},
]

DEFAULT_TOOL_CONFIGS: list[dict] = [
    {"skill_id": "social_visual",      "primary_tool": "gemini", "backup_tool": "dalle"},
    {"skill_id": "email_header",       "primary_tool": "gemini", "backup_tool": "canva"},
    {"skill_id": "brand_asset",        "primary_tool": "gemini", "backup_tool": "dalle"},
    {"skill_id": "ad_creative",        "primary_tool": "gemini", "backup_tool": "dalle"},
    {"skill_id": "presentation_slide", "primary_tool": "gemini", "backup_tool": "dalle"},
]


# ── Config loader (reads from DB, falls back to defaults) ──────────────────

class DesignConfigLoader:
    """Read/write design engine configuration from PostgreSQL."""

    async def get_tool_config(self, skill_id: str) -> ToolConfig:
        """Get tool routing for a skill. Falls back to global image_provider_chain."""
        from sqlalchemy import select
        async with _Session() as session:
            row = await session.get(ToolConfigRow, skill_id)
            if row:
                return ToolConfig(
                    skill_id=row.skill_id,
                    primary_tool=row.primary_tool,
                    backup_tool=row.backup_tool,
                    enabled=row.enabled,
                )
        # Default from first matching DEFAULT_TOOL_CONFIGS or global chain
        for d in DEFAULT_TOOL_CONFIGS:
            if d["skill_id"] == skill_id:
                return ToolConfig(skill_id=skill_id, primary_tool=d["primary_tool"], backup_tool=d["backup_tool"])
        chain = settings.image_provider_chain.split(",")
        return ToolConfig(skill_id=skill_id, primary_tool=chain[0].strip(), backup_tool=chain[1].strip() if len(chain) > 1 else "dalle")

    async def get_all_tool_configs(self) -> list[ToolConfig]:
        """Get all tool configs (for manager dashboard)."""
        from sqlalchemy import select
        async with _Session() as session:
            result = await session.execute(select(ToolConfigRow))
            rows = result.scalars().all()
        if rows:
            return [ToolConfig(skill_id=r.skill_id, primary_tool=r.primary_tool, backup_tool=r.backup_tool, enabled=r.enabled) for r in rows]
        return [ToolConfig(**d) for d in DEFAULT_TOOL_CONFIGS]

    async def save_tool_config(self, config: ToolConfig, user_id: str = "") -> None:
        """Upsert tool config for a skill."""
        from sqlalchemy import select
        async with _Session() as session:
            row = await session.get(ToolConfigRow, config.skill_id)
            if row:
                row.primary_tool = config.primary_tool
                row.backup_tool = config.backup_tool
                row.enabled = config.enabled
                row.updated_by = user_id
            else:
                session.add(ToolConfigRow(
                    skill_id=config.skill_id,
                    primary_tool=config.primary_tool,
                    backup_tool=config.backup_tool,
                    enabled=config.enabled,
                    updated_by=user_id,
                ))
            await session.commit()

    async def get_presets(self, skill_id: str) -> list[Preset]:
        """Get all presets for a skill."""
        from sqlalchemy import select
        async with _Session() as session:
            result = await session.execute(
                select(PresetRow).where(PresetRow.skill_id == skill_id)
            )
            rows = result.scalars().all()
        if rows:
            return [Preset(skill_id=r.skill_id, platform=r.platform, label=r.label,
                           width=r.width, height=r.height, aspect_ratio=r.aspect_ratio,
                           resolution=r.resolution, format=r.format) for r in rows]
        return [Preset(**{k: v for k, v in d.items() if k != "updated_by"})
                for d in DEFAULT_PRESETS if d["skill_id"] == skill_id]

    async def get_all_presets(self) -> list[Preset]:
        """Get all presets across all skills."""
        from sqlalchemy import select
        async with _Session() as session:
            result = await session.execute(select(PresetRow))
            rows = result.scalars().all()
        if rows:
            return [Preset(skill_id=r.skill_id, platform=r.platform, label=r.label,
                           width=r.width, height=r.height, aspect_ratio=r.aspect_ratio,
                           resolution=r.resolution, format=r.format) for r in rows]
        return [Preset(**{k: v for k, v in d.items() if k != "updated_by"})
                for d in DEFAULT_PRESETS]

    async def save_preset(self, preset: Preset, user_id: str = "") -> None:
        """Upsert a preset."""
        from sqlalchemy import select, and_
        async with _Session() as session:
            result = await session.execute(
                select(PresetRow).where(
                    and_(PresetRow.skill_id == preset.skill_id, PresetRow.platform == preset.platform)
                )
            )
            row = result.scalar_one_or_none()
            if row:
                row.label = preset.label
                row.width = preset.width
                row.height = preset.height
                row.aspect_ratio = preset.aspect_ratio
                row.resolution = preset.resolution
                row.format = preset.format
                row.updated_by = user_id
            else:
                session.add(PresetRow(
                    skill_id=preset.skill_id,
                    platform=preset.platform,
                    label=preset.label,
                    width=preset.width,
                    height=preset.height,
                    aspect_ratio=preset.aspect_ratio,
                    resolution=preset.resolution,
                    format=preset.format,
                    updated_by=user_id,
                ))
            await session.commit()

    async def get_rules(self) -> DesignRules:
        """Get global design rules."""
        async with _Session() as session:
            row = await session.get(DesignRulesRow, 1)
            if row:
                return DesignRules(
                    max_iterations=row.max_iterations,
                    default_quality=row.default_quality,
                    auto_review=row.auto_review,
                    auto_approve_min_score=row.auto_approve_min_score,
                    style_prompt_prefix=row.style_prompt_prefix,
                )
        return DesignRules()

    async def save_rules(self, rules: DesignRules, user_id: str = "") -> None:
        """Upsert global design rules."""
        async with _Session() as session:
            row = await session.get(DesignRulesRow, 1)
            if row:
                row.max_iterations = rules.max_iterations
                row.default_quality = rules.default_quality
                row.auto_review = rules.auto_review
                row.auto_approve_min_score = rules.auto_approve_min_score
                row.style_prompt_prefix = rules.style_prompt_prefix
                row.updated_by = user_id
            else:
                session.add(DesignRulesRow(
                    id=1,
                    max_iterations=rules.max_iterations,
                    default_quality=rules.default_quality,
                    auto_review=rules.auto_review,
                    auto_approve_min_score=rules.auto_approve_min_score,
                    style_prompt_prefix=rules.style_prompt_prefix,
                    updated_by=user_id,
                ))
            await session.commit()

    async def get_preset_for_platform(self, skill_id: str, platform: str) -> Preset | None:
        """Get a specific preset for a skill+platform combo."""
        presets = await self.get_presets(skill_id)
        for p in presets:
            if p.platform == platform:
                return p
        return presets[0] if presets else None


design_config = DesignConfigLoader()
