"""
Pixiv R18 Eyjafjalla Search (sync version for GitHub Actions)
Uses pixivpy3 for sync OAuth + search
"""
import json, os
from pixivpy3 import AppPixivAPI

REFRESH_TOKEN = "lL7bEXcWLqKHy1vNi7pl_W2D_XfMbgAPhJ5eDHSarFU"

def main():
    print("=" * 70)
    print("  Pixiv R18 Eyjafjalla Search")
    print("=" * 70)

    api = AppPixivAPI()
    api.login(refresh_token=REFRESH_TOKEN)
    print(f"  [OK] Logged in (user ID: {api.user_id})")

    queries = [
        "エイヤフィヤトラ R-18",
        "エイヤフィヤトラ",
    ]

    all_results = []
    seen_pids = set()

    for search_word in queries:
        print(f"\n[*] Searching: {search_word}")
        result = api.search_illust(
            search_word,
            search_target="partial_match_for_tags",
            sort="popular_desc",
        )

        illustrates = result.illust if hasattr(result, 'illust') else []
        if not illustrates:
            print("  No results")
            continue

        print(f"  Found {len(illustrates)} results")
        for ill in illustrates[:60]:
            if ill.id in seen_pids:
                continue
            seen_pids.add(ill.id)

            tags = [t.name for t in ill.tags] if hasattr(ill, 'tags') and ill.tags else []
            is_r18 = "R-18" in tags or getattr(ill, 'x_restrict', 0) == 1

            all_results.append({
                'pid': ill.id,
                'title': ill.title,
                'user': ill.user.name if hasattr(ill, 'user') and ill.user else "?",
                'bookmark': ill.total_bookmarks,
                'pages': ill.page_count,
                'r18': is_r18,
                'width': getattr(ill, 'width', 0),
                'height': getattr(ill, 'height', 0),
                'tags': tags[:8],
            })

    all_results.sort(key=lambda x: x['bookmark'], reverse=True)
    r18_list = [r for r in all_results if r['r18']]

    print(f"\n{'='*70}")
    print(f"  Total: {len(all_results)}, R18: {len(r18_list)}")

    print(f"\n  {'PID':>10} {'BM':>6} {'P':>2} R18  Title")
    print(f"  {'-'*55}")
    for r in all_results[:40]:
        r18m = "[R]" if r['r18'] else "   "
        print(f"  {r['pid']:>10} {r['bookmark']:>6} {r['pages']:>2} {r18m} {r['title'][:45]}")

    output = {
        'total': len(all_results),
        'r18_count': len(r18_list),
        'results': all_results,
    }
    output_path = "eyja_r18_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: {output_path}")

    # GitHub Actions summary
    step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if step_summary:
        with open(step_summary, 'a') as f:
            f.write(f"## Pixiv R18 Search Results\n\n")
            f.write(f"- Total: {len(all_results)}, R18: {len(r18_list)}\n\n")
            f.write(f"| PID | BM | R18 | Title | Tags |\n")
            f.write(f"| --- | -- | --- | --- | --- |\n")
            for r in r18_list[:30]:
                tag_str = ", ".join(r['tags'][:4])
                f.write(f"| {r['pid']} | {r['bookmark']} | R18 | {r['title']} | {tag_str} |\n")

if __name__ == "__main__":
    main()
