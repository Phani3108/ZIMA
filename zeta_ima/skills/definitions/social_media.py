from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="social_media",
    name="Social Media",
    description="Create platform-native social content — LinkedIn posts, Twitter threads, Instagram captions, and carousels. Each prompt adapts tone and format to the platform's norms.",
    icon="share-2",
    category="execution",
    platforms=["openai", "claude"],
    tools_used=["canva", "buffer"],
    workflow_stages=["research", "draft", "design", "preview", "schedule"],
    default_llm="openai",
    fallback_llms=["claude", "gemini"],
    prompts=[
        PromptTemplate(
            id="linkedin_post",
            name="LinkedIn Post",
            description="Professional LinkedIn post with hook, insight, and CTA.",
            variables=["topic", "key_insight", "target_audience", "cta_goal"],
            platform="any",
            agent="copy",
            prompt_text="""Write a LinkedIn post about {{topic}} for {{target_audience}}.

KEY INSIGHT: {{key_insight}}
CTA GOAL: {{cta_goal}}

{{brand_voice_context}}
{{brand_examples}}

Structure:
- **Line 1**: Hook (pattern interrupt — question, bold claim, or surprising stat)
- **Line 2**: Empty line (creates "see more" break)
- **Body**: 3-5 short paragraphs building the insight
  - Use line breaks between paragraphs
  - Include one specific example or data point
  - One contrarian or non-obvious take
- **CTA**: Clear ask (comment, share, check link in comments)
- **Hashtags**: Max 3, relevant

Rules:
- 150-250 words (LinkedIn sweet spot)
- No "I'm excited to announce" or "I'm thrilled"
- No emoji spam
- Write like a human, not a corporate account
- First-person, conversational
- Provide 3 VARIANTS with different hooks""",
        ),
        PromptTemplate(
            id="twitter_thread",
            name="Twitter/X Thread",
            description="Engaging thread (5-10 tweets) that builds an argument or tells a story.",
            variables=["topic", "key_argument", "supporting_points"],
            platform="any",
            agent="copy",
            prompt_text="""Write a Twitter/X thread about {{topic}}.

ARGUMENT: {{key_argument}}
SUPPORTING POINTS: {{supporting_points}}

{{brand_voice_context}}

Thread structure (8-10 tweets):

**Tweet 1 (Hook)**: Bold claim or question. Must stop the scroll. End with ↓
**Tweet 2-3**: Setup the problem or context
**Tweet 4-6**: Key insights/points (one per tweet)
**Tweet 7-8**: Example or proof
**Tweet 9**: Summary / takeaway
**Tweet 10**: CTA (follow, retweet, check link)

Rules:
- Each tweet: max 280 chars
- Each tweet must stand alone AND flow in sequence
- Use numbers: "1/10", "2/10", etc.
- No hashtags in thread (only in last tweet if any)
- Conversational, punchy, opinionated
- Include one "quotable" tweet that works as a standalone""",
        ),
        PromptTemplate(
            id="instagram_carousel",
            name="Instagram Carousel Script",
            description="Carousel post (8-10 slides) with headline + body per slide — ready for Canva design.",
            variables=["topic", "target_audience", "brand_style"],
            platform="any",
            agent="copy",
            output_type="json",
            prompt_text="""Write an Instagram Carousel about {{topic}} for {{target_audience}}.

BRAND STYLE: {{brand_style}}

{{brand_voice_context}}

Create a 10-slide carousel:

**Slide 1 (Cover)**: Bold headline (5-7 words max). Subtext: "Swipe →"
**Slide 2**: Problem statement (relatable)
**Slide 3-8**: One key point per slide
  - Headline: 3-5 words (large text)
  - Body: 1-2 sentences (small text)
  - Each slide self-contained but builds the story
**Slide 9**: Summary / recap of all points
**Slide 10**: CTA slide — "Save this for later" / "Follow for more"

Also provide:
- Caption (150-200 words, with line breaks)
- 5 relevant hashtags (mix of broad + niche)
- [DESIGN NOTE: color/style guidance for each slide]

Output as JSON: {"slides": [{"headline": "...", "body": "...", "design_note": "..."}], "caption": "...", "hashtags": [...]}""",
        ),
        PromptTemplate(
            id="social_calendar",
            name="Weekly Social Calendar",
            description="Plan a week of social content across platforms.",
            variables=["platforms", "content_themes", "campaign_goal", "posting_frequency"],
            platform="any",
            agent="copy",
            prompt_text="""Create a weekly social media content calendar.

PLATFORMS: {{platforms}}
THEMES: {{content_themes}}
GOAL: {{campaign_goal}}
FREQUENCY: {{posting_frequency}}

{{brand_voice_context}}

For each day, provide:
| Day | Platform | Content Type | Topic/Hook | Goal | Draft Copy |

Include:
- Mix of content types (educational, entertaining, promotional, engagement)
- Best posting times per platform
- One "hero" post per week (highest effort, highest potential)
- One engagement-focused post (poll, question, discussion)
- Cross-platform synergy (how posts reference each other)

Rules:
- No more than 20% promotional content
- Each post has a clear purpose
- Variety in format (text, image, carousel, video concept)""",
        ),
    ],
)
