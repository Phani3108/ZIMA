from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="landing_page",
    name="Landing Page",
    description="Design and write complete landing pages — full-page copy with layout, A/B variants, and hero section optimization. Outputs include design briefs for Canva/Figma.",
    icon="layout",
    category="execution",
    platforms=["claude", "openai"],
    tools_used=["canva", "figma"],
    workflow_stages=["wireframe", "copy", "design", "preview", "review"],
    default_llm="claude",
    fallback_llms=["openai", "gemini"],
    prompts=[
        PromptTemplate(
            id="full_landing_page",
            name="Full Landing Page",
            description="Complete landing page with wireframe, copy, and design notes.",
            variables=["product_name", "target_audience", "primary_cta", "key_benefit", "price_point"],
            platform="claude",
            agent="copy",
            output_type="html",
            prompt_text="""Design and write a complete Landing Page.

PRODUCT: {{product_name}}
AUDIENCE: {{target_audience}}
CTA: {{primary_cta}}
BENEFIT: {{key_benefit}}
PRICE: {{price_point}}

{{brand_voice_context}}
{{brand_examples}}

Output a complete landing page with sections clearly labeled:

**[SECTION: Hero]**
- Headline (10 words max, benefit-led)
- Subheadline (20 words, expand the promise)
- CTA button: {{primary_cta}}
- [IMAGE: hero image description]
- Trust badges / "as seen in" logos

**[SECTION: Problem]**
- "Are you struggling with..." (3 pain points)

**[SECTION: Solution]**
- Product introduction (bridge from problem)
- 3 benefit blocks (icon + headline + description)

**[SECTION: How It Works]**
- Step 1 → Step 2 → Step 3 (simple)

**[SECTION: Features]**
- 6 features in 2-column grid (headline + 1-sentence description)

**[SECTION: Social Proof]**
- 3 testimonials (or templates)
- Results numbers (3 metrics with large numbers)

**[SECTION: Pricing]**
- Price with value anchoring
- What's included (checklist)
- Guarantee

**[SECTION: FAQ]**
- 6 questions addressing common objections

**[SECTION: Final CTA]**
- Headline restating key benefit
- CTA button
- "No credit card required" / risk reversal

Include [DESIGN: note] annotations throughout for designer.""",
        ),
        PromptTemplate(
            id="ab_variant",
            name="A/B Test Variants",
            description="Generate A/B test variants for a landing page hero section.",
            variables=["current_headline", "current_subheadline", "product_name", "target_audience"],
            platform="any",
            agent="copy",
            prompt_text="""Create 5 A/B test variants for a landing page hero.

CURRENT HEADLINE: {{current_headline}}
CURRENT SUBHEADLINE: {{current_subheadline}}
PRODUCT: {{product_name}}
AUDIENCE: {{target_audience}}

{{brand_voice_context}}

For each variant:
1. **Headline** (different angle/approach)
2. **Subheadline** (supports the new headline)
3. **CTA Button Text** (matches the new framing)
4. **Hypothesis** (why this might outperform — what psychological lever it pulls)
5. **Test Priority** (1-5, based on expected impact)

Variant strategies:
- Variant A: Benefit-focused (what they get)
- Variant B: Problem-focused (what they escape)
- Variant C: Social proof-focused (what others achieved)
- Variant D: Curiosity-focused (what they'll discover)
- Variant E: Urgency-focused (why now)""",
        ),
    ],
)
