from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="lead_magnet",
    name="Lead Magnet",
    description="Create high-converting opt-in offers — ebooks, checklists, templates, calculators. Includes hook generation and full asset BUILD mode.",
    icon="magnet",
    category="strategy",
    platforms=["claude", "openai"],
    tools_used=["canva", "confluence"],
    workflow_stages=["research", "hook", "build", "design", "review"],
    default_llm="claude",
    fallback_llms=["openai", "gemini"],
    prompts=[
        PromptTemplate(
            id="create_offer",
            name="Create Opt-in Offer",
            description="Design a lead magnet concept with hook, format, and distribution plan.",
            variables=["target_audience", "pain_point", "desired_outcome", "business_context"],
            platform="claude",
            agent="copy",
            prompt_text="""You are a lead generation strategist.

AUDIENCE: {{target_audience}}
PAIN POINT: {{pain_point}}
DESIRED OUTCOME: {{desired_outcome}}
BUSINESS: {{business_context}}

{{brand_voice_context}}

Generate 5 lead magnet concepts. For each:

1. **Title** (specific, benefit-driven, e.g., "The 7-Minute SEO Audit Checklist")
2. **Format** (checklist / template / toolkit / mini-course / calculator / swipe file)
3. **Hook** (why someone would trade their email for this)
4. **Contents Outline** (what's inside, 5-8 items)
5. **Landing Page Headline** (for the opt-in page)
6. **Distribution Channels** (where to promote it)
7. **Estimated Conversion Rate** (low/medium/high based on format + specificity)

RECOMMENDATION: Which concept to build first and why.

Rules:
- Must solve a specific, urgent problem (not "learn about marketing")
- Must be consumable in < 15 minutes
- Must make the reader want to buy your product after using it""",
        ),
        PromptTemplate(
            id="build_full_asset",
            name="Build Mode — Full Lead Magnet",
            description="Generate the complete lead magnet content, ready to design.",
            variables=["lead_magnet_title", "format", "outline", "target_audience"],
            platform="claude",
            agent="copy",
            prompt_text="""BUILD MODE: Create the complete lead magnet.

TITLE: {{lead_magnet_title}}
FORMAT: {{format}}
OUTLINE: {{outline}}
AUDIENCE: {{target_audience}}

{{brand_voice_context}}
{{kb_context}}

Write the FULL lead magnet content:

1. **Cover Page** — Title, subtitle, author/company name
2. **Introduction** (why this matters, what they'll learn, credibility statement)
3. **Main Content** — All sections from the outline, fully written
4. **Action Steps** — Clear next steps after consuming
5. **CTA** — What to do next (book a call, start a trial, etc.)
6. **About Section** — Brief company/author bio

Formatting requirements:
- Use headers, bullets, numbered lists for scannability
- Include placeholder markers [IMAGE: description] for designer
- Include placeholder markers [CALLOUT: text] for highlighted boxes
- Word count: 1500-3000 words depending on format

Output: Complete markdown content ready for design in Canva.""",
            output_type="text",
        ),
    ],
)
