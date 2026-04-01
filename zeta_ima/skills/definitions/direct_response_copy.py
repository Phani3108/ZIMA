from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="direct_response_copy",
    name="Direct Response Copy",
    description="Craft high-converting landing pages, sales pages, VSL scripts, and headlines using proven persuasion frameworks from Ogilvy, Schwartz, Halbert, and Hopkins.",
    icon="pen-tool",
    category="execution",
    platforms=["openai", "claude"],
    tools_used=[],
    workflow_stages=["research", "draft", "review", "optimize"],
    default_llm="openai",
    fallback_llms=["claude", "gemini"],
    prompts=[
        PromptTemplate(
            id="landing_page_copy",
            name="Landing Page Copy",
            description="Full landing page with hero, benefits, social proof, FAQ, and CTA.",
            variables=["product_name", "target_audience", "key_benefit", "price_point", "social_proof"],
            platform="openai",
            agent="copy",
            prompt_text="""You are a senior direct response copywriter trained in the methods of David Ogilvy, Eugene Schwartz, and Gary Halbert.

Write complete landing page copy for {{product_name}}.

TARGET: {{target_audience}}
KEY BENEFIT: {{key_benefit}}
PRICE: {{price_point}}
SOCIAL PROOF: {{social_proof}}

BRAND VOICE:
{{brand_voice_context}}

APPROVED EXAMPLES:
{{brand_examples}}

Structure:
1. **Hero Section**
   - Headline (Schwartz-style — match awareness level)
   - Subheadline (expand the promise)
   - CTA button text
   - Hero image description [IMAGE: ...]

2. **Problem Agitation**
   - 3 pain points (specific, emotional)
   - "Sound familiar?" bridge

3. **Solution Introduction**
   - Position product as the bridge from pain → desired state
   - 3 key benefits with supporting details

4. **How It Works** (3 steps)

5. **Social Proof Block**
   - 3 testimonials (or templates if none provided)
   - Logos / numbers / trust signals

6. **Feature Deep-Dive** (5-7 features)
   - Feature → Benefit → Proof format

7. **Objection Handling / FAQ** (5-7 questions)

8. **Final CTA**
   - Urgency element (honest, not fake)
   - Risk reversal (guarantee)
   - Button text + supporting copy

Rules:
- No hyperbole or unsubstantiated claims
- Every benefit has a proof point
- Write at a 7th-grade reading level
- CTA above the fold AND at bottom""",
        ),
        PromptTemplate(
            id="headline_variants",
            name="Headline Variants",
            description="Generate 20 headline variations using different copywriting frameworks.",
            variables=["product_name", "key_benefit", "target_audience"],
            platform="any",
            agent="copy",
            prompt_text="""Generate 20 headlines for {{product_name}} targeting {{target_audience}}.

KEY BENEFIT: {{key_benefit}}

{{brand_voice_context}}

Use these frameworks (at least 2 headlines per framework):

1. **How-to**: "How to [achieve benefit] without [pain]"
2. **Question**: "Are you still [doing painful thing]?"
3. **Number**: "[N] ways to [benefit] in [timeframe]"
4. **Testimonial-style**: "I [achieved result] in [timeframe]. Here's how."
5. **Curiosity gap**: "The [unexpected thing] that [result]"
6. **Direct benefit**: "[Benefit]. [Proof point]. [CTA]."
7. **Before/After**: "From [pain state] to [desired state]"
8. **Contrarian**: "Why [common advice] is wrong"
9. **Specificity**: "The exact [system/method] that [specific result]"
10. **Social proof**: "[N] [audience] already [achieving result]"

For each headline:
- Score: Click-worthiness (1-10)
- Best channel: (landing page / ad / email subject / social)

RECOMMENDATION: Top 5 ranked with reasoning.""",
        ),
        PromptTemplate(
            id="vsl_script",
            name="Video Sales Letter Script",
            description="Write a VSL script (5-15 min) following the problem-agitate-solve structure.",
            variables=["product_name", "target_audience", "core_problem", "solution", "price_point", "guarantee"],
            platform="openai",
            agent="copy",
            prompt_text="""Write a Video Sales Letter (VSL) script.

PRODUCT: {{product_name}}
AUDIENCE: {{target_audience}}
PROBLEM: {{core_problem}}
SOLUTION: {{solution}}
PRICE: {{price_point}}
GUARANTEE: {{guarantee}}

{{brand_voice_context}}

Structure (aim for 8-12 minute read):

**[0:00 - 0:30] HOOK** — Pattern interrupt, bold claim or question

**[0:30 - 2:00] PROBLEM** — Specific, relatable pain. "If you're like most..."

**[2:00 - 3:00] AGITATE** — Consequences of not solving. Emotional weight.

**[3:00 - 4:00] CREDIBILITY** — Why should they listen to you?

**[4:00 - 6:00] SOLUTION** — Introduce the product. Show the transformation.

**[6:00 - 8:00] PROOF** — Results, testimonials, data, demonstrations.

**[8:00 - 9:00] OFFER** — What they get. Stack the value.

**[9:00 - 10:00] PRICE REVEAL** — Anchor high, reveal actual price, justify value.

**[10:00 - 11:00] GUARANTEE** — Remove risk.

**[11:00 - 12:00] CTA** — Tell them exactly what to do. Urgency.

**[12:00] CLOSE** — Final emotional note.

Include [VISUAL: description] cues for video production.
Write in conversational, spoken-word style — not written style.""",
        ),
        PromptTemplate(
            id="sales_email",
            name="Sales Page Email",
            description="Write a long-form sales email that can stand alone as a conversion piece.",
            variables=["product_name", "recipient_segment", "key_benefit", "offer_details"],
            platform="any",
            agent="copy",
            prompt_text="""Write a direct response sales email.

PRODUCT: {{product_name}}
SEGMENT: {{recipient_segment}}
BENEFIT: {{key_benefit}}
OFFER: {{offer_details}}

{{brand_voice_context}}

Structure:
1. **Subject Line** (5 options, ranked by open rate potential)
2. **Preview Text** (50 chars max)
3. **Opening Hook** (personal, specific, no "Dear" or "I hope this finds you")
4. **Problem Statement** (1-2 paragraphs)
5. **Solution Bridge** (introduce product naturally)
6. **3 Key Benefits** (bullet points with proof)
7. **Social Proof** (testimonial or result)
8. **The Offer** (what they get, deadline if applicable)
9. **CTA** (one clear action, repeated 2x in email)
10. **P.S. Line** (always include — most-read part of any email)

Rules:
- Short paragraphs (1-3 sentences max)
- Conversational tone
- No walls of text
- Mobile-friendly (short lines)""",
        ),
    ],
)
