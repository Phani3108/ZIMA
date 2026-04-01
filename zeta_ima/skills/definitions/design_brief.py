from zeta_ima.skills.base import PromptTemplate, SkillDefinition

skill = SkillDefinition(
    id="design_brief",
    name="Design Brief",
    description="Generate creative briefs for designers, brand kit specifications, and template requests. Bridges copy and design teams with structured handoffs.",
    icon="palette",
    category="distribution",
    platforms=["openai", "claude"],
    tools_used=["canva", "figma"],
    workflow_stages=["brief", "generate", "preview", "review"],
    default_llm="openai",
    fallback_llms=["claude", "gemini"],
    prompts=[
        PromptTemplate(
            id="creative_brief",
            name="Creative Brief",
            description="Structured brief for a designer to create visuals.",
            variables=["project_name", "deliverables", "target_audience", "brand_colors", "style_direction", "copy_text"],
            platform="openai",
            agent="design",
            prompt_text="""Create a Creative Brief for a designer.

PROJECT: {{project_name}}
DELIVERABLES: {{deliverables}}
AUDIENCE: {{target_audience}}
BRAND COLORS: {{brand_colors}}
STYLE: {{style_direction}}
COPY TO INCLUDE: {{copy_text}}

**CREATIVE BRIEF:**

1. **Project Overview** (2-3 sentences)
2. **Objective** — What should the viewer feel/do?
3. **Target Audience** — Demographics + psychographics
4. **Key Message** — The ONE thing the design must communicate
5. **Deliverables**
   | Asset | Dimensions | Format | Notes |
6. **Visual Direction**
   - Style: {{style_direction}}
   - Color palette: {{brand_colors}}
   - Typography guidance
   - Image style (photo/illustration/abstract)
   - Mood board keywords (5-7 adjectives)
7. **Copy & Content**
   - Headlines and body text to include
   - Hierarchy (what's most important visually?)
8. **Must-Haves**
   - Logo placement
   - CTA treatment
   - Legal/compliance requirements
9. **References** — 3 example designs for inspiration (describe them)
10. **DON'Ts** — What to avoid

Output: Structured brief ready to hand to a designer or upload to Canva/Figma.""",
        ),
        PromptTemplate(
            id="social_graphic_set",
            name="Social Graphic Set Brief",
            description="Brief for a set of social media graphics (posts, stories, covers).",
            variables=["campaign_name", "platforms", "key_messages", "brand_style"],
            platform="openai",
            agent="design",
            output_type="design",
            prompt_text="""Create briefs for a Social Graphic Set.

CAMPAIGN: {{campaign_name}}
PLATFORMS: {{platforms}}
MESSAGES: {{key_messages}}
STYLE: {{brand_style}}

{{brand_voice_context}}

Generate design briefs for:

1. **Feed Posts** (3 designs)
   - Dimensions: 1080x1080
   - Each: headline, body text, image/background description, CTA

2. **Stories** (3 designs)
   - Dimensions: 1080x1920
   - Each: headline, swipe-up CTA, visual description

3. **LinkedIn Banner** (1 design)
   - Dimensions: 1584x396
   - Headline + subtitle + visual concept

4. **Twitter Header** (1 design)
   - Dimensions: 1500x500
   - Campaign-themed

For each design:
- [CANVA: template style suggestion]
- [COLOR: primary, secondary, accent]
- [FONT: heading font + body font suggestion]
- [IMAGE: photo/illustration description]""",
        ),
    ],
)
