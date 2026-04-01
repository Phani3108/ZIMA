from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="seo_content",
    name="SEO Content",
    description="Generate rankable content with human voice — blog posts, pillar pages, and content refreshes. Integrates live SERP analysis and People Also Ask data.",
    icon="trending-up",
    category="execution",
    platforms=["openai", "gemini"],
    tools_used=["web_search", "semrush"],
    workflow_stages=["keyword_research", "serp_analysis", "outline", "draft", "optimize", "review"],
    default_llm="openai",
    fallback_llms=["gemini", "claude"],
    prompts=[
        PromptTemplate(
            id="seo_blog_post",
            name="SEO Blog Post",
            description="SERP-optimized blog post with keyword targeting, structure, and meta tags.",
            variables=["topic", "primary_keyword", "secondary_keywords", "target_word_count", "campaign_goal"],
            platform="openai",
            agent="copy",
            prompt_text="""You are an SEO content specialist. Write a comprehensive, rankable blog post.

TOPIC: {{topic}}
PRIMARY KEYWORD: {{primary_keyword}}
SECONDARY KEYWORDS: {{secondary_keywords}}
WORD COUNT: {{target_word_count}}
CAMPAIGN GOAL: {{campaign_goal}}

SERP RESEARCH (auto-injected from research stage):
{{kb_context}}

BRAND VOICE:
{{brand_voice_context}}

Requirements:
1. **Title** — Contains primary keyword, under 60 characters, compelling
2. **Meta Description** — 150-155 characters, includes keyword, has CTA
3. **URL Slug** — Clean, keyword-rich, no stop words
4. **Introduction** (100-150 words)
   - Hook with a stat, question, or bold claim
   - Preview what the reader will learn
   - Include primary keyword naturally
5. **Body** — H2/H3 structure
   - Primary keyword density: 1-2%
   - Secondary keywords woven naturally
   - Short paragraphs (2-3 sentences)
   - Include at least 2 original insights (not just restated common knowledge)
6. **FAQ Section** — 5 questions from People Also Ask
7. **Conclusion** — Summarize + CTA aligned with {{campaign_goal}}
8. **Internal Linking Suggestions** — 3-5 recommended internal links
9. **Schema Markup Recommendation** — Article, FAQ, or HowTo

Output: Full article in markdown with meta tags as frontmatter.""",
        ),
        PromptTemplate(
            id="content_refresh",
            name="Content Refresh",
            description="Update existing content for improved SEO performance.",
            variables=["existing_content", "current_ranking", "target_keyword", "competitor_urls"],
            platform="openai",
            agent="seo",
            prompt_text="""You are an SEO content optimizer. Refresh this content to improve rankings.

EXISTING CONTENT:
{{existing_content}}

CURRENT RANKING: {{current_ranking}}
TARGET KEYWORD: {{target_keyword}}
COMPETING PAGES: {{competitor_urls}}

Analyze and provide:

1. **Content Audit**
   - Current word count vs competitors
   - Keyword usage score
   - Content freshness issues (outdated stats, references)
   - Missing subtopics that competitors cover

2. **Recommended Changes**
   - Sections to add (with drafted content)
   - Sections to update (with new text)
   - Sections to remove (thin or off-topic)
   - New internal/external links to add

3. **Updated Meta Tags**
   - New title tag
   - New meta description
   - Updated H2/H3 structure

4. **Fresh FAQ Section** (5 current People Also Ask questions)

5. **REFRESHED VERSION** — Complete updated article

Mark all changes with [ADDED], [UPDATED], or [REMOVED] tags.""",
        ),
        PromptTemplate(
            id="pillar_page",
            name="Pillar Page (3000+ words)",
            description="Comprehensive pillar page that anchors a topic cluster.",
            variables=["topic", "primary_keyword", "subtopics", "target_audience"],
            platform="openai",
            agent="copy",
            prompt_text="""Write a comprehensive Pillar Page (3000-5000 words).

TOPIC: {{topic}}
KEYWORD: {{primary_keyword}}
SUBTOPICS: {{subtopics}}
AUDIENCE: {{target_audience}}

{{brand_voice_context}}
{{kb_context}}

Structure:
1. **Hero Section** — Definitive title, meta description, intro paragraph
2. **Table of Contents** — Clickable anchors to each H2
3. **Chapter 1: What Is [Topic]** — Foundational definition + context
4. **Chapter 2: Why It Matters** — Business impact + data
5. **Chapter 3-8: [Subtopics]** — Deep dive into each subtopic
   - Each chapter: 400-600 words
   - Include examples, data, expert quotes
   - Internal link placeholder to cluster article: [LINK: cluster-article-title]
6. **Chapter 9: How to Get Started** — Actionable steps
7. **Chapter 10: Tools & Resources** — Relevant tools list
8. **FAQ** — 8-10 questions
9. **Conclusion + CTA**

Rules:
- Write as the definitive resource on this topic
- Include original frameworks or mental models where possible
- Data-backed claims (cite sources)
- Scannable: headers, bullets, bold key phrases, callout boxes""",
        ),
    ],
)
