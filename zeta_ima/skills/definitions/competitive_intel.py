from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="competitive_intel",
    name="Competitive Intelligence",
    description="Monitor competitors, analyze positioning shifts, and generate actionable intelligence reports. Feeds insights into all other skills.",
    icon="eye",
    category="strategy",
    platforms=["claude", "gemini"],
    tools_used=["web_search", "confluence"],
    workflow_stages=["monitor", "analyze", "report", "distribute"],
    default_llm="claude",
    fallback_llms=["gemini", "openai"],
    prompts=[
        PromptTemplate(
            id="competitor_scan",
            name="Competitor Scan",
            description="Comprehensive scan of competitor activity — messaging, content, product changes.",
            variables=["competitors", "focus_areas", "time_period"],
            platform="claude",
            agent="research",
            prompt_text="""You are a competitive intelligence analyst. Conduct a thorough scan.

COMPETITORS: {{competitors}}
FOCUS AREAS: {{focus_areas}}
TIME PERIOD: {{time_period}}

KNOWLEDGE BASE (past intel):
{{kb_context}}

For each competitor, investigate and report:

1. **Messaging Changes** — Any new taglines, positioning shifts, or narrative changes?
2. **Product Updates** — New features, pricing changes, or product launches?
3. **Content Activity** — Recent blog posts, whitepapers, webinars, social campaigns?
4. **Hiring Signals** — Key roles they're hiring for (indicates strategic direction)?
5. **Customer Sentiment** — Review site trends (G2, Capterra, Reddit mentions)?
6. **Partnerships/Funding** — New alliances, acquisitions, or funding rounds?

**Summary Grid:**
| Competitor | Key Move | Threat Level | Our Response |
|---|---|---|---|

**Top 3 Actionable Insights** — what should we do differently based on this scan?""",
        ),
        PromptTemplate(
            id="swot_analysis",
            name="SWOT Analysis",
            description="Generate a SWOT analysis comparing your product to a specific competitor.",
            variables=["our_product", "competitor_product", "market_context"],
            platform="claude",
            agent="research",
            prompt_text="""Create a detailed SWOT analysis.

OUR PRODUCT: {{our_product}}
COMPETITOR: {{competitor_product}}
MARKET: {{market_context}}

{{kb_context}}

**STRENGTHS** (our advantages over this competitor)
- 5-7 specific strengths with evidence

**WEAKNESSES** (where competitor beats us)
- 5-7 specific weaknesses, honestly assessed

**OPPORTUNITIES** (market gaps we can exploit)
- 5-7 opportunities with recommended actions

**THREATS** (risks from this competitor + market)
- 5-7 threats with mitigation strategies

**Strategic Recommendation**: Top 3 priorities based on this SWOT.""",
        ),
        PromptTemplate(
            id="battlecard",
            name="Sales Battlecard",
            description="Create a competitive battlecard for sales teams.",
            variables=["our_product", "competitor", "target_buyer"],
            platform="claude",
            agent="copy",
            prompt_text="""Create a Sales Battlecard for use against {{competitor}}.

OUR PRODUCT: {{our_product}}
TARGET BUYER: {{target_buyer}}

{{kb_context}}
{{brand_voice_context}}

Format as a one-page battlecard:

**Quick Summary** (2 sentences — why we win)

**Positioning** (how to frame the conversation)

**Key Differentiators** (3-5 with proof points)
| Feature | Us | Them | Talk Track |

**Common Objections & Responses**
- "But [competitor] has X..." → Response
- "They're cheaper..." → Response
- "They have more customers..." → Response

**Landmines to Set** (questions to ask the prospect that expose competitor weaknesses)

**Trap Questions** (questions competitor might prompt — and how to handle them)

**Win Story** (1 paragraph customer story of someone who chose us over them)""",
        ),
    ],
)
