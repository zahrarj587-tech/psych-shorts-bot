import json
from pathlib import Path

POOL_FILE = Path("data/ideas_pool.json")
PUBLISHED_FILE = Path("data/published_ids.json")
IDEAS_FILE = Path("data/ideas.json")

def main():
    pool = json.loads(POOL_FILE.read_text(encoding="utf-8"))
    if PUBLISHED_FILE.exists():
        published = json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))
    else:
        published = []
    idx = len(published) % len(pool)
    selected = pool[idx]
    IDEAS_FILE.write_text(json.dumps([selected], indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Selected idea {selected['id']}: {selected['title']} (pool index {idx + 1}/{len(pool)})")

if __name__ == "__main__":
    main()
