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
        
        # Check clicks incremented
        time.sleep(0.5)  # Give DB time to update
        resp = requests.get(f"{BASE_URL}/links")
        links = resp.json()
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
        """GET /api/links - should return list sorted newest first"""
        resp = requests.get(f"{BASE_URL}/links")
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
        links = resp.json()
        assert isinstance(links, list), "Response should be a list"
        
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
        
        self.log(f"   Retrieved {len(links)} links, sorted correctly")
    
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
    
    def run_all_tests(self):
        """Run all tests in order"""
        self.log("=" * 60, Colors.BLUE)
        self.log("LinkMint Backend API Test Suite", Colors.BLUE)
        self.log(f"Testing: {BASE_URL}", Colors.BLUE)
        self.log("=" * 60, Colors.BLUE)
        
        # Run tests
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
