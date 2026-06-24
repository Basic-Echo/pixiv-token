"""
Pixiv R18 Eyjafjalla search - use public API + pixivpy3
Try multiple auth-free approaches
"""
import json, os, urllib.request, urllib.parse
from pixivpy3 import AppPixivAPI
import hashlib
from datetime import datetime

CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"
HASH_SECRET = "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"


def try_public_api():
    """Try Pixiv public API (no auth needed for some endpoints)"""
    all_works = []

    # R18 daily ranking
    print("\n[*] Trying public API ranking (R18 daily)...")
    try:
        url = "https://public-api.secure.pixiv.net/v1.1/ranking/day_r18.json"
        req = urllib.request.Request(url, headers={
            "User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)",
            "Referer": "https://www.pixiv.net",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            works = data.get("response", [{}])[0].get("works", []) if isinstance(data.get("response"), list) else []
            print(f"  [OK] Got {len(works)} works from R18 daily ranking")
            all_works.extend(works)
    except Exception as e:
        print(f"  [FAIL] {e}")

    # R18 weekly ranking
    print("\n[*] Trying R18 weekly ranking...")
    try:
        url = "https://public-api.secure.pixiv.net/v1.1/ranking/week_r18.json"
        req = urllib.request.Request(url, headers={
            "User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)",
            "Referer": "https://www.pixiv.net",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            works = data.get("response", [{}])[0].get("works", []) if isinstance(data.get("response"), list) else []
            print(f"  [OK] Got {len(works)} works from R18 weekly ranking")
            all_works.extend(works)
    except Exception as e:
        print(f"  [FAIL] {e}")

    # Search public API for Eyjafjalla
    print("\n[*] Trying public search API...")
    try:
        keyword = urllib.parse.quote("\u30a8\u30a4\u30e4\u30d5\u30a3\u30e4\u30c8\u30e9")
        url = f"https://public-api.secure.pixiv.net/v1.1/search/works.json?q={keyword}&search_target=partial_match_for_tags&sort=popular_desc&per_page=50"
        req = urllib.request.Request(url, headers={
            "User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)",
            "Referer": "https://www.pixiv.net",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            works = data.get("response", [])
            if isinstance(works, dict):
                works = works.get('works', works.get('illusts', []))
            elif isinstance(works, list) and works:
                works = works[0].get('works', works[0].get('illusts', [])) if isinstance(works[0], dict) else works
            print(f"  [OK] Got {len(works)} works from public search")
            all_works.extend(works)
    except Exception as e:
        print(f"  [FAIL] {e}")

    return all_works


def try_app_auth():
    """Try pixivpy3 auth with Android app credentials"""
    print("\n[*] Trying pixivpy3 auth (password grant)...")
    try:
        api = AppPixivAPI()
        api.login("shinkaisanka@gmail.com", "10760819zjq")
        print(f"  [OK] User ID: {api.user_id}, token: {api.access_token[:20]}...")
        return api
    except Exception as e:
        print(f"  [FAIL] {e}")
        return None


def try_sniff_auth():
    """Try raw OAuth with exact PixivIA App signature"""
    print("\n[*] Trying raw OAuth (iOS UA)...")
    try:
        local_time = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S+00:00")
        client_hash = hashlib.md5((local_time + HASH_SECRET).encode()).hexdigest()

        for ua in [
            "PixivIOSApp/7.13.3 (iOS 14.6; iPhone13,2)",
            "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)",
        ]:
            data = urllib.parse.urlencode({
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "grant_type": "password",
                "username": "shinkaisanka@gmail.com",
                "password": "10760819zjq",
                "get_secure_url": 1,
            }).encode()

            req = urllib.request.Request(
                "https://oauth.secure.pixiv.net/auth/token",
                data=data,
                headers={
                    "User-Agent": ua,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Client-Time": local_time,
                    "X-Client-Hash": client_hash,
                    "app-os": "ios",
                    "app-os-version": "14.6",
                },
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode())
                at = result.get("access_token")
                if at:
                    print(f"  [OK] UA={ua[:20]}... Got access_token!")
                    return result

    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        print(f"  [FAIL] HTTP {e.code}: {body[:200]}")
    except Exception as e:
        print(f"  [FAIL] {e}")
    return None


def search_with_api(api):
    """Search using authenticated API"""
    queries = [
        "\u30a8\u30a4\u30e4\u30d5\u30a3\u30e4\u30c8\u30e9 R-18",
        "\u30a8\u30a4\u30e4\u30d5\u30a3\u30e4\u30c8\u30e9",
    ]
    all_results = []
    seen_pids = set()

    for search_word in queries:
        print(f"\n[*] Searching: {search_word}")
        result = api.search_illust(search_word, search_target="partial_match_for_tags", sort="popular_desc")
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
                'pid': ill.id, 'title': ill.title,
                'user': ill.user.name if hasattr(ill, 'user') and ill.user else "?",
                'bookmark': ill.total_bookmarks, 'pages': ill.page_count,
                'r18': is_r18, 'width': getattr(ill, 'width', 0),
                'height': getattr(ill, 'height', 0), 'tags': tags[:8],
            })

    return all_results


def dedup_and_sort(results):
    seen = set()
    unique = []
    for r in results:
        if r['pid'] not in seen:
            seen.add(r['pid'])
            unique.append(r)
    unique.sort(key=lambda x: x['bookmark'], reverse=True)
    return unique


def main():
    print("=" * 70)
    print("  Pixiv R18 Eyjafjalla Search")
    print("=" * 70)

    all_results = []

    # Approach 1: Public ranking + public search API
    public_works = try_public_api()
    for w in public_works:
        if not isinstance(w, dict):
            continue
        tags = w.get('tags', [])
        if isinstance(tags, list):
            tag_names = [t.get('name', '') if isinstance(t, dict) else str(t) for t in tags]
        else:
            tag_names = []
        user = w.get('user', {})
        if not isinstance(user, dict):
            user = {}
        all_results.append({
            'pid': w.get('id', 0) or w.get('illust_id', 0),
            'title': w.get('title', '?'),
            'user': user.get('name', user.get('account', '?')),
            'bookmark': w.get('stats', {}).get('bookmarks_count', 0) if isinstance(w.get('stats'), dict) else 0,
            'pages': w.get('page_count', 1),
            'r18': True,
            'width': w.get('width', 0),
            'height': w.get('height', 0),
            'tags': tag_names[:8],
        })

    # Approach 2: Try pixivpy3 auth
    api = try_app_auth()
    if api:
        results = search_with_api(api)
        all_results.extend(results)
    else:
        # Approach 3: raw OAuth with different UAs
        raw_result = try_sniff_auth()
        if raw_result:
            at = raw_result.get("access_token")
            rt = raw_result.get("refresh_token", "")
            uid = raw_result.get("user", {}).get("id", 0)
            api2 = AppPixivAPI()
            api2.set_auth(at, rt)
            api2.user_id = uid
            results = search_with_api(api2)
            all_results.extend(results)

    # Dedup and sort
    unique = dedup_and_sort(all_results)
    r18_list = [r for r in unique if r['r18']]

    print(f"\n{'='*70}")
    print(f"  Total: {len(unique)}, R18: {len(r18_list)}")
    print(f"\n  {'PID':>10} {'BM':>6} {'P':>2} R18  Title")
    print(f"  {'-'*55}")
    for r in unique[:40]:
        r18m = "[R]" if r['r18'] else "   "
        print(f"  {r['pid']:>10} {r['bookmark']:>6} {r['pages']:>2} {r18m} {r['title'][:45]}")

    with open("eyja_r18_results.json", "w", encoding="utf-8") as f:
        json.dump({"total": len(unique), "r18_count": len(r18_list), "results": unique},
                  f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: eyja_r18_results.json")

    step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if step_summary:
        with open(step_summary, 'a') as f:
            f.write(f"## Search Results\nTotal: {len(unique)}, R18: {len(r18_list)}\n\n")
            f.write("| PID | BM | R18 | Title |\n| --- | -- | --- | --- |\n")
            for r in r18_list[:30]:
                f.write(f"| {r['pid']} | {r['bookmark']} | R18 | {r['title']} |\n")


if __name__ == "__main__":
    main()
