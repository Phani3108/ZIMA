from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="ad_creative",
    name="Ad Creative",
    description="Generate ad copy and creative briefs for Facebook, Google, LinkedIn, and display ads. Includes A/B variant generation and creative brief for designers.",
    icon="zap",
    category="execution",
    platforms=["openai", "gemini"],
    tools_used=["canva", "dalle"],
    workflow_stages=["audience_research", "copy_variants", "creative_brief", "generate_visuals", "preview"],
    default_llm="openai",
    fallback_llms=["gemini", "claude"],
    prompts=[
        PromptTemplate(
            id="facebook_ad",
            name="Facebook/Instagram Ad Set",
            description="3 ad variants with primary text, headline, description, and image brief.",
            variables=["product_name", "target_audience", "key_benefit", "landing_page_url", "ad_objective"],
            platform="openai",
            agent="copy",
            prompt_text="""Write 3 Facebook/Instagram ad variants for {{product_name}}.

AUDIENCE: {{target_audience}}
BENEFIT: {{key_benefit}}
LANDING PAGE: {{landing_page_url}}
OBJECTIVE: {{ad_objective}}

{{brand_voice_context}}

For each of the 3 variants, provide:

**Primary Text** (125 chars max for display, full text up to 500)
**Headline** (40 chars max)
**Description** (30 chars max)
**CTA Button**: Choose from (Learn More, Sign Up, Get Offer, Shop Now, Download)
**[IMAGE BRIEF]**: Describe the ideal ad image (for Canva/DALL-E generation)

Variant strategy:
- Variant A: Benefit-led (direct value proposition)
- Variant B: Problem-led (agitate the pain → solution)
- Variant C: Social proof-led (results/testimonials)

Rules:
- No clickbait or misleading claims
- Each variant tests a different angle (not just word swaps)
- Mobile-first (most impressions are mobile)
- Include emoji sparingly (1-2 max per ad)""",
        ),
        PromptTemplate(
            id="google_ads",
            name="Google Search Ads",
            description="Responsive search ad components — 15 headlines + 4 descriptions.",
            variables=["product_name", "target_keywords", "key_benefits", "landing_page_url"],
            platform="openai",
            agent="copy",
            prompt_text="""Write Google Responsive Search Ad components.

PRODUCT: {{product_name}}
KEYWORDS: {{target_keywords}}
BENEFITS: {{key_benefits}}
LANDING PAGE: {{landing_page_url}}

Generate:

**15 Headlines** (30 chars max each)
- At least 5 must include a target keyword
- At least 3 must include a number or stat
- At least 2 must include a CTA verb
- Mix: benefit, feature, urgency, trust, question

**4 Descriptions** (90 chars max each)
- Description 1: Value proposition + CTA
- Description 2: Features + differentiator
- Description 3: Social proof / trust signal
- Description 4: Urgency / special offer

**Sitelink Extensions** (4)
- Each: headline (25 chars) + description (35 chars x2)

**Callout Extensions** (6)
- 25 chars max each

Pin recommendations (which headlines/descriptions to pin to positions).""",
        ),
        PromptTemplate(
            id="ad_image_prompt",
            name="Ad Image Generation Prompt",
            description="Generate DALL-E / Midjourney prompts for ad visuals.",
            variables=["product_name", "ad_concept", "brand_colors", "style_preference"],
            platform="openai",
            agent="design",
            output_type="image",
            prompt_text="""Generate 5 image generation prompts for ad creative.

PRODUCT: {{product_name}}
CONCEPT: {{ad_concept}}
BRAND COLORS: {{brand_colors}}
STYLE: {{style_preference}}

For each prompt:
1. **DALL-E Prompt** (detailed, specific, 100-200 words)
2. **Aspect Ratio**: 1:1 (feed) or 9:16 (stories) or 16:9 (landscape)
3. **Text Overlay Zone**: Where to place text (top/center/bottom)
4. **Usage**: Which ad placement this is for

Rules:
- No text in generated images (text will be overlaid in Canva)
- Photorealistic or illustration style based on preference
- Include negative prompts (what to avoid)
- Brand-safe: no controversial imagery""",
        ),
    ],
)
