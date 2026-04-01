from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="brand_voice",
    name="Brand Voice",
    description="Define, audit, and maintain your brand's communication style. Creates a voice document that ensures consistency across all outputs. Every other skill auto-injects your brand voice.",
    icon="mic",
    category="foundation",
    platforms=["claude", "openai"],
    tools_used=["qdrant"],
    workflow_stages=["audit", "define", "validate"],
    default_llm="claude",
    fallback_llms=["openai", "gemini"],
    prompts=[
        PromptTemplate(
            id="define_voice",
            name="Define Brand Voice",
            description="Create a brand voice document from scratch based on your company and audience.",
            variables=["company_name", "industry", "target_audience", "tone_keywords", "competitors"],
            platform="claude",
            agent="copy",
            prompt_text="""You are a brand strategist specializing in voice and tone architecture.

Create a comprehensive Brand Voice Document for {{company_name}} in the {{industry}} space.

Target audience: {{target_audience}}
Desired tone keywords: {{tone_keywords}}
Key competitors (to differentiate from): {{competitors}}

BRAND VOICE (if existing — refine, don't restart):
{{brand_voice_context}}

Your Brand Voice Document must include:

1. **Voice Pillars** (3-4 core attributes, e.g., "Bold but not aggressive")
   - Each pillar: definition + DO example + DON'T example

2. **Tone Spectrum**
   - How tone shifts across contexts: social (casual) → website (professional) → support (empathetic) → sales (confident)

3. **Vocabulary Rules**
   - Words we USE (with reasoning)
   - Words we NEVER use (with alternatives)
   - Jargon policy (when to use industry terms vs plain language)

4. **Sentence Style**
   - Average sentence length target
   - Active vs passive voice preference
   - Punctuation style (Oxford comma, em dashes, exclamation marks)

5. **Brand Personality**
   - "If our brand were a person, they would be..."
   - 3 adjectives that describe us / 3 that don't

Output: Complete Brand Voice Document in markdown.""",
            example_output="# Brand Voice Document\n\n## Voice Pillars\n1. **Confident, not arrogant** — We speak with authority...",
        ),
        PromptTemplate(
            id="audit_voice",
            name="Audit Existing Content",
            description="Analyze your existing content to extract and document your current brand voice.",
            variables=["content_samples"],
            platform="claude",
            agent="research",
            prompt_text="""You are a brand voice analyst. Analyze the following content samples and extract the brand voice patterns.

CONTENT SAMPLES:
{{content_samples}}

EXISTING BRAND MEMORY:
{{brand_examples}}

Analyze and report:

1. **Current Voice Profile**
   - Dominant tone (formal/casual/technical/conversational)
   - Sentence structure patterns
   - Vocabulary tendencies
   - Personality that comes through

2. **Consistency Score** (1-10)
   - How consistent is the voice across samples?
   - Which samples deviate and how?

3. **Strengths**
   - What's working well in the current voice?

4. **Gaps & Recommendations**
   - Where does the voice feel generic or AI-generated?
   - Specific improvements to make it more distinctive

5. **Extracted Voice Rules**
   - Draft voice rules based on what you observed

Output: Voice Audit Report in markdown.""",
            example_output="# Voice Audit Report\n\n## Current Profile\nTone: Professional-casual blend...",
        ),
        PromptTemplate(
            id="voice_check",
            name="Voice Consistency Check",
            description="Score a piece of content against your brand voice document.",
            variables=["content_to_check"],
            platform="any",
            agent="review",
            prompt_text="""You are a brand voice quality checker.

BRAND VOICE DOCUMENT:
{{brand_voice_context}}

CONTENT TO CHECK:
{{content_to_check}}

Score this content on brand voice alignment:

1. **Overall Score**: X/10
2. **Pillar Alignment**: Score each voice pillar (1-10)
3. **Vocabulary Compliance**: Any banned words used? Missing preferred terms?
4. **Tone Match**: Does the tone match the intended context?
5. **Specific Fixes**: Line-by-line suggestions where voice drifts

Output the scored report, then a REVISED version of the content with fixes applied.""",
            example_output="## Voice Check: 7/10\n\n### Pillar Scores\n- Confident: 8/10...",
        ),
    ],
)
