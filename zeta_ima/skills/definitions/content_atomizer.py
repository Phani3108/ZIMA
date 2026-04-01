from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="content_atomizer",
    name="Content Atomizer",
    description="Transform a single piece of content into 15+ platform-specific assets. Extract hooks, quotes, threads, carousels, and scripts from blogs, videos, or podcasts.",
    icon="split",
    category="distribution",
    platforms=["claude", "openai"],
    tools_used=["canva", "buffer"],
    workflow_stages=["analyze", "atomize", "design", "preview", "schedule"],
    default_llm="claude",
    fallback_llms=["openai", "gemini"],
    prompts=[
        PromptTemplate(
            id="blog_to_15",
            name="Blog → 15+ Assets",
            description="Convert one blog post into 15+ platform-specific content pieces.",
            variables=["source_content", "target_platforms"],
            platform="claude",
            agent="copy",
            prompt_text="""You are a content distribution specialist.

SOURCE CONTENT:
{{source_content}}

TARGET PLATFORMS: {{target_platforms}}

{{brand_voice_context}}

Transform this content into ALL of the following:

1. **LinkedIn post** — Hook + key insight + CTA (150-250 words)
2. **Twitter/X thread** — 5-8 tweets, numbered, with hook opener
3. **Instagram carousel** — 8-10 slides (headline + body per slide)
4. **Email newsletter snippet** — 3 paragraphs + CTA
5. **LinkedIn carousel** — 8 slides (different angle than IG carousel)
6. **Pull quotes** — 3 standalone quotes for social graphics [DESIGN: send to Canva]
7. **YouTube Shorts / TikTok script** — 60-second spoken script
8. **Podcast talking points** — 5 bullet points for discussion
9. **Reddit post** — Educational, no self-promo feel, authentic tone
10. **Quora answer template** — Answer format for relevant questions
11. **Newsletter subject lines** — 5 variants
12. **Meta description** — SEO-optimized, 155 chars
13. **Tweet-sized summary** — Single tweet capturing the core insight
14. **Slack/Teams announcement** — For internal sharing
15. **Press release paragraph** — If newsworthy

For each asset:
- Adapt tone to platform norms
- Maintain {{brand_voice_context}} throughout
- Include relevant hooks and CTAs per platform
- Mark any that need visual design with [DESIGN NEEDED]""",
        ),
        PromptTemplate(
            id="repurpose_video",
            name="Video → Content Pieces",
            description="Extract content pieces from a video transcript.",
            variables=["transcript", "video_title", "target_platforms"],
            platform="claude",
            agent="copy",
            prompt_text="""Extract marketing content from this video transcript.

VIDEO: {{video_title}}
TRANSCRIPT:
{{transcript}}

PLATFORMS: {{target_platforms}}

{{brand_voice_context}}

Generate:
1. **Blog post** (1500-2000 words, structured with H2/H3)
2. **Key quotes** (10 quotable moments with timestamps)
3. **Twitter thread** (8-10 tweets from the best insights)
4. **LinkedIn post** (personal reflection on the topic)
5. **Social clips list** (5 clip suggestions with start/end timestamps + hook text)
6. **Newsletter** (400-word summary with personal commentary)
7. **Slide deck outline** (for repurposing as a presentation)

Rules:
- Don't just summarize — extract the most interesting/contrarian points
- Each piece should stand alone
- Add context that video viewers would have but readers won't""",
        ),
    ],
)
