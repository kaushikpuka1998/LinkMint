# Auth-Gated App Testing Playbook

NOTE - Do not be satisfied until you've tested the app completely especially the auth gated pages

## Step 1: Create Test User & Session
```bash
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API
```bash
curl -X GET "https://your-app.com/api/auth/me" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

## Step 3: Browser Testing
```javascript
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "your-app.com",
    "path": "/",
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
}]);
await page.goto("https://your-app.com");
```

## Quick Debug
```bash
mongosh --eval "use('test_database'); db.users.find().limit(2).pretty(); db.user_sessions.find().limit(2).pretty();"
mongosh --eval "use('test_database'); db.users.deleteMany({email: /test\.user\./}); db.user_sessions.deleteMany({session_token: /test_session/});"
```

## Checklist
- User document has user_id field (custom UUID, MongoDB's _id is separate)
- Session user_id matches user's user_id exactly
- All queries use `{"_id": 0}` projection
- Backend queries use user_id (not _id or id)
- /api/auth/me returns user data
- Dashboard loads without redirect
- CRUD operations work

## App-specific notes (LinkMint)
- Email/password auth ALSO uses the same session token mechanism (user_sessions collection + session_token cookie/bearer).
- Anonymous link shortening is allowed; signed-in users see only their own links.
