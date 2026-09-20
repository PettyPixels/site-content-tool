import settings

PORTFOLIO_SITE = settings.get_portfolio_site()
if PORTFOLIO_SITE is None:
    raise RuntimeError("Portfolio site not configured. Run main.py first.")
DATA_DIR = PORTFOLIO_SITE / "data"
MEDIA_DIR = PORTFOLIO_SITE / "media"
MEDIA_IMAGES_DIR = MEDIA_DIR / "images"
BLOG_DIR = PORTFOLIO_SITE / "blog"
POSTS_JSON = "posts.json"


def images_dir_for(content_type_key):
    return MEDIA_IMAGES_DIR / content_type_key
