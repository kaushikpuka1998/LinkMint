from fastapi import FastAPI, APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import json
import math
import random
import string
import secrets
import logging
import time
from io import BytesIO
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

import bcrypt
import httpx
import qrcode
import redis.asyncio as aioredis

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Redis connection (graceful fallback to Mongo if unavailable)
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
redis_client = aioredis.from_url(
    REDIS_URL,
    encoding='utf-8',
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

CACHE_TTL_SECONDS = 3600
SESSION_TTL_DAYS = 7
EMERGENT_SESSION_API = 'https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data'

app = FastAPI(title='LinkMint URL Shortener')
api_router = APIRouter(prefix='/api')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('linkmint')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
BASE62 = string.ascii_letters + string.digits
ALIAS_RE = re.compile(r'^[A-Za-z0-9_-]{3,32}$')
EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
RESERVED_CODES = {
    'api', 'app', 'static', 'admin', 'links', 'stats', 'health', 'assets',
    'auth', 'qr', 'r', 'resolve', 'shorten', 'login', 'register', 'logout',
}


def generate_code(length: int = 6) -> str:
    return ''.join(random.choices(BASE62, k=length))


def normalize_url(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError('URL is required')
    if not re.match(r'^https?://', raw, re.IGNORECASE):
        raw = 'https://' + raw
    parsed = urlparse(raw)
    if not parsed.netloc or '.' not in parsed.netloc:
        raise ValueError('Invalid URL')
    return raw


TAG_RE = re.compile(r'^[A-Za-z0-9 _-]{1,24}$')


def normalize_tags(tags: Optional[List[str]]) -> List[str]:
    """Trim, dedupe (case-insensitive), validate and cap tags at 5."""
    if not tags:
        return []
    result = []
    seen = set()
    for raw in tags:
        tag = str(raw).strip()
        if not tag:
            continue
        if not TAG_RE.match(tag):
            raise HTTPException(
                status_code=422,
                detail=f'Invalid tag "{tag[:24]}" - use up to 24 letters, numbers, spaces, dashes',
            )
        key = tag.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(tag)
        if len(result) >= 5:
            break
    return result


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_dt(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    dt = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_expired(expires_at) -> bool:
    dt = parse_dt(expires_at)
    return dt is not None and dt <= now_utc()


async def cache_get(code: str):
    try:
        raw = await redis_client.get(f'link:{code}')
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set(code: str, payload: dict):
    try:
        await redis_client.set(f'link:{code}', json.dumps(payload), ex=CACHE_TTL_SECONDS)
    except Exception:
        pass


async def cache_delete(code: str):
    try:
        await redis_client.delete(f'link:{code}')
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Rate limiting (anonymous link creation)
# Redis-backed fixed-window counters with in-memory fallback if Redis is down.
# ---------------------------------------------------------------------------
ANON_RATE_LIMITS = [
    ('min', 60, int(os.environ.get('ANON_LIMIT_PER_MIN', '10'))),
    ('hour', 3600, int(os.environ.get('ANON_LIMIT_PER_HOUR', '100'))),
]
_memory_buckets: dict = {}


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get('x-forwarded-for', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else 'unknown'


def _human_wait(seconds: int) -> str:
    if seconds >= 120:
        return f'{seconds // 60} minutes'
    if seconds > 60:
        return 'a couple of minutes'
    return f'{max(1, seconds)} seconds'


async def enforce_anon_rate_limit(request: Request):
    """Raise 429 if an anonymous visitor exceeds creation limits for their IP."""
    ip = get_client_ip(request)
    for suffix, ttl, cap in ANON_RATE_LIMITS:
        key = f'rl:shorten:{ip}:{suffix}'
        count = None
        retry_after = ttl
        try:
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, ttl)
            if count > cap:
                try:
                    retry_after = max(1, await redis_client.ttl(key))
                except Exception:
                    retry_after = ttl
        except Exception:
            # In-memory fixed-window fallback (per-process)
            now = time.time()
            bucket = _memory_buckets.get(key)
            if not bucket or now >= bucket['reset']:
                bucket = {'count': 0, 'reset': now + ttl}
                _memory_buckets[key] = bucket
            bucket['count'] += 1
            count = bucket['count']
            retry_after = max(1, int(bucket['reset'] - now))
        if count > cap:
            logger.warning('Rate limit hit (%s window) for ip=%s', suffix, ip)
            raise HTTPException(
                status_code=429,
                detail=(
                    f'Slow down! Anonymous visitors can create up to {cap} links per '
                    f'{"minute" if suffix == "min" else "hour"}. '
                    f'Try again in {_human_wait(retry_after)}, or sign in for unlimited shortening.'
                ),
                headers={'Retry-After': str(retry_after)},
            )


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


async def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    await db.user_sessions.insert_one({
        'user_id': user_id,
        'session_token': token,
        'created_at': now_utc().isoformat(),
        'expires_at': (now_utc() + timedelta(days=SESSION_TTL_DAYS)).isoformat(),
    })
    return token


def set_session_cookie(response: Response, token: str):
    response.set_cookie(
        key='session_token',
        value=token,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        secure=True,
        samesite='none',
        path='/',
    )


def get_request_token(request: Request) -> Optional[str]:
    token = request.cookies.get('session_token')
    if not token:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
    return token or None


async def get_current_user(request: Request) -> Optional[dict]:
    """Returns user dict or None. Checks session_token cookie first, then Bearer header."""
    token = get_request_token(request)
    if not token:
        return None
    session = await db.user_sessions.find_one({'session_token': token}, {'_id': 0})
    if not session:
        return None
    expires_at = parse_dt(session.get('expires_at'))
    if expires_at is None or expires_at < now_utc():
        await db.user_sessions.delete_one({'session_token': token})
        return None
    user = await db.users.find_one({'user_id': session['user_id']}, {'_id': 0, 'password_hash': 0})
    return user


async def require_user(request: Request) -> dict:
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail='Not authenticated')
    return user


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class LinkCreate(BaseModel):
    url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[str] = None
    tags: Optional[List[str]] = None


class BulkShortenInput(BaseModel):
    urls: List[str]


class BulkShortenItem(BaseModel):
    url: str
    code: Optional[str] = None
    error: Optional[str] = None


class BulkShortenResponse(BaseModel):
    results: List[BulkShortenItem]
    created: int
    failed: int


class LinkUpdate(BaseModel):
    url: Optional[str] = None
    expires_at: Optional[str] = None
    clear_expiry: bool = False
    tags: Optional[List[str]] = None


class DailyPoint(BaseModel):
    date: str
    clicks: int


class AnalyticsResponse(BaseModel):
    code: str
    total_clicks: int
    series: List[DailyPoint]


class Link(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    url: str
    clicks: int = 0
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool = False
    owner_id: Optional[str] = None
    tags: List[str] = []


class PaginatedLinks(BaseModel):
    items: List[Link]
    total: int
    page: int
    pages: int


class ResolveResponse(BaseModel):
    code: str
    url: str


class StatsResponse(BaseModel):
    total_links: int
    total_clicks: int
    active_links: int


class HealthResponse(BaseModel):
    mongo: str
    redis: str


class RegisterInput(BaseModel):
    email: str
    password: str
    name: str


class LoginInput(BaseModel):
    email: str
    password: str


class SessionInput(BaseModel):
    session_id: str


class UserOut(BaseModel):
    model_config = ConfigDict(extra='ignore')

    user_id: str
    email: str
    name: str
    picture: Optional[str] = None


def doc_to_link(doc: dict) -> Link:
    return Link(
        id=doc.get('id', str(uuid.uuid4())),
        code=doc['code'],
        url=doc['url'],
        clicks=int(doc.get('clicks', 0)),
        created_at=doc.get('created_at', ''),
        expires_at=doc.get('expires_at'),
        is_expired=is_expired(doc.get('expires_at')),
        owner_id=doc.get('owner_id'),
        tags=doc.get('tags') or [],
    )


def scope_query(user: Optional[dict]) -> dict:
    """Authenticated users see only their links; anonymous visitors see anonymous links."""
    if user:
        return {'owner_id': user['user_id']}
    return {'owner_id': None}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------
@api_router.post('/auth/register', response_model=UserOut)
async def auth_register(payload: RegisterInput, response: Response):
    email = payload.email.strip().lower()
    name = payload.name.strip()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail='Invalid email address')
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail='Password must be at least 6 characters')
    if not name:
        raise HTTPException(status_code=422, detail='Name is required')

    existing = await db.users.find_one({'email': email}, {'_id': 0})
    if existing:
        if existing.get('password_hash'):
            raise HTTPException(status_code=409, detail='An account with this email already exists')
        # Google-only account: link a password to it
        await db.users.update_one(
            {'user_id': existing['user_id']},
            {'$set': {'password_hash': hash_password(payload.password), 'updated_at': now_utc().isoformat()}},
        )
        user = await db.users.find_one({'user_id': existing['user_id']}, {'_id': 0, 'password_hash': 0})
    else:
        user_id = f'user_{uuid.uuid4().hex[:12]}'
        await db.users.insert_one({
            'user_id': user_id,
            'email': email,
            'name': name,
            'picture': None,
            'password_hash': hash_password(payload.password),
            'created_at': now_utc().isoformat(),
        })
        user = await db.users.find_one({'user_id': user_id}, {'_id': 0, 'password_hash': 0})

    token = await create_session(user['user_id'])
    set_session_cookie(response, token)
    return UserOut(**user)


@api_router.post('/auth/login', response_model=UserOut)
async def auth_login(payload: LoginInput, response: Response):
    email = payload.email.strip().lower()
    user = await db.users.find_one({'email': email}, {'_id': 0})
    if not user or not user.get('password_hash') or not verify_password(payload.password, user['password_hash']):
        raise HTTPException(status_code=401, detail='Invalid email or password')
    token = await create_session(user['user_id'])
    set_session_cookie(response, token)
    user.pop('password_hash', None)
    return UserOut(**user)


@api_router.post('/auth/session', response_model=UserOut)
async def auth_session(payload: SessionInput, response: Response):
    """Exchange Emergent OAuth session_id (from URL fragment) for a session token.
    REMINDER: The session-data call MUST be made from the backend, never the frontend.
    """
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            res = await http.get(EMERGENT_SESSION_API, headers={'X-Session-ID': payload.session_id})
    except Exception:
        raise HTTPException(status_code=502, detail='Could not reach authentication service')
    if res.status_code != 200:
        raise HTTPException(status_code=401, detail='Invalid or expired session')
    data = res.json()
    email = str(data.get('email', '')).strip().lower()
    if not email:
        raise HTTPException(status_code=401, detail='Authentication failed')

    existing = await db.users.find_one({'email': email}, {'_id': 0})
    if existing:
        await db.users.update_one(
            {'user_id': existing['user_id']},
            {'$set': {
                'name': data.get('name') or existing.get('name') or email,
                'picture': data.get('picture') or existing.get('picture'),
                'updated_at': now_utc().isoformat(),
            }},
        )
        user_id = existing['user_id']
    else:
        user_id = f'user_{uuid.uuid4().hex[:12]}'
        await db.users.insert_one({
            'user_id': user_id,
            'email': email,
            'name': data.get('name') or email,
            'picture': data.get('picture'),
            'created_at': now_utc().isoformat(),
        })

    token = await create_session(user_id)
    set_session_cookie(response, token)
    user = await db.users.find_one({'user_id': user_id}, {'_id': 0, 'password_hash': 0})
    return UserOut(**user)


@api_router.get('/auth/me', response_model=UserOut)
async def auth_me(request: Request):
    user = await require_user(request)
    return UserOut(**user)


@api_router.post('/auth/logout')
async def auth_logout(request: Request, response: Response):
    token = get_request_token(request)
    if token:
        await db.user_sessions.delete_one({'session_token': token})
    response.delete_cookie('session_token', path='/')
    return {'logged_out': True}


# ---------------------------------------------------------------------------
# App routes
# ---------------------------------------------------------------------------
@api_router.get('/')
async def root():
    return {'message': 'LinkMint URL Shortener API'}


@api_router.get('/health', response_model=HealthResponse)
async def health():
    mongo_status = 'ok'
    redis_status = 'ok'
    try:
        await db.command('ping')
    except Exception:
        mongo_status = 'down'
    try:
        await redis_client.ping()
    except Exception:
        redis_status = 'down'
    return HealthResponse(mongo=mongo_status, redis=redis_status)


@api_router.post('/shorten', response_model=Link)
async def shorten(payload: LinkCreate, request: Request):
    user = await get_current_user(request)
    if not user:
        await enforce_anon_rate_limit(request)
    try:
        url = normalize_url(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    expires_at = None
    if payload.expires_at:
        try:
            dt = parse_dt(payload.expires_at)
            if dt <= now_utc():
                raise HTTPException(status_code=422, detail='Expiration must be in the future')
            expires_at = dt.isoformat()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=422, detail='Invalid expiration date')

    if payload.custom_alias:
        alias = payload.custom_alias.strip()
        if not ALIAS_RE.match(alias):
            raise HTTPException(
                status_code=422,
                detail='Alias must be 3-32 characters (letters, numbers, dashes, underscores)',
            )
        if alias.lower() in RESERVED_CODES:
            raise HTTPException(status_code=409, detail='This alias is reserved')
        existing = await db.links.find_one({'code': alias}, {'_id': 0})
        if existing:
            raise HTTPException(status_code=409, detail='This alias is already taken')
        code = alias
    else:
        code = generate_code()
        for _ in range(5):
            if not await db.links.find_one({'code': code}, {'_id': 0}):
                break
            code = generate_code()
        else:
            raise HTTPException(status_code=500, detail='Could not generate a unique code')

    doc = {
        'id': str(uuid.uuid4()),
        'code': code,
        'url': url,
        'clicks': 0,
        'created_at': now_utc().isoformat(),
        'expires_at': expires_at,
        'owner_id': user['user_id'] if user else None,
        'tags': normalize_tags(payload.tags),
    }
    await db.links.insert_one(dict(doc))
    await cache_set(code, {'url': url, 'expires_at': expires_at})
    logger.info('Shortened %s -> %s (owner=%s)', url[:80], code, doc['owner_id'])
    return doc_to_link(doc)


@api_router.post('/shorten/bulk', response_model=BulkShortenResponse)
async def shorten_bulk(payload: BulkShortenInput, request: Request):
    user = await require_user(request)  # bulk shortening is for signed-in users only
    raw_urls = [u.strip() for u in payload.urls if u and u.strip()]
    if not raw_urls:
        raise HTTPException(status_code=422, detail='Provide at least one URL')
    if len(raw_urls) > 50:
        raise HTTPException(status_code=422, detail='Maximum 50 URLs per batch')

    results: List[BulkShortenItem] = []
    for raw in raw_urls:
        try:
            url = normalize_url(raw)
        except ValueError as e:
            results.append(BulkShortenItem(url=raw, error=str(e)))
            continue
        code = generate_code()
        for _ in range(5):
            if not await db.links.find_one({'code': code}, {'_id': 0}):
                break
            code = generate_code()
        else:
            results.append(BulkShortenItem(url=url, error='Could not generate a unique code'))
            continue
        doc = {
            'id': str(uuid.uuid4()),
            'code': code,
            'url': url,
            'clicks': 0,
            'created_at': now_utc().isoformat(),
            'expires_at': None,
            'owner_id': user['user_id'],
        }
        await db.links.insert_one(dict(doc))
        await cache_set(code, {'url': url, 'expires_at': None})
        results.append(BulkShortenItem(url=url, code=code))

    created = sum(1 for r in results if r.code)
    logger.info('Bulk shorten by %s: %d created, %d failed', user['user_id'], created, len(results) - created)
    return BulkShortenResponse(results=results, created=created, failed=len(results) - created)


@api_router.patch('/links/{code}', response_model=Link)
async def update_link(code: str, payload: LinkUpdate, request: Request):
    user = await get_current_user(request)
    doc = await db.links.find_one({'code': code}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='Link not found')
    owner_id = doc.get('owner_id')
    if owner_id is not None and (not user or user['user_id'] != owner_id):
        raise HTTPException(status_code=403, detail='You do not own this link')

    updates = {}
    if payload.url is not None and payload.url.strip():
        try:
            updates['url'] = normalize_url(payload.url)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    if payload.clear_expiry:
        updates['expires_at'] = None
    elif payload.expires_at:
        try:
            dt = parse_dt(payload.expires_at)
            if dt <= now_utc():
                raise HTTPException(status_code=422, detail='Expiration must be in the future')
            updates['expires_at'] = dt.isoformat()
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=422, detail='Invalid expiration date')
    if payload.tags is not None:
        updates['tags'] = normalize_tags(payload.tags)
    if not updates:
        raise HTTPException(status_code=422, detail='Nothing to update')

    await db.links.update_one({'code': code}, {'$set': updates})
    doc.update(updates)
    await cache_set(code, {'url': doc['url'], 'expires_at': doc.get('expires_at')})
    logger.info('Updated link %s (fields=%s)', code, list(updates.keys()))
    return doc_to_link(doc)


@api_router.get('/tags', response_model=List[str])
async def list_tags(request: Request):
    """Distinct tags within the caller's link scope, sorted alphabetically."""
    user = await get_current_user(request)
    tags = await db.links.distinct('tags', scope_query(user))
    return sorted([t for t in tags if t], key=str.lower)


@api_router.get('/links/export.csv')
async def export_links_csv(request: Request, q: str = '', tag: str = ''):
    """Export the caller's visible links (same scoping/filters as GET /api/links) as CSV."""
    import csv
    from io import StringIO

    user = await get_current_user(request)
    query = scope_query(user)
    filters = [query]
    q = q.strip()
    if q:
        rx = {'$regex': re.escape(q), '$options': 'i'}
        filters.append({'$or': [{'code': rx}, {'url': rx}]})
    tag = tag.strip()
    if tag:
        filters.append({'tags': {'$regex': f'^{re.escape(tag)}$', '$options': 'i'}})
    query = {'$and': filters} if len(filters) > 1 else query

    proto = request.headers.get('x-forwarded-proto', 'https').split(',')[0].strip()
    host = request.headers.get('x-forwarded-host') or request.headers.get('host', 'localhost')

    docs = await db.links.find(query, {'_id': 0}).sort('created_at', -1).to_list(5000)
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(['code', 'short_url', 'destination_url', 'clicks', 'tags', 'created_at', 'expires_at', 'status'])
    for d in docs:
        writer.writerow([
            d['code'],
            f'{proto}://{host}/{d["code"]}',
            d['url'],
            int(d.get('clicks', 0)),
            '|'.join(d.get('tags') or []),
            d.get('created_at', ''),
            d.get('expires_at') or '',
            'expired' if is_expired(d.get('expires_at')) else 'active',
        ])
    filename = f'linkmint-links-{now_utc().strftime("%Y%m%d")}.csv'
    return Response(
        content=buf.getvalue(),
        media_type='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@api_router.get('/links/{code}/analytics', response_model=AnalyticsResponse)
async def link_analytics(code: str, request: Request, days: int = 30):
    user = await get_current_user(request)
    doc = await db.links.find_one({'code': code}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='Link not found')
    owner_id = doc.get('owner_id')
    if owner_id is not None and (not user or user['user_id'] != owner_id):
        raise HTTPException(status_code=403, detail='You do not own this link')
    days = max(7, min(days, 90))
    daily = doc.get('daily', {}) or {}
    series = []
    for i in range(days - 1, -1, -1):
        d = (now_utc() - timedelta(days=i)).strftime('%Y-%m-%d')
        series.append(DailyPoint(date=d, clicks=int(daily.get(d, 0))))
    return AnalyticsResponse(code=code, total_clicks=int(doc.get('clicks', 0)), series=series)


@api_router.get('/links', response_model=PaginatedLinks)
async def list_links(request: Request, q: str = '', tag: str = '', page: int = 1, limit: int = 25):
    user = await get_current_user(request)
    query = scope_query(user)
    filters = [query]
    q = q.strip()
    if q:
        rx = {'$regex': re.escape(q), '$options': 'i'}
        filters.append({'$or': [{'code': rx}, {'url': rx}]})
    tag = tag.strip()
    if tag:
        filters.append({'tags': {'$regex': f'^{re.escape(tag)}$', '$options': 'i'}})
    query = {'$and': filters} if len(filters) > 1 else query
    limit = max(1, min(limit, 100))
    page = max(1, page)
    total = await db.links.count_documents(query)
    pages = max(1, math.ceil(total / limit))
    page = min(page, pages)
    docs = (
        await db.links.find(query, {'_id': 0})
        .sort('created_at', -1)
        .skip((page - 1) * limit)
        .to_list(limit)
    )
    return PaginatedLinks(items=[doc_to_link(d) for d in docs], total=total, page=page, pages=pages)


@api_router.get('/stats', response_model=StatsResponse)
async def stats(request: Request):
    user = await get_current_user(request)
    base = scope_query(user)
    total_links = await db.links.count_documents(base)
    pipeline = [{'$match': base}, {'$group': {'_id': None, 'clicks': {'$sum': '$clicks'}}}]
    agg = await db.links.aggregate(pipeline).to_list(1)
    total_clicks = int(agg[0]['clicks']) if agg else 0
    now_iso = now_utc().isoformat()
    active_links = await db.links.count_documents({
        '$and': [base, {'$or': [{'expires_at': None}, {'expires_at': {'$gt': now_iso}}]}]
    })
    return StatsResponse(total_links=total_links, total_clicks=total_clicks, active_links=active_links)


@api_router.delete('/links/{code}')
async def delete_link(code: str, request: Request):
    user = await get_current_user(request)
    doc = await db.links.find_one({'code': code}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='Link not found')
    owner_id = doc.get('owner_id')
    if owner_id is not None and (not user or user['user_id'] != owner_id):
        raise HTTPException(status_code=403, detail='You do not own this link')
    await db.links.delete_one({'code': code})
    await cache_delete(code)
    return {'deleted': True, 'code': code}


@api_router.get('/qr/{code}')
async def qr_image(code: str, request: Request):
    doc = await db.links.find_one({'code': code}, {'_id': 0})
    if not doc:
        raise HTTPException(status_code=404, detail='Link not found')
    proto = request.headers.get('x-forwarded-proto', 'https').split(',')[0].strip()
    host = request.headers.get('x-forwarded-host') or request.headers.get('host', 'localhost')
    short_url = f'{proto}://{host}/{code}'
    qr = qrcode.QRCode(box_size=10, border=2)
    qr.add_data(short_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    buf = BytesIO()
    img.save(buf, format='PNG')
    return Response(
        content=buf.getvalue(),
        media_type='image/png',
        headers={
            'Cache-Control': 'public, max-age=300',
            'Content-Disposition': f'inline; filename="linkmint-{code}.png"',
        },
    )


async def _resolve_code(code: str) -> str:
    """Resolve a code to its destination URL. Redis first, Mongo fallback. Increments clicks."""
    cached = await cache_get(code)
    if cached:
        if is_expired(cached.get('expires_at')):
            raise HTTPException(status_code=410, detail='This link has expired')
        url = cached['url']
    else:
        doc = await db.links.find_one({'code': code}, {'_id': 0})
        if not doc:
            raise HTTPException(status_code=404, detail='Link not found')
        if is_expired(doc.get('expires_at')):
            raise HTTPException(status_code=410, detail='This link has expired')
        url = doc['url']
        await cache_set(code, {'url': url, 'expires_at': doc.get('expires_at')})
    await db.links.update_one(
        {'code': code},
        {'$inc': {'clicks': 1, f'daily.{now_utc().strftime("%Y-%m-%d")}': 1}},
    )
    return url


@api_router.get('/resolve/{code}', response_model=ResolveResponse)
async def resolve(code: str):
    url = await _resolve_code(code)
    return ResolveResponse(code=code, url=url)


@api_router.get('/r/{code}')
async def redirect(code: str):
    url = await _resolve_code(code)
    return RedirectResponse(url=url, status_code=302)


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.on_event('startup')
async def startup():
    try:
        await db.links.create_index('code', unique=True)
        await db.links.create_index('created_at')
        await db.links.create_index('owner_id')
        await db.users.create_index('email', unique=True)
        await db.users.create_index('user_id', unique=True)
        await db.user_sessions.create_index('session_token', unique=True)
    except Exception as e:
        logger.warning('Index creation failed: %s', e)
    try:
        await redis_client.ping()
        logger.info('Redis connected')
    except Exception:
        logger.warning('Redis unavailable - falling back to MongoDB only')


@app.on_event('shutdown')
async def shutdown_db_client():
    client.close()
    try:
        await redis_client.close()
    except Exception:
        pass
