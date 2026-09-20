# Ported from ~/CC_Projects/blog-tool/blogpost.py's template/slug/excerpt logic
# (the parts with no $EDITOR/input() I/O), so this tab produces byte-identical
# post pages to the CLI tool. blog-tool itself is untouched.
import re

from config import BLOG_DIR

POST_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <!-- This page's structure is the template used by
       ~/CC_Projects/blog-tool/blogpost.py to generate new posts.
       New posts should be created via that tool, not by copying this file by hand. -->
  <meta charset="UTF-8">
  <meta name="description" content="{title} - a devlog post on PettyPixels.">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - PettyPixels</title>
  <link rel="icon" type="image/svg+xml" href="../favicon.svg">
  <link rel="stylesheet" href="../styles.css">
</head>
<body>
  <div class="page-shell">
    <div class="window">
      <div class="titlebar">
        <span>pettypixels.exe</span>
        <span class="titlebar-controls" aria-hidden="true">
          <span>_</span><span>&#9633;</span><span>X</span>
        </span>
      </div>
      <nav class="menubar">
        <a href="../index.html">Home</a>
        <a href="../games.html">Games</a>
        <a href="../art.html">Art</a>
        <a href="../models.html">3D</a>
        <a href="../music.html">Music</a>
        <a href="../blog.html" class="current">Blog</a>
        <a href="#contact">Contact</a>
      </nav>

      <div class="window-body">
        <section class="panel">
          <h1 class="panel-title">{title}</h1>
          <div class="panel-body">
            <p class="copyright">{tag} | {date}</p>
{body}
            <p><a href="../blog.html" class="btn">&larr; Back to Blog</a></p>
          </div>
        </section>

        <section class="panel" id="contact">
          <h2 class="panel-title">Contact</h2>
          <div class="panel-body">
            <div class="social-icons">
              <a href="https://github.com/PettyPixels" target="_blank" rel="noopener noreferrer"><img src="../media/icons/github.svg" alt="GitHub"></a>
              <a href="https://www.linkedin.com/in/zachpetty" target="_blank" rel="noopener noreferrer"><img src="../media/icons/linkedin.svg" alt="LinkedIn"></a>
              <a href="mailto:zach@pettypixels.dev"><img src="../media/icons/email.svg" alt="Email"></a>
              <a href="https://zachpetty.itch.io/" target="_blank" rel="noopener noreferrer"><img src="../media/icons/itchio.svg" alt="Itch.io"></a>
              <a href="https://www.youtube.com/@PettyPixelsDev" target="_blank" rel="noopener noreferrer"><img src="../media/icons/youtube.svg" alt="YouTube"></a>
              <a href="https://discord.gg/vHTsk4FcWH" target="_blank" rel="noopener noreferrer"><img src="../media/icons/discord.svg" alt="Discord"></a>
            </div>
          </div>
        </section>
        <p class="copyright">&copy; 2026 Zach Petty</p>
      </div>
    </div>
  </div>
</body>
</html>
"""

BODY_START_MARKER = '<p class="copyright">'
BODY_END_MARKER = '<p><a href="../blog.html" class="btn">'


def slugify(title):
    slug = title.lower().strip()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    return slug or "post"


def unique_slug(base_slug, existing_slugs):
    slug = base_slug
    n = 2
    while f"{slug}.html" in existing_slugs or (BLOG_DIR / f"{slug}.html").exists():
        slug = f"{base_slug}-{n}"
        n += 1
    return slug


def strip_tags_and_excerpt(html_body, max_len=150):
    text = re.sub(r"<[^>]+>", " ", html_body)
    text = re.sub(r"\s+", " ", text).strip()
    match = re.search(r"^.*?[.!?](?=\s|$)", text)
    sentence = match.group(0) if match else text
    if len(sentence) > max_len:
        sentence = sentence[:max_len].rstrip() + "…"
    return sentence


def indent_body(body_text):
    lines = [line for line in body_text.splitlines() if line.strip()]
    if not lines:
        return "            <p></p>"
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("<"):
            out.append(f"            {stripped}")
        else:
            out.append(f"            <p>{stripped}</p>")
    return "\n".join(out)


def extract_body(html_text):
    start = html_text.find(BODY_START_MARKER)
    end = html_text.find(BODY_END_MARKER)
    if start == -1 or end == -1:
        return ""
    after_byline = html_text.find("\n", start)
    body_html = html_text[after_byline + 1 : end].strip("\n")
    lines = body_html.splitlines()
    stripped_lines = [line.strip() for line in lines if line.strip()]
    return "\n".join(stripped_lines)


def render_post_html(title, tag, post_date, body_text):
    return POST_TEMPLATE.format(title=title, tag=tag, date=post_date, body=indent_body(body_text))
