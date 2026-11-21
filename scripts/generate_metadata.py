import json
import re
from pathlib import Path

IDEAS_FILE = Path("data/ideas.json")
OUTPUT_DIR = Path("output")

GENERAL_TAGS = [
    "psychology",
    "behavioral psychology",
    "human behavior",
    "mindset",
    "self improvement",
    "shorts",
]

def generate_hashtags(title: str, base_tags: list) -> str:
    # استخراج كلمات من العنوان لعمل هاشتاجات مخصصة
    words = re.findall(r'\b[A-Za-z]{4,}\b', title.lower())
    
    # كلمات شائعة مش هنحتاجها كهاشتاجات
    stopwords = {
        "this", "that", "with", "from", "your", "what", "when", "why", "how",
        "they", "them", "their", "have", "will", "make", "made", "about",
        "which", "there", "these", "those", "into", "over", "after", "before",
        "more", "most", "some", "such", "only", "than", "then", "does", "your"
    }
    
    # هناخد أول 3 كلمات مخصصة
    specific_tags = [w for w in set(words) if w not in stopwords][:3]
    
    all_hashtags = list(set(base_tags + specific_tags))
    return " ".join(f"#{t.replace(' ', '').replace('-', '')}" for t in all_hashtags)

def build_metadata(idea: dict) -> dict:
    idea_id = idea.get("id", 1)
    title = idea.get("title", "Psychology Insight").strip()
    hook = idea.get("hook", "").strip()
    script = idea.get("script", "").strip()

    tags = GENERAL_TAGS.copy()
    
    # لو الفكرة فيها tags جاهزة في ideas_pool.json، هنضيفها
    if "tags" in idea and isinstance(idea["tags"], list):
        tags.extend(idea["tags"])
        
    hashtags_str = generate_hashtags(title, tags)

    description = (
        f"{hook}\n\n"
        f"In this short breakdown, we look at how everyday psychological patterns shape decisions, focus, and reactions.\n\n"
        f"Key takeaway:\n{script}\n\n"
        f"Subscribe for daily bite-sized psychology and human behavior insights.\n\n"
        f"{hashtags_str}"
    )

    return {
        "id": idea_id,
        "title": f"{title} #Shorts",
        "description": description,
        "tags": tags,
        "privacy_status": "unlisted",
    }

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ideas = json.loads(IDEAS_FILE.read_text(encoding="utf-8"))
    for idea in ideas:
        idea_id = idea.get("id", 1)
        meta = build_metadata(idea)
        meta_path = OUTPUT_DIR / f"idea_{idea_id}_meta.json"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved metadata: {meta_path}")

if __name__ == "__main__":
    main()
