#!/usr/bin/env python3
"""
LinkMint Backend API Test Suite
Tests all endpoints using the public URL
"""
import requests
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

BASE_URL = "https://go-shortlink.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

class LinkMintTester:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.created_codes = []
        self.session_token = None  # For authenticated requests
        self.test_user_email = None
        self.test_user2_token = None  # For ownership tests
        
    def log(self, message: str, color: str = Colors.RESET):
        print(f"{color}{message}{Colors.RESET}")
    
    def test(self, name: str, func):
        """Run a single test"""
        self.tests_run += 1
        self.log(f"\n[{self.tests_run}] Testing: {name}", Colors.BLUE)
        try:
            func()
            self.tests_passed += 1
            self.log(f"✅ PASSED: {name}", Colors.GREEN)
            return True
        except AssertionError as e:
            self.tests_failed += 1
            self.log(f"❌ FAILED: {name}", Colors.RED)
            self.log(f"   Error: {str(e)}", Colors.RED)
            return False
        except Exception as e:
            self.tests_failed += 1
            self.log(f"❌ ERROR: {name}", Colors.RED)
            self.log(f"   Exception: {str(e)}", Colors.RED)
            return False
    
    def cleanup(self):
        """Delete all created test links"""
        self.log("\n🧹 Cleaning up test links...", Colors.YELLOW)
        for code in self.created_codes:
            try:
                requests.delete(f"{BASE_URL}/links/{code}")
            except Exception:
                pass
    
    # ========== TEST CASES ==========
    
    def test_health_check(self):
        """GET /api/health - should return mongo:ok and redis:ok"""
        resp = requests.get(f"{BASE_URL}/health")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get('mongo') == 'ok', f"Mongo status: {data.get('mongo')}"
        assert data.get('redis') == 'ok', f"Redis status: {data.get('redis')}"
        self.log(f"   Health: mongo={data['mongo']}, redis={data['redis']}")
    
    def test_shorten_plain_url(self):
        """POST /api/shorten with plain URL (auto https:// prefixing)"""
        # Test with URL missing https://
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "example.com/test"})
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert 'code' in data, "Response missing 'code'"
        assert 'url' in data, "Response missing 'url'"
        assert data['url'].startswith('https://'), f"URL not prefixed with https://: {data['url']}"
        self.created_codes.append(data['code'])
        self.log(f"   Created: /{data['code']} -> {data['url']}")
    
    def test_shorten_with_custom_alias_success(self):
        """POST /api/shorten with custom_alias - success"""
        alias = f"test-alias-{int(time.time())}"
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com",
            "custom_alias": alias
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data['code'] == alias, f"Expected code={alias}, got {data['code']}"
        self.created_codes.append(alias)
        self.log(f"   Created custom alias: /{alias}")
    
    def test_shorten_duplicate_alias(self):
        """POST /api/shorten with duplicate custom_alias - should return 409"""
        # Note: 'demo-link' already exists in DB from manual testing
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com",
            "custom_alias": "demo-link"
        })
        assert resp.status_code == 409, f"Expected 409 for duplicate alias, got {resp.status_code}"
        self.log(f"   Correctly rejected duplicate alias 'demo-link'")
    
    def test_shorten_invalid_alias(self):
        """POST /api/shorten with invalid alias (e.g. 'a!') - should return 422"""
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com",
            "custom_alias": "a!"
        })
        assert resp.status_code == 422, f"Expected 422 for invalid alias, got {resp.status_code}"
        self.log(f"   Correctly rejected invalid alias 'a!'")
    
    def test_shorten_reserved_alias(self):
        """POST /api/shorten with reserved alias 'api' - should return 409"""
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com",
            "custom_alias": "api"
        })
        assert resp.status_code == 409, f"Expected 409 for reserved alias, got {resp.status_code}"
        self.log(f"   Correctly rejected reserved alias 'api'")
    
    def test_shorten_invalid_url(self):
        """POST /api/shorten with invalid URL - should return 422"""
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "notaurl"})
        assert resp.status_code == 422, f"Expected 422 for invalid URL, got {resp.status_code}"
        self.log(f"   Correctly rejected invalid URL 'notaurl'")
    
    def test_shorten_with_future_expiry(self):
        """POST /api/shorten with expires_at in future - should work"""
        future = datetime.now(timezone.utc) + timedelta(days=7)
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com/expiring",
            "expires_at": future.isoformat()
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data['expires_at'] is not None, "expires_at should be set"
        self.created_codes.append(data['code'])
        self.log(f"   Created link with future expiry: /{data['code']}")
    
    def test_shorten_with_past_expiry(self):
        """POST /api/shorten with expires_at in past - should return 422"""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com",
            "expires_at": past.isoformat()
        })
        assert resp.status_code == 422, f"Expected 422 for past expiry, got {resp.status_code}"
        self.log(f"   Correctly rejected past expiration date")
    
    def test_resolve_code(self):
        """GET /api/resolve/{code} - should return url and increment clicks"""
        # Create a link first
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/resolve-test"})
        assert resp.status_code == 200
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Resolve it
        resp = requests.get(f"{BASE_URL}/resolve/{code}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data['code'] == code
        assert data['url'] == "https://example.com/resolve-test"
        self.log(f"   Resolved /{code} -> {data['url']}")
        
        # Check clicks incremented (Phase 4: /links now returns paginated format)
        time.sleep(0.5)  # Give DB time to update
        resp = requests.get(f"{BASE_URL}/links")
        data = resp.json()
        links = data.get('items', data) if isinstance(data, dict) else data
        link = next((l for l in links if l['code'] == code), None)
        assert link is not None, f"Link {code} not found in list"
        assert link['clicks'] >= 1, f"Clicks not incremented: {link['clicks']}"
        self.log(f"   Clicks incremented to {link['clicks']}")
    
    def test_resolve_nonexistent(self):
        """GET /api/resolve/nonexistent - should return 404"""
        resp = requests.get(f"{BASE_URL}/resolve/nonexistent-code-xyz")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        self.log(f"   Correctly returned 404 for nonexistent code")
    
    def test_redirect_endpoint(self):
        """GET /api/r/{code} - should return 302 redirect"""
        # Create a link first
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/redirect-test"})
        assert resp.status_code == 200
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Test redirect (don't follow redirects)
        resp = requests.get(f"{BASE_URL}/r/{code}", allow_redirects=False)
        assert resp.status_code == 302, f"Expected 302, got {resp.status_code}"
        assert 'location' in resp.headers, "Missing Location header"
        assert resp.headers['location'] == "https://example.com/redirect-test"
        self.log(f"   Redirect working: /{code} -> {resp.headers['location']}")
    
    def test_expired_link(self):
        """Expired link should return 410"""
        # Create a link with very short expiry (1 second in future)
        future = datetime.now(timezone.utc) + timedelta(seconds=1)
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com/will-expire",
            "expires_at": future.isoformat()
        })
        assert resp.status_code == 200
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Wait for expiration
        self.log(f"   Waiting 2 seconds for link to expire...")
        time.sleep(2)
        
        # Try to resolve - should get 410
        resp = requests.get(f"{BASE_URL}/resolve/{code}")
        assert resp.status_code == 410, f"Expected 410 for expired link, got {resp.status_code}"
        self.log(f"   Correctly returned 410 for expired link")
    
    def test_list_links(self):
        """GET /api/links - should return paginated format {items, total, page, pages}"""
        resp = requests.get(f"{BASE_URL}/links")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        
        # Phase 4: Response is now paginated
        assert isinstance(data, dict), "Response should be a dict"
        assert 'items' in data, "Response should have 'items' field"
        assert 'total' in data, "Response should have 'total' field"
        assert 'page' in data, "Response should have 'page' field"
        assert 'pages' in data, "Response should have 'pages' field"
        
        links = data['items']
        assert isinstance(links, list), "'items' should be a list"
        
        # Check sorting (newest first)
        if len(links) >= 2:
            for i in range(len(links) - 1):
                t1 = datetime.fromisoformat(links[i]['created_at'].replace('Z', '+00:00'))
                t2 = datetime.fromisoformat(links[i+1]['created_at'].replace('Z', '+00:00'))
                assert t1 >= t2, f"Links not sorted by created_at desc"
        
        # Check fields
        if links:
            link = links[0]
            assert 'code' in link
            assert 'url' in link
            assert 'clicks' in link
            assert 'is_expired' in link
        
        self.log(f"   Retrieved {len(links)} links (page {data['page']}/{data['pages']}), total={data['total']}, sorted correctly")
    
    def test_delete_link(self):
        """DELETE /api/links/{code} - should work, then 404 on resolve"""
        # Create a link
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/to-delete"})
        assert resp.status_code == 200
        code = resp.json()['code']
        
        # Delete it
        resp = requests.delete(f"{BASE_URL}/links/{code}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get('deleted') == True
        self.log(f"   Deleted /{code}")
        
        # Try to resolve - should get 404
        resp = requests.get(f"{BASE_URL}/resolve/{code}")
        assert resp.status_code == 404, f"Expected 404 after delete, got {resp.status_code}"
        self.log(f"   Correctly returned 404 after deletion")
    
    def test_delete_nonexistent(self):
        """DELETE /api/links/nonexistent - should return 404"""
        resp = requests.delete(f"{BASE_URL}/links/nonexistent-xyz")
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        self.log(f"   Correctly returned 404 for nonexistent link")
    
    def test_stats(self):
        """GET /api/stats - should return total_links, total_clicks, active_links"""
        resp = requests.get(f"{BASE_URL}/stats")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert 'total_links' in data
        assert 'total_clicks' in data
        assert 'active_links' in data
        assert isinstance(data['total_links'], int)
        assert isinstance(data['total_clicks'], int)
        assert isinstance(data['active_links'], int)
        self.log(f"   Stats: {data['total_links']} links, {data['total_clicks']} clicks, {data['active_links']} active")
    
    # ========== PHASE 4: AUTH TESTS ==========
    
    def test_auth_register_success(self):
        """POST /api/auth/register - create new user, returns UserOut + session cookie"""
        timestamp = int(time.time())
        self.test_user_email = f"test-{timestamp}@linkmint.test"
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": self.test_user_email,
            "password": "secret123",
            "name": "Test User"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert 'user_id' in data, "Missing user_id"
        assert data['email'] == self.test_user_email
        assert data['name'] == "Test User"
        assert 'password_hash' not in data, "password_hash should not be in response"
        
        # Check session cookie
        assert 'session_token' in resp.cookies, "Missing session_token cookie"
        self.session_token = resp.cookies['session_token']
        self.log(f"   Registered user: {data['email']}, user_id={data['user_id']}")
    
    def test_auth_register_duplicate_email(self):
        """POST /api/auth/register with duplicate email - should return 409"""
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": self.test_user_email,
            "password": "secret123",
            "name": "Duplicate"
        })
        assert resp.status_code == 409, f"Expected 409 for duplicate email, got {resp.status_code}"
        self.log(f"   Correctly rejected duplicate email")
    
    def test_auth_register_short_password(self):
        """POST /api/auth/register with password < 6 chars - should return 422"""
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": f"short-{int(time.time())}@test.com",
            "password": "12345",
            "name": "Short Pass"
        })
        assert resp.status_code == 422, f"Expected 422 for short password, got {resp.status_code}"
        self.log(f"   Correctly rejected short password")
    
    def test_auth_register_invalid_email(self):
        """POST /api/auth/register with invalid email - should return 422"""
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "not-an-email",
            "password": "secret123",
            "name": "Invalid Email"
        })
        assert resp.status_code == 422, f"Expected 422 for invalid email, got {resp.status_code}"
        self.log(f"   Correctly rejected invalid email")
    
    def test_auth_login_success(self):
        """POST /api/auth/login with correct credentials - returns user + cookie"""
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": self.test_user_email,
            "password": "secret123"
        })
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data['email'] == self.test_user_email
        assert 'session_token' in resp.cookies
        self.log(f"   Login successful for {data['email']}")
    
    def test_auth_login_wrong_password(self):
        """POST /api/auth/login with wrong password - should return 401"""
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": self.test_user_email,
            "password": "wrongpassword"
        })
        assert resp.status_code == 401, f"Expected 401 for wrong password, got {resp.status_code}"
        self.log(f"   Correctly rejected wrong password")
    
    def test_auth_me_with_cookie(self):
        """GET /api/auth/me with session_token cookie - should return user"""
        cookies = {'session_token': self.session_token}
        resp = requests.get(f"{BASE_URL}/auth/me", cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data['email'] == self.test_user_email
        self.log(f"   /auth/me with cookie: {data['email']}")
    
    def test_auth_me_with_bearer_token(self):
        """GET /api/auth/me with Authorization: Bearer header - should return user"""
        headers = {'Authorization': f'Bearer {self.session_token}'}
        resp = requests.get(f"{BASE_URL}/auth/me", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data['email'] == self.test_user_email
        self.log(f"   /auth/me with Bearer token: {data['email']}")
    
    def test_auth_me_no_session(self):
        """GET /api/auth/me without session - should return 401"""
        resp = requests.get(f"{BASE_URL}/auth/me")
        assert resp.status_code == 401, f"Expected 401 without session, got {resp.status_code}"
        self.log(f"   Correctly returned 401 without session")
    
    def test_auth_logout(self):
        """POST /api/auth/logout - deletes session, subsequent /me returns 401"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/auth/logout", cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data.get('logged_out') == True
        self.log(f"   Logout successful")
        
        # Try /me again - should fail
        resp = requests.get(f"{BASE_URL}/auth/me", cookies=cookies)
        assert resp.status_code == 401, f"Expected 401 after logout, got {resp.status_code}"
        self.log(f"   /auth/me correctly returns 401 after logout")
        
        # Re-login for subsequent tests
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": self.test_user_email,
            "password": "secret123"
        })
        self.session_token = resp.cookies['session_token']
    
    def test_auth_session_invalid(self):
        """POST /api/auth/session with fake session_id - should return 401 or 502 gracefully"""
        resp = requests.post(f"{BASE_URL}/auth/session", json={"session_id": "fake-session-id-xyz"})
        assert resp.status_code in [401, 502], f"Expected 401 or 502 for fake session_id, got {resp.status_code}"
        self.log(f"   Correctly returned {resp.status_code} for fake session_id")
    
    # ========== PHASE 4: OWNERSHIP TESTS ==========
    
    def test_ownership_shorten_authenticated(self):
        """POST /api/shorten while authenticated - sets owner_id"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/owned"}, cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data['owner_id'] is not None, "owner_id should be set for authenticated user"
        self.created_codes.append(data['code'])
        self.log(f"   Created owned link: /{data['code']}, owner_id={data['owner_id']}")
    
    def test_ownership_list_links_authenticated(self):
        """GET /api/links while authenticated - returns ONLY user's links"""
        cookies = {'session_token': self.session_token}
        resp = requests.get(f"{BASE_URL}/links", cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert 'items' in data, "Response should have 'items' field"
        items = data['items']
        
        # All items should belong to this user (owner_id set)
        for link in items:
            assert link['owner_id'] is not None, f"Link {link['code']} has owner_id=None (should be user's)"
        self.log(f"   Authenticated /links returned {len(items)} user-owned links")
    
    def test_ownership_list_links_anonymous(self):
        """GET /api/links without auth - returns ONLY anonymous links (owner_id=None)"""
        resp = requests.get(f"{BASE_URL}/links")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        items = data['items']
        
        # All items should be anonymous (owner_id=None)
        for link in items:
            assert link['owner_id'] is None, f"Link {link['code']} has owner_id set (should be None for anonymous)"
        self.log(f"   Anonymous /links returned {len(items)} anonymous links")
    
    def test_ownership_delete_own_link(self):
        """DELETE /api/links/{code} - owner can delete own link"""
        # Create a link as authenticated user
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/to-delete-own"}, cookies=cookies)
        code = resp.json()['code']
        
        # Delete it
        resp = requests.delete(f"{BASE_URL}/links/{code}", cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        self.log(f"   Owner successfully deleted own link /{code}")
    
    def test_ownership_delete_other_user_link_403(self):
        """DELETE /api/links/{code} on another user's link - should return 403"""
        # Create a second user
        timestamp = int(time.time())
        user2_email = f"test2-{timestamp}@linkmint.test"
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": user2_email,
            "password": "secret123",
            "name": "Test User 2"
        })
        user2_token = resp.cookies['session_token']
        
        # User 2 creates a link
        cookies2 = {'session_token': user2_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/user2-link"}, cookies=cookies2)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # User 1 tries to delete User 2's link - should get 403
        cookies1 = {'session_token': self.session_token}
        resp = requests.delete(f"{BASE_URL}/links/{code}", cookies=cookies1)
        assert resp.status_code == 403, f"Expected 403 when deleting other user's link, got {resp.status_code}"
        self.log(f"   Correctly returned 403 when trying to delete another user's link")
    
    def test_ownership_delete_anonymous_link_by_anyone(self):
        """DELETE /api/links/{code} on anonymous link - anyone can delete"""
        # Create anonymous link
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/anon-deletable"})
        code = resp.json()['code']
        
        # Authenticated user deletes it - should work
        cookies = {'session_token': self.session_token}
        resp = requests.delete(f"{BASE_URL}/links/{code}", cookies=cookies)
        assert resp.status_code == 200, f"Expected 200 when deleting anonymous link, got {resp.status_code}"
        self.log(f"   Anonymous link /{code} successfully deleted by authenticated user")
    
    # ========== PHASE 4: SEARCH & PAGINATION TESTS ==========
    
    def test_search_by_code(self):
        """GET /api/links?q=<substring> - filters by code case-insensitively"""
        # Create a link with known code
        alias = f"search-test-{int(time.time())}"
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com", "custom_alias": alias}, cookies=cookies)
        self.created_codes.append(alias)
        
        # Search for it (case-insensitive)
        resp = requests.get(f"{BASE_URL}/links", params={"q": "SEARCH-TEST"}, cookies=cookies)
        assert resp.status_code == 200
        items = resp.json()['items']
        assert len(items) > 0, "Search should return results"
        assert any(alias in link['code'] for link in items), f"Search results should include {alias}"
        self.log(f"   Search by code 'SEARCH-TEST' found {len(items)} results")
    
    def test_search_by_url(self):
        """GET /api/links?q=<substring> - filters by URL case-insensitively"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/unique-search-url-xyz"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        resp = requests.get(f"{BASE_URL}/links", params={"q": "unique-search-url"}, cookies=cookies)
        items = resp.json()['items']
        assert len(items) > 0, "Search should return results"
        assert any("unique-search-url" in link['url'].lower() for link in items)
        self.log(f"   Search by URL 'unique-search-url' found {len(items)} results")
    
    def test_pagination(self):
        """GET /api/links?page=2&limit=2 - paginates correctly with {items,total,page,pages}"""
        # Create multiple links to ensure pagination
        cookies = {'session_token': self.session_token}
        for i in range(5):
            resp = requests.post(f"{BASE_URL}/shorten", json={"url": f"https://example.com/page-{i}"}, cookies=cookies)
            self.created_codes.append(resp.json()['code'])
        
        # Get page 1 with limit 2
        resp = requests.get(f"{BASE_URL}/links", params={"page": 1, "limit": 2}, cookies=cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert 'items' in data
        assert 'total' in data
        assert 'page' in data
        assert 'pages' in data
        assert data['page'] == 1
        assert len(data['items']) <= 2
        self.log(f"   Pagination: page 1, {len(data['items'])} items, total={data['total']}, pages={data['pages']}")
        
        # Get page 2
        if data['pages'] >= 2:
            resp = requests.get(f"{BASE_URL}/links", params={"page": 2, "limit": 2}, cookies=cookies)
            data2 = resp.json()
            assert data2['page'] == 2
            self.log(f"   Pagination: page 2, {len(data2['items'])} items")
    
    # ========== PHASE 4: STATS SCOPING TEST ==========
    
    def test_stats_scoped_authenticated(self):
        """GET /api/stats while authenticated - returns user's totals only"""
        cookies = {'session_token': self.session_token}
        resp = requests.get(f"{BASE_URL}/stats", cookies=cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert 'total_links' in data
        self.log(f"   Authenticated stats: {data['total_links']} links (user's only)")
    
    def test_stats_scoped_anonymous(self):
        """GET /api/stats without auth - returns anonymous link totals only"""
        resp = requests.get(f"{BASE_URL}/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert 'total_links' in data
        self.log(f"   Anonymous stats: {data['total_links']} links (anonymous only)")
    
    # ========== PHASE 4: QR CODE TESTS ==========
    
    def test_qr_code_success(self):
        """GET /api/qr/{code} - returns valid image/png (200)"""
        # Create a link first
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/qr-test"})
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Get QR code
        resp = requests.get(f"{BASE_URL}/qr/{code}")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        assert resp.headers['content-type'] == 'image/png', f"Expected image/png, got {resp.headers['content-type']}"
        assert len(resp.content) > 0, "QR image should have content"
        self.log(f"   QR code for /{code}: {len(resp.content)} bytes")
    
    def test_qr_code_nonexistent(self):
        """GET /api/qr/nonexistent - should return 404"""
        resp = requests.get(f"{BASE_URL}/qr/nonexistent-code-xyz")
        assert resp.status_code == 404, f"Expected 404 for nonexistent QR, got {resp.status_code}"
        self.log(f"   Correctly returned 404 for nonexistent QR code")
    
    # ========== PHASE 6: BULK SHORTENING TESTS ==========
    
    def test_bulk_anonymous_401(self):
        """POST /api/shorten/bulk without auth - should return 401"""
        resp = requests.post(f"{BASE_URL}/shorten/bulk", json={"urls": ["https://example.com"]})
        assert resp.status_code == 401, f"Expected 401 for anonymous bulk, got {resp.status_code}"
        self.log(f"   Correctly returned 401 for anonymous bulk shortening")
    
    def test_bulk_authenticated_success(self):
        """POST /api/shorten/bulk with auth - creates multiple links"""
        cookies = {'session_token': self.session_token}
        urls = [
            "https://example.com/bulk1",
            "https://example.com/bulk2",
            "example.com/bulk3"  # Test https:// prefix
        ]
        resp = requests.post(f"{BASE_URL}/shorten/bulk", json={"urls": urls}, cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert 'results' in data, "Missing 'results' field"
        assert 'created' in data, "Missing 'created' field"
        assert 'failed' in data, "Missing 'failed' field"
        assert data['created'] == 3, f"Expected 3 created, got {data['created']}"
        assert data['failed'] == 0, f"Expected 0 failed, got {data['failed']}"
        
        # Check results structure
        for r in data['results']:
            assert 'url' in r, "Result missing 'url'"
            if r.get('code'):
                self.created_codes.append(r['code'])
                # Check https:// prefix was added
                assert r['url'].startswith('https://'), f"URL not prefixed: {r['url']}"
        
        self.log(f"   Bulk created {data['created']} links, {data['failed']} failed")
    
    def test_bulk_mixed_urls(self):
        """POST /api/shorten/bulk with mixed valid/invalid URLs - returns per-item results"""
        cookies = {'session_token': self.session_token}
        urls = [
            "https://example.com/valid1",
            "notaurl",  # Invalid
            "https://example.com/valid2"
        ]
        resp = requests.post(f"{BASE_URL}/shorten/bulk", json={"urls": urls}, cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data['created'] == 2, f"Expected 2 created, got {data['created']}"
        assert data['failed'] == 1, f"Expected 1 failed, got {data['failed']}"
        
        # Check error in results
        error_result = next((r for r in data['results'] if r.get('error')), None)
        assert error_result is not None, "Should have one error result"
        assert error_result['url'] == 'notaurl', f"Error result URL mismatch"
        
        # Collect created codes
        for r in data['results']:
            if r.get('code'):
                self.created_codes.append(r['code'])
        
        self.log(f"   Bulk with mixed URLs: {data['created']} created, {data['failed']} failed")
    
    def test_bulk_empty_list_422(self):
        """POST /api/shorten/bulk with empty list - should return 422"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten/bulk", json={"urls": []}, cookies=cookies)
        assert resp.status_code == 422, f"Expected 422 for empty list, got {resp.status_code}"
        self.log(f"   Correctly returned 422 for empty URL list")
    
    def test_bulk_over_50_urls_422(self):
        """POST /api/shorten/bulk with >50 URLs - should return 422"""
        cookies = {'session_token': self.session_token}
        urls = [f"https://example.com/bulk{i}" for i in range(51)]
        resp = requests.post(f"{BASE_URL}/shorten/bulk", json={"urls": urls}, cookies=cookies)
        assert resp.status_code == 422, f"Expected 422 for >50 URLs, got {resp.status_code}"
        self.log(f"   Correctly returned 422 for >50 URLs")
    
    # ========== PHASE 6: ANALYTICS TESTS ==========
    
    def test_analytics_click_tracking(self):
        """GET /api/resolve/{code} increments both clicks and daily bucket"""
        cookies = {'session_token': self.session_token}
        # Create a link
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/analytics-test"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Resolve it to generate clicks
        for _ in range(3):
            resp = requests.get(f"{BASE_URL}/resolve/{code}")
            assert resp.status_code == 200
        
        time.sleep(0.5)  # Give DB time to update
        
        # Get analytics
        resp = requests.get(f"{BASE_URL}/links/{code}/analytics", cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert 'code' in data, "Missing 'code' field"
        assert 'total_clicks' in data, "Missing 'total_clicks' field"
        assert 'series' in data, "Missing 'series' field"
        assert data['total_clicks'] >= 3, f"Expected >=3 clicks, got {data['total_clicks']}"
        
        # Check today's bucket
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_point = next((p for p in data['series'] if p['date'] == today), None)
        assert today_point is not None, f"Today's date {today} not in series"
        assert today_point['clicks'] >= 3, f"Expected >=3 clicks today, got {today_point['clicks']}"
        
        self.log(f"   Analytics: {data['total_clicks']} total clicks, today={today_point['clicks']}")
    
    def test_analytics_series_length(self):
        """GET /api/links/{code}/analytics?days=7 - series length clamped 7-90"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/series-test"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Test days=7
        resp = requests.get(f"{BASE_URL}/links/{code}/analytics", params={"days": 7}, cookies=cookies)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data['series']) == 7, f"Expected 7 days, got {len(data['series'])}"
        
        # Test days=90
        resp = requests.get(f"{BASE_URL}/links/{code}/analytics", params={"days": 90}, cookies=cookies)
        data = resp.json()
        assert len(data['series']) == 90, f"Expected 90 days, got {len(data['series'])}"
        
        # Test days=5 (should clamp to 7)
        resp = requests.get(f"{BASE_URL}/links/{code}/analytics", params={"days": 5}, cookies=cookies)
        data = resp.json()
        assert len(data['series']) == 7, f"Expected 7 days (clamped), got {len(data['series'])}"
        
        self.log(f"   Analytics series length clamping works correctly")
    
    def test_analytics_404_unknown_code(self):
        """GET /api/links/nonexistent/analytics - should return 404"""
        cookies = {'session_token': self.session_token}
        resp = requests.get(f"{BASE_URL}/links/nonexistent-xyz/analytics", cookies=cookies)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        self.log(f"   Correctly returned 404 for nonexistent code analytics")
    
    def test_analytics_403_owned_link_by_anon(self):
        """GET /api/links/{code}/analytics on owned link by anon - should return 403"""
        cookies = {'session_token': self.session_token}
        # Create owned link
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/owned-analytics"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Try to access analytics without auth
        resp = requests.get(f"{BASE_URL}/links/{code}/analytics")
        assert resp.status_code == 403, f"Expected 403 for anon accessing owned link analytics, got {resp.status_code}"
        self.log(f"   Correctly returned 403 for anon accessing owned link analytics")
    
    def test_analytics_anonymous_link_accessible(self):
        """GET /api/links/{code}/analytics on anonymous link - accessible to anyone"""
        # Create anonymous link
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/anon-analytics"})
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Access analytics without auth - should work
        resp = requests.get(f"{BASE_URL}/links/{code}/analytics")
        assert resp.status_code == 200, f"Expected 200 for anon link analytics, got {resp.status_code}"
        data = resp.json()
        assert 'total_clicks' in data
        self.log(f"   Anonymous link analytics accessible to anyone")
    
    # ========== PHASE 6: LINK EDITING TESTS ==========
    
    def test_edit_url_cache_invalidation(self):
        """PATCH /api/links/{code} changes URL and invalidates cache"""
        cookies = {'session_token': self.session_token}
        # Create link
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/original"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Edit URL
        new_url = "https://example.com/updated"
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={"url": new_url}, cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data['url'] == new_url, f"Expected URL={new_url}, got {data['url']}"
        assert data['code'] == code, "Short code should not change"
        
        # Verify resolve returns new URL (cache invalidation)
        resp = requests.get(f"{BASE_URL}/resolve/{code}")
        assert resp.status_code == 200
        assert resp.json()['url'] == new_url, f"Resolve should return new URL"
        
        self.log(f"   Edit URL successful, cache invalidated, resolve returns new URL")
    
    def test_edit_set_future_expiry(self):
        """PATCH /api/links/{code} sets future expiry"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/edit-expiry"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Set expiry
        future = datetime.now(timezone.utc) + timedelta(days=7)
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={"expires_at": future.isoformat()}, cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data['expires_at'] is not None, "expires_at should be set"
        self.log(f"   Set future expiry successfully")
    
    def test_edit_clear_expiry(self):
        """PATCH /api/links/{code} with clear_expiry:true removes expiry"""
        cookies = {'session_token': self.session_token}
        # Create link with expiry
        future = datetime.now(timezone.utc) + timedelta(days=7)
        resp = requests.post(f"{BASE_URL}/shorten", json={
            "url": "https://example.com/clear-expiry",
            "expires_at": future.isoformat()
        }, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Clear expiry
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={"clear_expiry": True}, cookies=cookies)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        data = resp.json()
        assert data['expires_at'] is None, "expires_at should be None after clear_expiry"
        self.log(f"   Clear expiry successful")
    
    def test_edit_past_expiry_422(self):
        """PATCH /api/links/{code} with past expiry - should return 422"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/edit-past"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        past = datetime.now(timezone.utc) - timedelta(days=1)
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={"expires_at": past.isoformat()}, cookies=cookies)
        assert resp.status_code == 422, f"Expected 422 for past expiry, got {resp.status_code}"
        self.log(f"   Correctly returned 422 for past expiry")
    
    def test_edit_invalid_url_422(self):
        """PATCH /api/links/{code} with invalid URL - should return 422"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/edit-invalid"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={"url": "notaurl"}, cookies=cookies)
        assert resp.status_code == 422, f"Expected 422 for invalid URL, got {resp.status_code}"
        self.log(f"   Correctly returned 422 for invalid URL")
    
    def test_edit_empty_body_422(self):
        """PATCH /api/links/{code} with empty body - should return 422 'Nothing to update'"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/edit-empty"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={}, cookies=cookies)
        assert resp.status_code == 422, f"Expected 422 for empty body, got {resp.status_code}"
        assert 'Nothing to update' in resp.text, "Should return 'Nothing to update' message"
        self.log(f"   Correctly returned 422 for empty update body")
    
    def test_edit_403_anon_editing_owned_link(self):
        """PATCH /api/links/{code} anon editing owned link - should return 403"""
        cookies = {'session_token': self.session_token}
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/owned-edit"}, cookies=cookies)
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Try to edit without auth
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={"url": "https://example.com/hacked"})
        assert resp.status_code == 403, f"Expected 403 for anon editing owned link, got {resp.status_code}"
        self.log(f"   Correctly returned 403 for anon editing owned link")
    
    def test_edit_404_unknown_code(self):
        """PATCH /api/links/nonexistent - should return 404"""
        cookies = {'session_token': self.session_token}
        resp = requests.patch(f"{BASE_URL}/links/nonexistent-xyz", json={"url": "https://example.com"}, cookies=cookies)
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}"
        self.log(f"   Correctly returned 404 for nonexistent code")
    
    def test_edit_anonymous_link_by_anon(self):
        """PATCH /api/links/{code} anonymous link editable by anon"""
        # Create anonymous link
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/anon-edit"})
        code = resp.json()['code']
        self.created_codes.append(code)
        
        # Edit without auth - should work
        resp = requests.patch(f"{BASE_URL}/links/{code}", json={"url": "https://example.com/anon-edited"})
        assert resp.status_code == 200, f"Expected 200 for anon editing anon link, got {resp.status_code}"
        data = resp.json()
        assert data['url'] == "https://example.com/anon-edited"
        self.log(f"   Anonymous link editable by anyone")
    
    # ========== PHASE 6: ANONYMOUS RATE LIMIT REGRESSION ==========
    
    def test_anonymous_rate_limit_10_per_min(self):
        """Anonymous rate limit: 10 creates/min per IP - should return 429 after 10"""
        # Use a unique X-Forwarded-For IP to avoid conflicts with other tests
        test_ip = f"192.168.100.{int(time.time()) % 255}"
        headers = {'X-Forwarded-For': test_ip}
        
        # Create 10 links rapidly
        for i in range(10):
            resp = requests.post(f"{BASE_URL}/shorten", json={"url": f"https://example.com/ratelimit{i}"}, headers=headers)
            if resp.status_code == 200:
                self.created_codes.append(resp.json()['code'])
        
        # 11th request should get 429
        resp = requests.post(f"{BASE_URL}/shorten", json={"url": "https://example.com/ratelimit11"}, headers=headers)
        assert resp.status_code == 429, f"Expected 429 after 10 requests, got {resp.status_code}"
        assert 'Retry-After' in resp.headers, "Missing Retry-After header"
        self.log(f"   Anonymous rate limit working: 429 after 10 requests from IP {test_ip}")
    
    def run_all_tests(self):
        """Run all tests in order"""
        self.log("=" * 60, Colors.BLUE)
        self.log("LinkMint Backend API Test Suite - Phase 1-6", Colors.BLUE)
        self.log(f"Testing: {BASE_URL}", Colors.BLUE)
        self.log("=" * 60, Colors.BLUE)
        
        # Phase 1-3: Core shortener (regression tests)
        self.log("\n📦 PHASE 1-3: Core Shortener (Regression)", Colors.YELLOW)
        self.test("Health check", self.test_health_check)
        self.test("Shorten plain URL (auto https://)", self.test_shorten_plain_url)
        self.test("Shorten with custom alias (success)", self.test_shorten_with_custom_alias_success)
        self.test("Shorten with duplicate alias (409)", self.test_shorten_duplicate_alias)
        self.test("Shorten with invalid alias (422)", self.test_shorten_invalid_alias)
        self.test("Shorten with reserved alias (409)", self.test_shorten_reserved_alias)
        self.test("Shorten with invalid URL (422)", self.test_shorten_invalid_url)
        self.test("Shorten with future expiry", self.test_shorten_with_future_expiry)
        self.test("Shorten with past expiry (422)", self.test_shorten_with_past_expiry)
        self.test("Resolve code and increment clicks", self.test_resolve_code)
        self.test("Resolve nonexistent code (404)", self.test_resolve_nonexistent)
        self.test("Redirect endpoint (302)", self.test_redirect_endpoint)
        self.test("Expired link returns 410", self.test_expired_link)
        self.test("List links (sorted)", self.test_list_links)
        self.test("Delete link", self.test_delete_link)
        self.test("Delete nonexistent link (404)", self.test_delete_nonexistent)
        self.test("Stats endpoint", self.test_stats)
        
        # Phase 4: Auth
        self.log("\n🔐 PHASE 4: Authentication", Colors.YELLOW)
        self.test("Register new user (success)", self.test_auth_register_success)
        self.test("Register duplicate email (409)", self.test_auth_register_duplicate_email)
        self.test("Register short password (422)", self.test_auth_register_short_password)
        self.test("Register invalid email (422)", self.test_auth_register_invalid_email)
        self.test("Login with correct credentials", self.test_auth_login_success)
        self.test("Login with wrong password (401)", self.test_auth_login_wrong_password)
        self.test("GET /auth/me with cookie", self.test_auth_me_with_cookie)
        self.test("GET /auth/me with Bearer token", self.test_auth_me_with_bearer_token)
        self.test("GET /auth/me without session (401)", self.test_auth_me_no_session)
        self.test("Logout and verify session deleted", self.test_auth_logout)
        self.test("POST /auth/session with fake session_id", self.test_auth_session_invalid)
        
        # Phase 4: Ownership
        self.log("\n👤 PHASE 4: Ownership & Permissions", Colors.YELLOW)
        self.test("Shorten while authenticated sets owner_id", self.test_ownership_shorten_authenticated)
        self.test("GET /links authenticated returns user's links", self.test_ownership_list_links_authenticated)
        self.test("GET /links anonymous returns anonymous links", self.test_ownership_list_links_anonymous)
        self.test("DELETE own link (success)", self.test_ownership_delete_own_link)
        self.test("DELETE other user's link (403)", self.test_ownership_delete_other_user_link_403)
        self.test("DELETE anonymous link by anyone", self.test_ownership_delete_anonymous_link_by_anyone)
        
        # Phase 4: Search & Pagination
        self.log("\n🔍 PHASE 4: Search & Pagination", Colors.YELLOW)
        self.test("Search by code (case-insensitive)", self.test_search_by_code)
        self.test("Search by URL (case-insensitive)", self.test_search_by_url)
        self.test("Pagination with page & limit", self.test_pagination)
        
        # Phase 4: Stats scoping
        self.log("\n📊 PHASE 4: Stats Scoping", Colors.YELLOW)
        self.test("Stats scoped to authenticated user", self.test_stats_scoped_authenticated)
        self.test("Stats scoped to anonymous links", self.test_stats_scoped_anonymous)
        
        # Phase 4: QR codes
        self.log("\n📱 PHASE 4: QR Codes", Colors.YELLOW)
        self.test("GET /qr/{code} returns image/png", self.test_qr_code_success)
        self.test("GET /qr/nonexistent returns 404", self.test_qr_code_nonexistent)
        
        # Phase 6: Bulk Shortening
        self.log("\n📦 PHASE 6: Bulk Shortening", Colors.YELLOW)
        self.test("Bulk anonymous returns 401", self.test_bulk_anonymous_401)
        self.test("Bulk authenticated success", self.test_bulk_authenticated_success)
        self.test("Bulk with mixed valid/invalid URLs", self.test_bulk_mixed_urls)
        self.test("Bulk empty list returns 422", self.test_bulk_empty_list_422)
        self.test("Bulk >50 URLs returns 422", self.test_bulk_over_50_urls_422)
        
        # Phase 6: Analytics
        self.log("\n📊 PHASE 6: Click Analytics", Colors.YELLOW)
        self.test("Analytics click tracking (total + daily)", self.test_analytics_click_tracking)
        self.test("Analytics series length clamping (7-90)", self.test_analytics_series_length)
        self.test("Analytics 404 for unknown code", self.test_analytics_404_unknown_code)
        self.test("Analytics 403 for anon accessing owned link", self.test_analytics_403_owned_link_by_anon)
        self.test("Analytics accessible for anonymous links", self.test_analytics_anonymous_link_accessible)
        
        # Phase 6: Link Editing
        self.log("\n✏️ PHASE 6: Link Editing", Colors.YELLOW)
        self.test("Edit URL and cache invalidation", self.test_edit_url_cache_invalidation)
        self.test("Edit set future expiry", self.test_edit_set_future_expiry)
        self.test("Edit clear expiry", self.test_edit_clear_expiry)
        self.test("Edit past expiry returns 422", self.test_edit_past_expiry_422)
        self.test("Edit invalid URL returns 422", self.test_edit_invalid_url_422)
        self.test("Edit empty body returns 422", self.test_edit_empty_body_422)
        self.test("Edit 403 for anon editing owned link", self.test_edit_403_anon_editing_owned_link)
        self.test("Edit 404 for unknown code", self.test_edit_404_unknown_code)
        self.test("Edit anonymous link by anon", self.test_edit_anonymous_link_by_anon)
        
        # Phase 6: Rate Limit Regression
        self.log("\n🚦 PHASE 6: Rate Limit Regression", Colors.YELLOW)
        self.test("Anonymous rate limit 10/min per IP", self.test_anonymous_rate_limit_10_per_min)
        
        # Cleanup
        self.cleanup()
        
        # Summary
        self.log("\n" + "=" * 60, Colors.BLUE)
        self.log("TEST SUMMARY", Colors.BLUE)
        self.log("=" * 60, Colors.BLUE)
        self.log(f"Total tests: {self.tests_run}")
        self.log(f"Passed: {self.tests_passed}", Colors.GREEN)
        self.log(f"Failed: {self.tests_failed}", Colors.RED if self.tests_failed > 0 else Colors.GREEN)
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"Success rate: {success_rate:.1f}%", Colors.GREEN if success_rate == 100 else Colors.YELLOW)
        
        return 0 if self.tests_failed == 0 else 1

if __name__ == "__main__":
    tester = LinkMintTester()
    sys.exit(tester.run_all_tests())
