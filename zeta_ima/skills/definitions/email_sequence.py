from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="email_sequence",
    name="Email Sequences",
    description="Design and write complete email sequences — welcome, nurture, launch, win-back, and cart abandonment. Each sequence includes subject lines, preview text, and full body copy.",
    icon="mail",
    category="execution",
    platforms=["openai", "claude"],
    tools_used=["mailchimp", "sendgrid"],
    workflow_stages=["strategy", "draft", "subject_lines", "template", "preview", "upload"],
    default_llm="openai",
    fallback_llms=["claude", "gemini"],
    prompts=[
        PromptTemplate(
            id="welcome_series",
            name="Welcome Email Series (5 emails)",
            description="Onboarding sequence for new subscribers — builds trust and drives first conversion.",
            variables=["brand_name", "lead_magnet_topic", "core_offer", "target_audience"],
            platform="openai",
            agent="copy",
            prompt_text="""Write a 5-email Welcome Sequence.

BRAND: {{brand_name}}
LEAD MAGNET: {{lead_magnet_topic}}
CORE OFFER: {{core_offer}}
AUDIENCE: {{target_audience}}

{{brand_voice_context}}

**Email 1 — Delivery + Quick Win** (send immediately)
- Deliver the lead magnet
- One quick insight they can use today
- Set expectations for the sequence

**Email 2 — Story + Credibility** (Day 2)
- Origin story or "why we built this"
- Establish authority without bragging

**Email 3 — Value + Education** (Day 4)
- Teach something useful (related to lead magnet topic)
- Build "this brand gets me" feeling

**Email 4 — Social Proof + Soft CTA** (Day 6)
- Customer story or case study
- First mention of core offer (soft)

**Email 5 — Direct Offer** (Day 8)
- Clear pitch for {{core_offer}}
- Objection handling in copy
- Urgency element (honest)

For EACH email provide:
- Subject line (+ 2 A/B variants)
- Preview text (50 chars)
- Full body copy
- CTA button text
- Send timing + reasoning""",
        ),
        PromptTemplate(
            id="launch_sequence",
            name="Product Launch Sequence (7 emails)",
            description="Pre-launch → launch → urgency sequence for product or feature launches.",
            variables=["product_name", "launch_date", "offer_details", "target_segment", "urgency_mechanism"],
            platform="openai",
            agent="copy",
            prompt_text="""Write a 7-email Product Launch Sequence.

PRODUCT: {{product_name}}
LAUNCH DATE: {{launch_date}}
OFFER: {{offer_details}}
SEGMENT: {{target_segment}}
URGENCY: {{urgency_mechanism}}

{{brand_voice_context}}

**Pre-Launch (3 emails):**
Email 1 — Teaser / curiosity builder (7 days before)
Email 2 — Problem education + hint at solution (4 days before)
Email 3 — "Doors open tomorrow" anticipation (1 day before)

**Launch (2 emails):**
Email 4 — Launch announcement (launch day AM)
Email 5 — Social proof + FAQ (launch day +2)

**Urgency (2 emails):**
Email 6 — "48 hours left" + objection handling
Email 7 — "Final hours" + last chance

For EACH email:
- Subject line (+ 2 A/B variants)
- Preview text
- Full body copy
- CTA
- Send time""",
        ),
        PromptTemplate(
            id="nurture_sequence",
            name="Nurture Sequence (6 emails)",
            description="Long-term nurture for leads not ready to buy — builds trust over 30 days.",
            variables=["brand_name", "content_topics", "target_audience", "conversion_goal"],
            platform="claude",
            agent="copy",
            prompt_text="""Write a 6-email Nurture Sequence over 30 days.

BRAND: {{brand_name}}
TOPICS: {{content_topics}}
AUDIENCE: {{target_audience}}
GOAL: {{conversion_goal}}

{{brand_voice_context}}

Cadence: Every 5 days. Mix of value, story, and soft pitch.

Email 1 (Day 1) — Pure value. Teach something surprising.
Email 2 (Day 6) — Story. Customer journey or behind-the-scenes.
Email 3 (Day 11) — Curated resources. "3 things I found useful this week."
Email 4 (Day 16) — Contrarian take. Challenge a common assumption.
Email 5 (Day 21) — Case study. Specific results with details.
Email 6 (Day 26) — Direct ask. "Ready to [goal]? Here's how to start."

Rules:
- 80% value, 20% pitch (only emails 5 and 6 sell)
- Each email standalone (don't require reading previous)
- Conversational tone — like writing to a smart friend
- Short (200-400 words per email)

For EACH: Subject, preview text, full copy, CTA.""",
        ),
    ],
)
