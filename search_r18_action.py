"""
Pixiv R18 Eyjafjalla Search (sync version for GitHub Actions)
Manual OAuth to support older pixivpy3 versions
"""
import json, os, hashlib, urllib.request, urllib.parse
from datetime import datetime
from pixivpy3 import AppPixivAPI

CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
HASH_SECRET = "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"
PIXIV_USER = "shinkaisanka@gmail.com"
PIXIV_PASS = "10760819zjq"


def oauth_login():
    """Manual OAuth via password grant"""
    local_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
    client_hash = hashlib.md5((local_time + HASH_SECRET).encode()).hexdigest()

    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "password",
        "username": PIXIV_USER,
        "password": PIXIV_PASS,
        "get_secure_url": 1,
    }).encode()

    headers = {
        "User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)",
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Client-Time": local_time,
        "X-Client-Hash": client_hash,
    }

    req = urllib.request.Request(
        "https://oauth.secure.pixiv.net/auth/token",
        data=data, headers=headers, method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode())
            access_token = result.get("access_token")
            refresh_token = result.get("refresh_token", "")
            user_id = result.get("user", {}).get("id", 0)
            print(f"  [OK] Logged in (user ID: {user_id})")
            return access_token, refresh_token, user_id
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        print(f"  [FAIL] HTTP {e.code}: {body[:300]}")
        raise


def main():
    print("=" * 70)
    print("  Pixiv R18 Eyjafjalla Search")
    print("=" * 70)

    # Manual OAuth
    print("\n[*] Logging in...")
    access_token, refresh_token, user_id = oauth_login()

    # Setup pixivpy3 with our token
    api = AppPixivAPI()
    api.set_auth(access_token, refresh_token)
    api.user_id = user_id

    queries = [
        "\u30a8\u30a4\u30e4\u30d5\u30a3\u30e4\u30c8\u30e9 R-18",
        "\u30a8\u30a4\u30e4\u30d5\u30a3\u30e4\u30c8\u30e9",
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

    # GitHub Actions step summary
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
