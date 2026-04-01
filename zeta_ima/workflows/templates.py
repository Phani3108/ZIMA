"""
Pre-built workflow templates.

Each template defines a sequence of stages with agent assignments and prompt IDs.
Templates are pure data — the workflow engine executes them.
"""

WORKFLOW_TEMPLATES: dict[str, dict] = {
    "linkedin_campaign": {
        "name": "LinkedIn Campaign",
        "skill_id": "social_media",
        "description": "End-to-end LinkedIn post: research → draft → design → preview → schedule.",
        "stages": [
            {"name": "Research",           "agent": "research",  "prompt": "competitive_landscape", "skill_id": "competitive_intel"},
            {"name": "Brand Context",      "agent": "research",  "prompt": "voice_check",           "skill_id": "brand_voice"},
            {"name": "Draft Copy",         "agent": "copy",      "prompt": "linkedin_post",         "skill_id": "social_media", "requires_approval": True},
            {"name": "Design Visual",      "agent": "design",    "prompt": "social_graphic_set",    "skill_id": "design_brief"},
            {"name": "Preview",            "agent": "copy",      "prompt": "linkedin_post",         "skill_id": "social_media", "requires_approval": True},
            {"name": "Create Jira Ticket", "agent": "copy",      "prompt": "linkedin_post",         "skill_id": "social_media"},
            {"name": "Notify Team",        "agent": "copy",      "prompt": "linkedin_post",         "skill_id": "social_media"},
        ],
    },
    "seo_blog_post": {
        "name": "SEO Blog Post",
        "skill_id": "seo_content",
        "description": "Keyword research → SERP analysis → outline → draft → optimize → review → publish → atomize.",
        "stages": [
            {"name": "Keyword Research",   "agent": "seo",       "prompt": "six_circles",           "skill_id": "keyword_research"},
            {"name": "SERP Analysis",      "agent": "seo",       "prompt": "content_gap",           "skill_id": "keyword_research"},
            {"name": "Outline",            "agent": "copy",      "prompt": "seo_blog_post",         "skill_id": "seo_content", "requires_approval": True},
            {"name": "Draft",              "agent": "copy",      "prompt": "seo_blog_post",         "skill_id": "seo_content"},
            {"name": "SEO Optimization",   "agent": "seo",       "prompt": "content_refresh",       "skill_id": "seo_content"},
            {"name": "Review",             "agent": "copy",      "prompt": "seo_blog_post",         "skill_id": "seo_content", "requires_approval": True},
            {"name": "Atomize Content",    "agent": "copy",      "prompt": "blog_to_15",            "skill_id": "content_atomizer"},
        ],
    },
    "email_launch_sequence": {
        "name": "Email Launch Sequence",
        "skill_id": "email_sequence",
        "description": "Audience research → sequence plan → draft emails → subject lines → template → preview.",
        "stages": [
            {"name": "Audience Research",  "agent": "research",  "prompt": "find_differentiators",  "skill_id": "positioning"},
            {"name": "Sequence Strategy",  "agent": "copy",      "prompt": "launch_sequence",       "skill_id": "email_sequence", "requires_approval": True},
            {"name": "Write Emails",       "agent": "copy",      "prompt": "launch_sequence",       "skill_id": "email_sequence"},
            {"name": "Subject Line Test",  "agent": "copy",      "prompt": "headline_variants",     "skill_id": "direct_response_copy"},
            {"name": "HTML Template",      "agent": "design",    "prompt": "creative_brief",        "skill_id": "design_brief"},
            {"name": "Preview & Test",     "agent": "copy",      "prompt": "launch_sequence",       "skill_id": "email_sequence", "requires_approval": True},
        ],
    },
    "ad_campaign": {
        "name": "Paid Ad Campaign",
        "skill_id": "ad_creative",
        "description": "Audience research → ad copy → visuals → A/B preview → tracking.",
        "stages": [
            {"name": "Audience Research",  "agent": "research",  "prompt": "find_differentiators",  "skill_id": "positioning"},
            {"name": "Ad Copy Variants",   "agent": "copy",      "prompt": "facebook_ad",           "skill_id": "ad_creative"},
            {"name": "Google Ads",         "agent": "copy",      "prompt": "google_ads",            "skill_id": "ad_creative"},
            {"name": "Generate Visuals",   "agent": "design",    "prompt": "ad_image_prompt",       "skill_id": "ad_creative"},
            {"name": "A/B Preview",        "agent": "copy",      "prompt": "facebook_ad",           "skill_id": "ad_creative", "requires_approval": True},
        ],
    },
    "product_launch": {
        "name": "Full Product Launch",
        "skill_id": "product_marketing",
        "description": "Complete launch: competitive analysis → positioning → messaging → landing page → email → social → ads → PR.",
        "stages": [
            {"name": "Competitive Analysis", "agent": "research",  "prompt": "competitor_scan",      "skill_id": "competitive_intel"},
            {"name": "Positioning",          "agent": "research",  "prompt": "find_differentiators", "skill_id": "positioning"},
            {"name": "Messaging Framework",  "agent": "copy",      "prompt": "messaging_framework",  "skill_id": "product_marketing", "requires_approval": True},
            {"name": "Landing Page Copy",    "agent": "copy",      "prompt": "full_landing_page",    "skill_id": "landing_page"},
            {"name": "Email Sequence",       "agent": "copy",      "prompt": "launch_sequence",      "skill_id": "email_sequence"},
            {"name": "Social Campaign",      "agent": "copy",      "prompt": "linkedin_post",        "skill_id": "social_media"},
            {"name": "Ad Creatives",         "agent": "copy",      "prompt": "facebook_ad",          "skill_id": "ad_creative"},
            {"name": "PR Brief",             "agent": "copy",      "prompt": "launch_brief",         "skill_id": "product_marketing"},
            {"name": "Content Atomization",  "agent": "copy",      "prompt": "blog_to_15",           "skill_id": "content_atomizer"},
        ],
    },
    "content_repurpose": {
        "name": "Content Repurpose",
        "skill_id": "content_atomizer",
        "description": "Take existing content → atomize into 15+ assets → design → schedule.",
        "stages": [
            {"name": "Analyze Source",     "agent": "research",  "prompt": "audit_voice",           "skill_id": "brand_voice"},
            {"name": "Atomize",            "agent": "copy",      "prompt": "blog_to_15",            "skill_id": "content_atomizer"},
            {"name": "Design Graphics",    "agent": "design",    "prompt": "social_graphic_set",    "skill_id": "design_brief"},
            {"name": "Preview All",        "agent": "copy",      "prompt": "blog_to_15",            "skill_id": "content_atomizer", "requires_approval": True},
        ],
    },
    "competitive_report": {
        "name": "Competitive Intelligence Report",
        "skill_id": "competitive_intel",
        "description": "Scan → analyze → SWOT → battlecard → publish → notify.",
        "stages": [
            {"name": "Web Research",       "agent": "research",  "prompt": "competitor_scan",       "skill_id": "competitive_intel"},
            {"name": "SWOT Analysis",      "agent": "research",  "prompt": "swot_analysis",         "skill_id": "competitive_intel"},
            {"name": "Battlecard",         "agent": "copy",      "prompt": "battlecard",            "skill_id": "competitive_intel", "requires_approval": True},
        ],
    },
}


def list_templates() -> list[dict]:
    """Return all templates for the API."""
    return [
        {
            "id": tid,
            "name": t["name"],
            "skill_id": t["skill_id"],
            "description": t.get("description", ""),
            "stage_count": len(t["stages"]),
            "stages": [
                {"name": s["name"], "agent": s["agent"], "requires_approval": s.get("requires_approval", False)}
                for s in t["stages"]
            ],
        }
        for tid, t in WORKFLOW_TEMPLATES.items()
    ]
