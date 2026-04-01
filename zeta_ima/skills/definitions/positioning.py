from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="positioning",
    name="Positioning & Angles",
    description="Find differentiated hooks through competitive analysis. Uses 8 positioning frameworks to surface what makes your offering compelling and unique.",
    icon="target",
    category="foundation",
    platforms=["claude", "openai"],
    tools_used=["web_search"],
    workflow_stages=["research", "analyze", "position"],
    default_llm="claude",
    fallback_llms=["openai", "gemini"],
    prompts=[
        PromptTemplate(
            id="find_differentiators",
            name="Find Differentiators",
            description="Analyze your product against competitors to find unique positioning angles.",
            variables=["product_name", "product_description", "competitors", "target_audience"],
            platform="claude",
            agent="research",
            prompt_text="""You are a positioning strategist. Analyze {{product_name}} and find differentiated angles.

PRODUCT: {{product_description}}
COMPETITORS: {{competitors}}
TARGET AUDIENCE: {{target_audience}}

KNOWLEDGE BASE CONTEXT:
{{kb_context}}

Apply these 8 positioning frameworks:

1. **Category Creation** — Can we define a new category? (e.g., "AI Marketing Agency" vs "Marketing Tool")
2. **Against the Leader** — How do we position against the market leader?
3. **Niche Focus** — What underserved niche can we own?
4. **Feature Superiority** — What feature do we do 10x better?
5. **Price/Value** — Where do we sit on the value spectrum?
6. **Use Case** — What specific job-to-be-done do we nail?
7. **Audience Identity** — Who is our "people like us" audience?
8. **Enemy Positioning** — What are we fighting against? (status quo, incumbent, old way)

For each framework:
- Score: Viable (1-5) / Impact (1-5)
- One-line positioning statement
- Key proof point

RECOMMENDATION: Top 3 angles ranked, with reasoning.

Output: Positioning Analysis Report.""",
        ),
        PromptTemplate(
            id="competitive_analysis",
            name="Competitive Landscape Analysis",
            description="Deep dive into competitor positioning, messaging, and gaps.",
            variables=["competitors", "our_product"],
            platform="claude",
            agent="research",
            prompt_text="""You are a competitive intelligence analyst.

OUR PRODUCT: {{our_product}}
COMPETITORS TO ANALYZE: {{competitors}}

KNOWLEDGE BASE:
{{kb_context}}

For each competitor, analyze:
1. **Positioning Statement** — What category do they claim? What's their tagline?
2. **Messaging Themes** — Top 3 themes in their marketing
3. **Target Audience** — Who are they going after?
4. **Pricing Model** — How do they charge?
5. **Strengths** — What do they do well?
6. **Weaknesses** — Where do they fall short?
7. **Content Strategy** — What channels do they invest in?

Then create:
- **Positioning Map**: 2x2 matrix (choose the most meaningful axes)
- **Gap Analysis**: What opportunities do competitors miss?
- **Recommended Counter-Positioning**: How to position against each

Output: Competitive Landscape Report.""",
        ),
        PromptTemplate(
            id="unique_angles",
            name="Unique Angle Generator",
            description="Generate 10 unique content angles based on your positioning.",
            variables=["positioning_statement", "target_audience", "content_goal"],
            platform="any",
            agent="copy",
            prompt_text="""You are a creative strategist who finds non-obvious content angles.

POSITIONING: {{positioning_statement}}
AUDIENCE: {{target_audience}}
GOAL: {{content_goal}}

BRAND VOICE:
{{brand_voice_context}}

Generate 10 unique content angles. For each:
1. **Angle Title** (compelling, specific)
2. **Hook** (opening line that stops the scroll)
3. **Core Argument** (the insight or contrarian take)
4. **Format** (blog, LinkedIn post, video, infographic, thread)
5. **Estimated Impact** (awareness / leads / authority — pick one)

Rules:
- No generic angles ("5 tips for X" is banned)
- At least 3 must be contrarian or counterintuitive
- At least 2 must reference real data/trends
- At least 1 must be a story-driven angle""",
        ),
    ],
)
