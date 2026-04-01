from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="newsletter",
    name="Newsletter",
    description="Write engaging newsletters in 9 distinct formats — from curated roundups to story-driven deep dives. Transform existing content into subscriber touchpoints.",
    icon="newspaper",
    category="execution",
    platforms=["claude", "openai"],
    tools_used=[],
    workflow_stages=["topic", "draft", "review"],
    default_llm="claude",
    fallback_llms=["openai", "gemini"],
    prompts=[
        PromptTemplate(
            id="curated_roundup",
            name="Curated Roundup Newsletter",
            description="Weekly roundup of industry links, insights, and commentary.",
            variables=["newsletter_name", "topic_focus", "links_and_summaries", "personal_take"],
            platform="claude",
            agent="copy",
            prompt_text="""Write a Curated Roundup Newsletter.

NEWSLETTER: {{newsletter_name}}
TOPIC: {{topic_focus}}
LINKS: {{links_and_summaries}}
YOUR TAKE: {{personal_take}}

{{brand_voice_context}}

Structure:
1. **Subject Line** (3 options — curiosity-driven)
2. **Opening** (2-3 sentences — set the theme, personal touch)
3. **Featured Items** (3-5 curated links)
   For each:
   - Headline (your framing, not the original)
   - 2-3 sentence summary + your commentary
   - [LINK: url]
4. **Quick Hits** (3-4 one-liner links with brief commentary)
5. **One Thing** — Your personal recommendation (book/tool/idea)
6. **CTA** — Reply prompt or share ask

Tone: Knowledgeable friend sharing the best of what they read. NOT a news digest robot.
Length: 500-800 words.""",
        ),
        PromptTemplate(
            id="story_driven",
            name="Story-Driven Newsletter",
            description="Narrative-led newsletter that teaches through storytelling.",
            variables=["topic", "story_seed", "lesson", "target_audience"],
            platform="claude",
            agent="copy",
            prompt_text="""Write a Story-Driven Newsletter.

TOPIC: {{topic}}
STORY SEED: {{story_seed}}
LESSON: {{lesson}}
AUDIENCE: {{target_audience}}

{{brand_voice_context}}

Structure:
1. **Subject Line** (3 options — tease the story, not the lesson)
2. **The Story** (300-400 words)
   - Open with a vivid scene or moment
   - Build tension or curiosity
   - Include specific details (names, numbers, settings)
3. **The Bridge** (1-2 sentences connecting story to lesson)
4. **The Lesson** (200-300 words)
   - 3 actionable takeaways
   - Framework or mental model if applicable
5. **The Application** (2-3 sentences — how the reader uses this today)
6. **CTA** — Question for replies

Rules:
- Story must be true (or clearly labeled as hypothetical)
- Lesson must be non-obvious
- No "moral of the story is..." — be subtle
Length: 600-900 words.""",
        ),
        PromptTemplate(
            id="tutorial_newsletter",
            name="Tutorial Newsletter",
            description="Step-by-step how-to newsletter with actionable instructions.",
            variables=["skill_to_teach", "difficulty_level", "tools_needed", "target_audience"],
            platform="any",
            agent="copy",
            prompt_text="""Write a Tutorial Newsletter teaching {{skill_to_teach}}.

DIFFICULTY: {{difficulty_level}}
TOOLS NEEDED: {{tools_needed}}
AUDIENCE: {{target_audience}}

{{brand_voice_context}}

Structure:
1. **Subject Line** (3 options — promise a specific result)
2. **Intro** — Why this matters, what they'll be able to do after
3. **Prerequisites** — What they need before starting
4. **Steps** (5-8 clear steps)
   Each step:
   - Action headline ("Step 3: Configure your template")
   - What to do (specific instructions)
   - Why it matters (1 sentence)
   - Common mistake to avoid
   - [SCREENSHOT: description of what to show]
5. **Result** — What the finished thing looks like
6. **Level Up** — One advanced tip for those who want more
7. **CTA** — "Reply with your result" or "Try it and share"

Length: 700-1000 words. Dense with value.""",
        ),
    ],
)
