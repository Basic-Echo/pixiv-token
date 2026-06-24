"""
Pixiv R18 Search via OAuth PKCE flow
- If PIXIV_CODE env var is set: exchange code for tokens and search
- If not: generate PKCE login URL
"""
import json, os, sys, hashlib, urllib.request, urllib.parse
from base64 import urlsafe_b64encode
from hashlib import sha256
from secrets import token_urlsafe
from pixivpy3 import AppPixivAPI

CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"

VERIFIER_FILE = "code_verifier.txt"

def s256(data):
    return urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode("ascii")


def get_or_create_verifier():
    if os.path.exists(VERIFIER_FILE):
        with open(VERIFIER_FILE) as f:
            return f.read().strip()
    verifier = token_urlsafe(32)
    with open(VERIFIER_FILE, "w") as f:
        f.write(verifier)
    print(f"  [*] New code_verifier generated and saved to {VERIFIER_FILE}")
    return verifier


def exchange_code(code, code_verifier):
    """Exchange authorization code for tokens"""
    data = urllib.parse.urlencode({
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "code_verifier": code_verifier,
        "grant_type": "authorization_code",
        "include_policy": "true",
        "redirect_uri": "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback",
    }).encode()

    headers = {
        "User-Agent": "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    req = urllib.request.Request(
        "https://oauth.secure.pixiv.net/auth/token",
        data=data, headers=headers, method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        access_token = result.get("access_token")
        new_refresh = result.get("refresh_token", "")
        user_id = result.get("user", {}).get("id", 0)
        return access_token, new_refresh, user_id


def search_pixiv(access_token, refresh_token, user_id):
    """Search R18 Eyjafjalla"""
    api = AppPixivAPI()
    api.set_auth(access_token, refresh_token)
    api.user_id = user_id
    print(f"  [OK] Token valid - searching as user {user_id}")

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
                'pid': ill.id, 'title': ill.title,
                'user': ill.user.name if hasattr(ill, 'user') and ill.user else "?",
                'bookmark': ill.total_bookmarks, 'pages': ill.page_count,
                'r18': is_r18, 'width': getattr(ill, 'width', 0),
                'height': getattr(ill, 'height', 0), 'tags': tags[:8],
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

    with open("eyja_r18_results.json", "w", encoding="utf-8") as f:
        json.dump({"total": len(all_results), "r18_count": len(r18_list), "results": all_results},
                  f, indent=2, ensure_ascii=False)
    print(f"\n  Saved: eyja_r18_results.json")

    # GitHub step summary
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as f:
            f.write(f"## Pixiv R18 Search Results\n\nTotal: {len(all_results)}, R18: {len(r18_list)}\n\n")
            f.write(f"| PID | BM | R18 | Title |\n| --- | -- | --- | --- |\n")
            for r in r18_list[:30]:
                f.write(f"| {r['pid']} | {r['bookmark']} | R18 | {r['title']} |\n")


def main():
    print("=" * 70)
    print("  Pixiv R18 Eyjafjalla - PKCE OAuth Flow")
    print("=" * 70)

    auth_code = os.environ.get("PIXIV_CODE", "").strip()

    if auth_code:
        # Step 2: Exchange code for tokens and search
        print(f"\n[*] Exchanging authorization code for tokens...")
        verifier = get_or_create_verifier()
        try:
            access_token, refresh_token, user_id = exchange_code(auth_code, verifier)
            print(f"  [OK] Got access_token! User ID: {user_id}")
            print(f"  [*] Refresh token: {refresh_token[:30]}...")
            search_pixiv(access_token, refresh_token, user_id)
        except Exception as e:
            print(f"  [FAIL] Code exchange failed: {e}")
            sys.exit(1)
    else:
        # Step 1: Generate PKCE login URL
        code_verifier = get_or_create_verifier()
        code_challenge = s256(code_verifier.encode("ascii"))

        print(f"\n  [*] code_verifier: {code_verifier}")

        url = (
            "https://app-api.pixiv.net/web/v1/login"
            f"?code_challenge={code_challenge}"
            "&code_challenge_method=S256"
            "&client=pixiv-android"
        )

        print(f"\n{'='*70}")
        print(f"  [ACTION REQUIRED] Open this URL in a browser that can access Pixiv:")
        print(f"{'='*70}\n")
        print(f"  {url}")
        print(f"\n{'='*70}")
        print(f"  After login, you'll be redirected to a callback URL.")
        print(f"  Copy the 'code' parameter from the URL and re-run this")
        print(f"  workflow with PIXIV_CODE input set to that value.")
        print(f"{'='*70}")

        # Save URL to GITHUB_STEP_SUMMARY
        summary = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary:
            with open(summary, 'a') as f:
                f.write(f"## Pixiv OAuth Login\n\n")
                f.write(f"Open this URL (needs Pixiv access):\n")
                f.write(f"[Login URL]({url})\n\n")
                f.write(f"After login, get the 'code' from the redirect URL and re-run with PIXIV_CODE input.\n")


if __name__ == "__main__":
    main()
