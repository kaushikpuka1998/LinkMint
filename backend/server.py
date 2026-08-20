from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import re
import json
import random
import string
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

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
RESERVED_CODES = {'api', 'app', 'static', 'admin', 'links', 'stats', 'health', 'assets'}


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
# Models
# ---------------------------------------------------------------------------
class LinkCreate(BaseModel):
    url: str
    custom_alias: Optional[str] = None
    expires_at: Optional[str] = None


class Link(BaseModel):
    model_config = ConfigDict(extra='ignore')

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    code: str
    url: str
    clicks: int = 0
    created_at: str
    expires_at: Optional[str] = None
    is_expired: bool = False


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


def doc_to_link(doc: dict) -> Link:
    return Link(
        id=doc.get('id', str(uuid.uuid4())),
        code=doc['code'],
        url=doc['url'],
        clicks=int(doc.get('clicks', 0)),
        created_at=doc.get('created_at', ''),
        expires_at=doc.get('expires_at'),
        is_expired=is_expired(doc.get('expires_at')),
    )


# ---------------------------------------------------------------------------
# Routes
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
async def shorten(payload: LinkCreate):
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
    }
    await db.links.insert_one(dict(doc))
    await cache_set(code, {'url': url, 'expires_at': expires_at})
    logger.info('Shortened %s -> %s', url[:80], code)
    return doc_to_link(doc)


@api_router.get('/links', response_model=List[Link])
async def list_links(limit: int = 100):
    docs = await db.links.find({}, {'_id': 0}).sort('created_at', -1).to_list(min(limit, 500))
    return [doc_to_link(d) for d in docs]


@api_router.get('/stats', response_model=StatsResponse)
async def stats():
    total_links = await db.links.count_documents({})
    pipeline = [{'$group': {'_id': None, 'clicks': {'$sum': '$clicks'}}}]
    agg = await db.links.aggregate(pipeline).to_list(1)
    total_clicks = int(agg[0]['clicks']) if agg else 0
    now_iso = now_utc().isoformat()
    active_links = await db.links.count_documents({
        '$or': [{'expires_at': None}, {'expires_at': {'$gt': now_iso}}]
    })
    return StatsResponse(total_links=total_links, total_clicks=total_clicks, active_links=active_links)


@api_router.delete('/links/{code}')
async def delete_link(code: str):
    result = await db.links.delete_one({'code': code})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail='Link not found')
    await cache_delete(code)
    return {'deleted': True, 'code': code}


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
    await db.links.update_one({'code': code}, {'$inc': {'clicks': 1}})
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
