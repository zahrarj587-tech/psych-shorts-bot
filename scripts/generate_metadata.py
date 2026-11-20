import json
from pathlib import Path

IDEAS_FILE = Path("data/ideas.json")
STATE_FILE = Path("data/published_ids.json")
OUTPUT_DIR = Path("output")


def load_published_ids() -> set[int]:
    if not STATE_FILE.exists():
        return set()
    data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return set(data.get("processed_ids", []))


def save_published_id(idea_id: int) -> None:
    processed = sorted(load_published_ids() | {idea_id})
    STATE_FILE.write_text(
        json.dumps({"processed_ids": processed}, indent=2),
        encoding="utf-8",
    )


def build_metadata(idea: dict) -> dict:
    idea_id = idea.get("id", 1)
    title = idea.get("title", "Psychology Insight").strip()
    hook = idea.get("hook", "").strip()
    script = idea.get("script", "").strip()

    tags = [
        "psychology",
        "behavioral psychology",
        "human behavior",
        "mindset",
        "self improvement",
        "shorts",
    ]
    hashtags = " ".join(f"#{t.replace(' ', '')}" for t in tags)

    description = (
        f"{hook}\n\n"
        f"In this short breakdown, we look at how everyday psychological patterns "
        f"shape decisions, focus, and reactions.\n\n"
        f"Key takeaway:\n{script}\n\n"
        f"Subscribe for daily bite-sized psychology and human behavior insights.\n\n"
        f"{hashtags}"
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
