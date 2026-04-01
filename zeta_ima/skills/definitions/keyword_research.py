from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="keyword_research",
    name="Keyword Research",
    description="Strategic keyword and topic research using the 6 Circles Method. Identifies what content to create, prioritizes topics, and builds content clusters — without expensive SEO tools.",
    icon="search",
    category="foundation",
    platforms=["openai", "gemini"],
    tools_used=["semrush", "web_search"],
    workflow_stages=["research", "cluster", "prioritize"],
    default_llm="openai",
    fallback_llms=["gemini", "claude"],
    prompts=[
        PromptTemplate(
            id="six_circles",
            name="6 Circles Keyword Method",
            description="Comprehensive keyword research using 6 audience intent circles.",
            variables=["business_type", "core_offering", "target_audience", "competitors"],
            platform="openai",
            agent="seo",
            prompt_text="""You are an SEO strategist using the 6 Circles Method for keyword research.

BUSINESS: {{business_type}}
CORE OFFERING: {{core_offering}}
AUDIENCE: {{target_audience}}
COMPETITORS: {{competitors}}

Apply the 6 Circles Method:

**Circle 1 — Problem Aware** (audience knows they have a problem)
- 10 keywords people search when they first realize the problem
- Example: "why is my marketing not working"

**Circle 2 — Solution Aware** (they know solutions exist)
- 10 keywords for people comparing solution types
- Example: "marketing automation vs agency"

**Circle 3 — Product Aware** (they know your product category)
- 10 keywords for people evaluating specific products
- Example: "best AI marketing tools 2026"

**Circle 4 — Brand Aware** (they know your brand)
- 10 branded/comparison keywords
- Example: "{{core_offering}} vs [competitor]"

**Circle 5 — Adjacent Topics** (related but not direct)
- 10 keywords for topics your audience cares about beyond your product
- Example: "content marketing trends"

**Circle 6 — Long-tail Gold** (low competition, high intent)
- 10 highly specific long-tail keywords
- Example: "AI tool to write LinkedIn posts for B2B SaaS"

For each keyword:
- Estimated search intent (informational / navigational / commercial / transactional)
- Content format recommendation (blog / landing page / video / tool)
- Priority score (1-5 based on business impact + feasibility)

Output: Organized keyword map with 60 keywords across 6 circles.""",
        ),
        PromptTemplate(
            id="topic_clusters",
            name="Topic Cluster Builder",
            description="Build SEO topic clusters with pillar pages and supporting content.",
            variables=["primary_topic", "business_context", "existing_content"],
            platform="openai",
            agent="seo",
            prompt_text="""You are an SEO content architect. Build a topic cluster strategy.

PRIMARY TOPIC: {{primary_topic}}
BUSINESS: {{business_context}}
EXISTING CONTENT (if any): {{existing_content}}

KNOWLEDGE BASE:
{{kb_context}}

Create a Topic Cluster with:

1. **Pillar Page** (comprehensive guide, 3000+ words)
   - Title, URL slug, target keyword
   - H2 outline (8-12 sections)

2. **Cluster Content** (10-15 supporting articles)
   For each:
   - Title + target keyword
   - Relationship to pillar (subtopic / use case / FAQ / comparison)
   - Word count target
   - Internal link to pillar (which section)

3. **Content Calendar**
   - Recommended publish order (build authority progressively)
   - 1 pillar + 3 cluster pieces per month cadence

4. **Interlinking Map**
   - How all pieces connect to each other (not just to pillar)

Output: Complete Topic Cluster Plan.""",
        ),
        PromptTemplate(
            id="content_gap",
            name="Content Gap Analysis",
            description="Find content opportunities your competitors rank for but you don't.",
            variables=["our_domain", "competitor_domains", "target_topics"],
            platform="gemini",
            agent="seo",
            prompt_text="""You are an SEO competitive analyst. Identify content gaps.

OUR DOMAIN: {{our_domain}}
COMPETITOR DOMAINS: {{competitor_domains}}
TARGET TOPICS: {{target_topics}}

Analyze and identify:

1. **Keywords competitors rank for that we don't**
   - Group by topic cluster
   - Estimate traffic potential (high/medium/low)

2. **Content types competitors have that we lack**
   - Comparison pages, tool pages, glossary, templates, etc.

3. **SERP features competitors capture**
   - Featured snippets, People Also Ask, video carousels

4. **Quick wins** (top 10 opportunities ranked by effort vs impact)
   For each: keyword, competitor ranking, content type needed, estimated effort

5. **Strategic gaps** (longer-term opportunities)
   - Topics no competitor covers well yet

Output: Content Gap Report with prioritized action items.""",
        ),
    ],
)
