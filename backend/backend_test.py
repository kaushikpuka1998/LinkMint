#!/usr/bin/env python3
"""
LinkMint Phase 7 Backend Testing
Tests: Tags (create, edit, filter, validation), CSV Export, Regression
"""
import requests
import sys
import time
from datetime import datetime

BASE_URL = "https://go-shortlink.preview.emergentagent.com/api"

class TestRunner:
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.token = None
        self.user_email = None
        self.failures = []

    def log(self, msg, level="INFO"):
        print(f"[{level}] {msg}")

    def test(self, name, fn):
        """Run a single test function"""
        self.tests_run += 1
        self.log(f"\n{'='*60}")
        self.log(f"Test {self.tests_run}: {name}")
        self.log('='*60)
        try:
            fn()
            self.tests_passed += 1
            self.log(f"✅ PASSED: {name}", "PASS")
            return True
        except AssertionError as e:
            self.tests_failed += 1
            self.log(f"❌ FAILED: {name} - {str(e)}", "FAIL")
            self.failures.append(f"{name}: {str(e)}")
            return False
        except Exception as e:
            self.tests_failed += 1
            self.log(f"❌ ERROR: {name} - {str(e)}", "ERROR")
            self.failures.append(f"{name}: {str(e)}")
            return False

    def api_call(self, method, endpoint, expected_status=None, data=None, headers=None, params=None):
        """Make API call and optionally assert status"""
        url = f"{BASE_URL}{endpoint}"
        h = headers or {}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        
        self.log(f"{method} {endpoint}", "API")
        
        try:
            if method == 'GET':
                resp = requests.get(url, headers=h, params=params, timeout=10)
            elif method == 'POST':
                resp = requests.post(url, json=data, headers=h, params=params, timeout=10)
            elif method == 'PATCH':
                resp = requests.patch(url, json=data, headers=h, params=params, timeout=10)
            elif method == 'DELETE':
                resp = requests.delete(url, headers=h, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            self.log(f"Response: {resp.status_code}", "API")
            
            if expected_status is not None:
                assert resp.status_code == expected_status, \
                    f"Expected {expected_status}, got {resp.status_code}. Body: {resp.text[:200]}"
            
            return resp
        except requests.exceptions.RequestException as e:
            raise Exception(f"API call failed: {str(e)}")

    def login(self, email="neo@test.com", password="secret123"):
        """Login and store token"""
        self.log(f"Logging in as {email}")
        resp = self.api_call('POST', '/auth/login', 200, {'email': email, 'password': password})
        data = resp.json()
        self.user_email = data['email']
        # Token is in cookie, but we'll use Bearer for testing
        # Extract from Set-Cookie header
        cookies = resp.cookies
        if 'session_token' in cookies:
            self.token = cookies['session_token']
            self.log(f"Logged in as {self.user_email}")
        else:
            raise Exception("No session_token in response")

    def summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total: {self.tests_run}")
        print(f"Passed: {self.tests_passed} ✅")
        print(f"Failed: {self.tests_failed} ❌")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        if self.failures:
            print("\nFAILURES:")
            for f in self.failures:
                print(f"  - {f}")
        
        return 0 if self.tests_failed == 0 else 1


def main():
    runner = TestRunner()
    
    # ========================================================================
    # PHASE 7: TAGS BACKEND TESTS
    # ========================================================================
    
    def test_tags_create_with_deduping():
        """POST /api/shorten with tags ['Marketing',' launch ','marketing'] -> deduped/trimmed to ['Marketing','launch']"""
        runner.login()
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-tags-dedupe',
            'tags': ['Marketing', ' launch ', 'marketing']  # case-insensitive dedupe
        })
        data = resp.json()
        assert 'tags' in data, "Response missing tags field"
        tags = data['tags']
        assert len(tags) == 2, f"Expected 2 tags after dedupe, got {len(tags)}: {tags}"
        # Should keep first occurrence case
        assert 'Marketing' in tags, f"Expected 'Marketing' in {tags}"
        assert 'launch' in tags, f"Expected 'launch' in {tags}"
        runner.log(f"✓ Tags deduped correctly: {tags}")
    
    def test_tags_invalid_chars():
        """Invalid tag chars (e.g. 'bad!tag@') -> 422"""
        runner.login()
        resp = runner.api_call('POST', '/shorten', 422, {
            'url': 'https://example.com/test-invalid-tag',
            'tags': ['bad!tag@']
        })
        data = resp.json()
        assert 'detail' in data, "Expected error detail"
        assert 'Invalid tag' in data['detail'], f"Expected 'Invalid tag' in error: {data['detail']}"
        runner.log(f"✓ Invalid tag rejected: {data['detail']}")
    
    def test_tags_too_long():
        """Tags >24 chars -> 422"""
        runner.login()
        long_tag = 'a' * 25
        resp = runner.api_call('POST', '/shorten', 422, {
            'url': 'https://example.com/test-long-tag',
            'tags': [long_tag]
        })
        data = resp.json()
        assert 'detail' in data, "Expected error detail"
        assert 'Invalid tag' in data['detail'], f"Expected 'Invalid tag' in error: {data['detail']}"
        runner.log(f"✓ Long tag rejected: {data['detail']}")
    
    def test_tags_max_five():
        """Max 5 tags enforced"""
        runner.login()
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-max-tags',
            'tags': ['tag1', 'tag2', 'tag3', 'tag4', 'tag5', 'tag6', 'tag7']
        })
        data = resp.json()
        assert len(data['tags']) == 5, f"Expected max 5 tags, got {len(data['tags'])}"
        runner.log(f"✓ Max 5 tags enforced: {data['tags']}")
    
    def test_tags_patch_replace():
        """PATCH /api/links/{code} with tags replaces list"""
        runner.login()
        # Create link with tags
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-patch-tags',
            'tags': ['old1', 'old2']
        })
        code = resp.json()['code']
        
        # Update tags
        resp = runner.api_call('PATCH', f'/links/{code}', 200, {
            'tags': ['new1', 'new2', 'new3']
        })
        data = resp.json()
        assert data['tags'] == ['new1', 'new2', 'new3'], f"Expected replaced tags, got {data['tags']}"
        runner.log(f"✓ Tags replaced: {data['tags']}")
    
    def test_tags_patch_clear():
        """PATCH with tags:[] clears tags"""
        runner.login()
        # Create link with tags
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-clear-tags',
            'tags': ['tag1', 'tag2']
        })
        code = resp.json()['code']
        
        # Clear tags
        resp = runner.api_call('PATCH', f'/links/{code}', 200, {
            'tags': []
        })
        data = resp.json()
        assert data['tags'] == [], f"Expected empty tags, got {data['tags']}"
        runner.log(f"✓ Tags cleared")
    
    def test_get_tags_distinct():
        """GET /api/tags returns distinct sorted tags scoped to caller"""
        runner.login()
        # Create a few links with tags
        runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-tags-1',
            'tags': ['alpha', 'beta']
        })
        runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-tags-2',
            'tags': ['beta', 'gamma']  # beta is duplicate
        })
        
        resp = runner.api_call('GET', '/tags', 200)
        tags = resp.json()
        assert isinstance(tags, list), f"Expected list, got {type(tags)}"
        assert 'alpha' in tags, f"Expected 'alpha' in {tags}"
        assert 'beta' in tags, f"Expected 'beta' in {tags}"
        assert 'gamma' in tags, f"Expected 'gamma' in {tags}"
        # Check sorted (case-insensitive)
        sorted_tags = sorted(tags, key=str.lower)
        assert tags == sorted_tags, f"Expected sorted tags, got {tags}"
        runner.log(f"✓ Distinct tags: {tags}")
    
    def test_filter_by_tag_case_insensitive():
        """GET /api/links?tag=MARKETING filters case-insensitively"""
        runner.login()
        # Create link with tag 'marketing'
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-filter-tag',
            'tags': ['marketing']
        })
        code = resp.json()['code']
        
        # Filter by uppercase
        resp = runner.api_call('GET', '/links', 200, params={'tag': 'MARKETING'})
        data = resp.json()
        codes = [item['code'] for item in data['items']]
        assert code in codes, f"Expected {code} in filtered results"
        runner.log(f"✓ Case-insensitive tag filter works")
    
    def test_combined_q_and_tag_filters():
        """Combined q + tag filters work together"""
        runner.login()
        # Create link with specific code and tag
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-combined-filter',
            'custom_alias': 'testcombined123',
            'tags': ['special']
        })
        
        # Filter by both q and tag
        resp = runner.api_call('GET', '/links', 200, params={'q': 'testcombined', 'tag': 'special'})
        data = resp.json()
        assert data['total'] >= 1, f"Expected at least 1 result, got {data['total']}"
        codes = [item['code'] for item in data['items']]
        assert 'testcombined123' in codes, f"Expected testcombined123 in {codes}"
        runner.log(f"✓ Combined q+tag filter works")
    
    # ========================================================================
    # PHASE 7: CSV EXPORT TESTS
    # ========================================================================
    
    def test_csv_export_format():
        """GET /api/links/export.csv returns text/csv with proper headers"""
        runner.login()
        resp = runner.api_call('GET', '/links/export.csv', 200)
        
        # Check content type
        content_type = resp.headers.get('Content-Type', '')
        assert 'text/csv' in content_type, f"Expected text/csv, got {content_type}"
        
        # Check Content-Disposition
        disposition = resp.headers.get('Content-Disposition', '')
        assert 'attachment' in disposition, f"Expected attachment in {disposition}"
        
        # Check CSV content
        csv_text = resp.text
        lines = csv_text.strip().split('\n')
        assert len(lines) >= 1, "Expected at least header row"
        
        header = lines[0]
        expected_cols = ['code', 'short_url', 'destination_url', 'clicks', 'tags', 'created_at', 'expires_at', 'status']
        for col in expected_cols:
            assert col in header, f"Expected '{col}' in header: {header}"
        
        runner.log(f"✓ CSV format correct, {len(lines)} rows")
    
    def test_csv_export_auth_scoping():
        """Authed export contains only own links"""
        runner.login()
        # Create a link
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-csv-auth',
            'custom_alias': 'csvauth123'
        })
        
        # Export CSV
        resp = runner.api_call('GET', '/links/export.csv', 200)
        csv_text = resp.text
        
        # Should contain our link
        assert 'csvauth123' in csv_text, f"Expected csvauth123 in CSV"
        runner.log(f"✓ CSV contains own links")
    
    def test_csv_export_with_filters():
        """?tag= and ?q= filters apply to CSV export"""
        runner.login()
        # Create link with tag
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-csv-filter',
            'custom_alias': 'csvfilter123',
            'tags': ['exporttest']
        })
        
        # Export with tag filter
        resp = runner.api_call('GET', '/links/export.csv', 200, params={'tag': 'exporttest'})
        csv_text = resp.text
        
        assert 'csvfilter123' in csv_text, f"Expected csvfilter123 in filtered CSV"
        runner.log(f"✓ CSV filters work")
    
    def test_csv_tags_joined_with_pipe():
        """Tags in CSV are joined with '|'"""
        runner.login()
        # Create link with multiple tags
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/test-csv-tags',
            'custom_alias': 'csvtags123',
            'tags': ['tag1', 'tag2', 'tag3']
        })
        
        # Export CSV
        resp = runner.api_call('GET', '/links/export.csv', 200)
        csv_text = resp.text
        
        # Find the row with our link
        for line in csv_text.split('\n'):
            if 'csvtags123' in line:
                assert 'tag1|tag2|tag3' in line, f"Expected 'tag1|tag2|tag3' in line: {line}"
                runner.log(f"✓ Tags joined with pipe: {line}")
                break
        else:
            raise AssertionError("Link not found in CSV")
    
    # ========================================================================
    # REGRESSION TESTS
    # ========================================================================
    
    def test_regression_shorten():
        """Basic shorten still works"""
        runner.login()
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/regression-test'
        })
        data = resp.json()
        assert 'code' in data, "Missing code in response"
        assert 'url' in data, "Missing url in response"
        runner.log(f"✓ Shorten works: /{data['code']}")
    
    def test_regression_resolve():
        """Resolve still works"""
        runner.login()
        # Create link
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/regression-resolve'
        })
        code = resp.json()['code']
        
        # Resolve it
        resp = runner.api_call('GET', f'/resolve/{code}', 200)
        data = resp.json()
        assert data['url'] == 'https://example.com/regression-resolve', f"Wrong URL: {data['url']}"
        runner.log(f"✓ Resolve works")
    
    def test_regression_stats():
        """Stats endpoint still works"""
        runner.login()
        resp = runner.api_call('GET', '/stats', 200)
        data = resp.json()
        assert 'total_links' in data, "Missing total_links"
        assert 'total_clicks' in data, "Missing total_clicks"
        assert 'active_links' in data, "Missing active_links"
        runner.log(f"✓ Stats: {data}")
    
    def test_regression_pagination():
        """Pagination still works"""
        runner.login()
        resp = runner.api_call('GET', '/links', 200, params={'page': 1, 'limit': 5})
        data = resp.json()
        assert 'items' in data, "Missing items"
        assert 'total' in data, "Missing total"
        assert 'page' in data, "Missing page"
        assert 'pages' in data, "Missing pages"
        runner.log(f"✓ Pagination: page {data['page']}/{data['pages']}, {data['total']} total")
    
    def test_regression_qr():
        """QR endpoint still works"""
        runner.login()
        # Create link
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/regression-qr'
        })
        code = resp.json()['code']
        
        # Get QR
        resp = runner.api_call('GET', f'/qr/{code}', 200)
        assert resp.headers.get('Content-Type') == 'image/png', "Expected image/png"
        assert len(resp.content) > 0, "Empty QR image"
        runner.log(f"✓ QR code generated, {len(resp.content)} bytes")
    
    def test_regression_analytics():
        """Analytics endpoint still works"""
        runner.login()
        # Create link
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/regression-analytics'
        })
        code = resp.json()['code']
        
        # Get analytics
        resp = runner.api_call('GET', f'/links/{code}/analytics', 200)
        data = resp.json()
        assert 'total_clicks' in data, "Missing total_clicks"
        assert 'series' in data, "Missing series"
        runner.log(f"✓ Analytics: {data['total_clicks']} clicks")
    
    def test_regression_edit():
        """Edit link still works"""
        runner.login()
        # Create link
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/regression-edit-old'
        })
        code = resp.json()['code']
        
        # Edit it
        resp = runner.api_call('PATCH', f'/links/{code}', 200, {
            'url': 'https://example.com/regression-edit-new'
        })
        data = resp.json()
        assert data['url'] == 'https://example.com/regression-edit-new', f"URL not updated: {data['url']}"
        runner.log(f"✓ Edit works")
    
    def test_regression_delete():
        """Delete link still works"""
        runner.login()
        # Create link
        resp = runner.api_call('POST', '/shorten', 200, {
            'url': 'https://example.com/regression-delete'
        })
        code = resp.json()['code']
        
        # Delete it
        resp = runner.api_call('DELETE', f'/links/{code}', 200)
        data = resp.json()
        assert data['deleted'] == True, "Delete failed"
        
        # Verify it's gone
        resp = runner.api_call('GET', f'/resolve/{code}', 404)
        runner.log(f"✓ Delete works")
    
    def test_regression_bulk_shorten():
        """Bulk shorten still works"""
        runner.login()
        resp = runner.api_call('POST', '/shorten/bulk', 200, {
            'urls': [
                'https://example.com/bulk1',
                'https://example.com/bulk2',
                'https://example.com/bulk3'
            ]
        })
        data = resp.json()
        assert 'results' in data, "Missing results"
        assert data['created'] == 3, f"Expected 3 created, got {data['created']}"
        runner.log(f"✓ Bulk shorten: {data['created']} created")
    
    def test_regression_rate_limit_anon():
        """Anonymous rate limit still enforced (test with different IPs)"""
        # Test without auth, using different X-Forwarded-For IPs
        test_ip = f"192.168.1.{int(time.time()) % 255}"
        headers = {'X-Forwarded-For': test_ip}
        
        # Create 10 links (should succeed)
        for i in range(10):
            resp = requests.post(f"{BASE_URL}/shorten", 
                json={'url': f'https://example.com/ratelimit-{i}'},
                headers=headers,
                timeout=10)
            assert resp.status_code == 200, f"Request {i+1} failed: {resp.status_code}"
        
        # 11th should fail with 429
        resp = requests.post(f"{BASE_URL}/shorten",
            json={'url': 'https://example.com/ratelimit-11'},
            headers=headers,
            timeout=10)
        assert resp.status_code == 429, f"Expected 429, got {resp.status_code}"
        runner.log(f"✓ Rate limit enforced (429 on 11th request)")
    
    def test_regression_auth_login():
        """Auth login still works"""
        resp = runner.api_call('POST', '/auth/login', 200, {
            'email': 'neo@test.com',
            'password': 'secret123'
        })
        data = resp.json()
        assert 'email' in data, "Missing email"
        assert data['email'] == 'neo@test.com', f"Wrong email: {data['email']}"
        runner.log(f"✓ Login works: {data['email']}")
    
    # ========================================================================
    # RUN ALL TESTS
    # ========================================================================
    
    runner.log("Starting LinkMint Phase 7 Backend Tests")
    runner.log(f"Base URL: {BASE_URL}")
    
    # Tags tests
    runner.test("Tags: Create with deduping", test_tags_create_with_deduping)
    runner.test("Tags: Invalid chars rejected", test_tags_invalid_chars)
    runner.test("Tags: Too long rejected", test_tags_too_long)
    runner.test("Tags: Max 5 enforced", test_tags_max_five)
    runner.test("Tags: PATCH replaces list", test_tags_patch_replace)
    runner.test("Tags: PATCH clears with []", test_tags_patch_clear)
    runner.test("Tags: GET /tags distinct sorted", test_get_tags_distinct)
    runner.test("Tags: Filter case-insensitive", test_filter_by_tag_case_insensitive)
    runner.test("Tags: Combined q+tag filters", test_combined_q_and_tag_filters)
    
    # CSV export tests
    runner.test("CSV: Export format", test_csv_export_format)
    runner.test("CSV: Auth scoping", test_csv_export_auth_scoping)
    runner.test("CSV: Filters apply", test_csv_export_with_filters)
    runner.test("CSV: Tags joined with pipe", test_csv_tags_joined_with_pipe)
    
    # Regression tests
    runner.test("Regression: Shorten", test_regression_shorten)
    runner.test("Regression: Resolve", test_regression_resolve)
    runner.test("Regression: Stats", test_regression_stats)
    runner.test("Regression: Pagination", test_regression_pagination)
    runner.test("Regression: QR", test_regression_qr)
    runner.test("Regression: Analytics", test_regression_analytics)
    runner.test("Regression: Edit", test_regression_edit)
    runner.test("Regression: Delete", test_regression_delete)
    runner.test("Regression: Bulk shorten", test_regression_bulk_shorten)
    runner.test("Regression: Rate limit", test_regression_rate_limit_anon)
    runner.test("Regression: Auth login", test_regression_auth_login)
    
    return runner.summary()


if __name__ == '__main__':
    sys.exit(main())
