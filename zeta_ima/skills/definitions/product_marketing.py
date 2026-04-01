from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="product_marketing",
    name="Product Marketing",
    description="Create messaging frameworks, launch briefs, battlecards, and enablement docs. Bridges product and marketing with structured deliverables.",
    icon="package",
    category="strategy",
    platforms=["claude", "openai"],
    tools_used=["confluence", "jira"],
    workflow_stages=["research", "messaging", "collateral", "review", "distribute"],
    default_llm="claude",
    fallback_llms=["openai", "gemini"],
    prompts=[
        PromptTemplate(
            id="messaging_framework",
            name="Messaging Framework",
            description="Build a structured messaging hierarchy — positioning, value props, proof points.",
            variables=["product_name", "target_personas", "key_differentiators", "competitors"],
            platform="claude",
            agent="copy",
            prompt_text="""You are a product marketing strategist. Create a Messaging Framework.

PRODUCT: {{product_name}}
TARGET PERSONAS: {{target_personas}}
DIFFERENTIATORS: {{key_differentiators}}
COMPETITORS: {{competitors}}

{{brand_voice_context}}
{{kb_context}}

**MESSAGING HIERARCHY:**

1. **Positioning Statement** (1 sentence — category, target, differentiation, reason to believe)

2. **Value Propositions** (3 pillars)
   For each pillar:
   - Headline (benefit-led, 8 words max)
   - Supporting statement (1-2 sentences)
   - Proof point (data, customer quote, or feature)

3. **Persona-Specific Messages**
   For each persona in {{target_personas}}:
   - Pain point they care most about
   - Tailored headline
   - Key objection + response

4. **Elevator Pitches**
   - 15-second version
   - 30-second version
   - 60-second version

5. **Tagline Options** (5 candidates, ranked)

6. **Messaging Don'ts** — What to avoid saying and why""",
        ),
        PromptTemplate(
            id="launch_brief",
            name="Product Launch Brief",
            description="Complete launch brief with timeline, channels, assets needed, and success metrics.",
            variables=["product_name", "launch_date", "target_audience", "key_message", "budget_level"],
            platform="claude",
            agent="copy",
            prompt_text="""Create a Product Launch Brief.

PRODUCT: {{product_name}}
LAUNCH DATE: {{launch_date}}
AUDIENCE: {{target_audience}}
KEY MESSAGE: {{key_message}}
BUDGET: {{budget_level}}

{{brand_voice_context}}

**LAUNCH BRIEF:**

1. **Executive Summary** (3 sentences)
2. **Goals & KPIs**
   - Primary goal + metric
   - Secondary goals + metrics
3. **Audience Segments** (prioritized)
4. **Key Messaging** (per segment)
5. **Channel Strategy**
   | Channel | Role | Asset Needed | Owner | Due Date |
6. **Content Calendar** (week-by-week, 4 weeks pre + 2 weeks post)
7. **Asset Checklist**
   - [ ] Landing page
   - [ ] Email sequence
   - [ ] Social posts
   - [ ] Press release
   - [ ] Internal enablement doc
   - [ ] Demo/video
8. **Risk Mitigation** — What could go wrong + contingency
9. **Success Criteria** — How we'll evaluate at 30/60/90 days""",
        ),
    ],
)
