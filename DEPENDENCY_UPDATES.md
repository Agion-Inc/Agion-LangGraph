# Dependency Updates - Agion SDK

## Summary

All Agion SDK dependencies have been updated to their latest versions as of October 2025.

## Updated Dependencies

### Core Dependencies (`agion-sdk-python/pyproject.toml`)

| Package | Previous | Latest | Update |
|---------|----------|--------|--------|
| redis | >=5.0.0 | >=6.4.0 | ✅ Updated |
| aiohttp | >=3.9.0 | >=3.12.15 | ✅ Updated |
| pydantic | >=2.0.0 | >=2.11.9 | ✅ Updated |

### Dev Dependencies

| Package | Previous | Latest | Update |
|---------|----------|--------|--------|
| pytest | >=7.4.0 | >=8.4.2 | ✅ Updated |
| pytest-asyncio | >=0.21.0 | >=1.2.0 | ✅ Updated |
| pytest-cov | >=4.1.0 | >=7.0.0 | ✅ Updated |
| black | >=23.7.0 | >=25.9.0 | ✅ Updated |
| ruff | >=0.0.285 | >=0.13.2 | ✅ Updated |
| mypy | >=1.5.0 | >=1.18.2 | ✅ Updated |

### Backend Integration (`backend/requirements.txt`)

| Package | Previous | Latest | Update |
|---------|----------|--------|--------|
| redis | 5.2.2 | 6.4.0 | ✅ Updated |

## Python Version Support

Updated SDK to require Python 3.12+:
- **Minimum**: Python 3.12 (was 3.9)
- **Maximum**: Python 3.13
- **Rationale**:
  - Project uses Python 3.13 in production
  - No need to support older versions (3.9-3.11)
  - LangGraph requires 3.9+, but we're more strict
  - Modern Python features and better performance
- **Classifiers**: Support only Python 3.12 and 3.13
- **Black targets**: py312, py313 only
- **Ruff target**: py312
- **Mypy target**: py312

## Key Changes

### Redis 6.4.0 (from 5.0.0)
- **Major version upgrade**: 5.x → 6.x
- **Breaking changes**: May include API changes in async Redis client
- **New features**:
  - Improved async/await support
  - Better connection pooling
  - Enhanced error handling
  - Performance improvements

### Pytest 8.4.2 (from 7.4.0)
- **Major version upgrade**: 7.x → 8.x
- **New features**:
  - Better async test support
  - Improved fixtures
  - Enhanced reporting

### Pytest-asyncio 1.2.0 (from 0.21.0)
- **Major version upgrade**: 0.x → 1.x
- **Stable release**: First 1.x stable version
- **Breaking changes**: May require test updates

### Pytest-cov 7.0.0 (from 4.1.0)
- **Major version upgrade**: 4.x → 7.x
- **New features**: Better coverage reporting

### Black 25.9.0 (from 23.7.0)
- **Multiple major versions**: 23.x → 25.x
- **New features**:
  - Better formatting
  - Python 3.13 support

### Ruff 0.13.2 (from 0.0.285)
- **Significant upgrade**: 0.0.x → 0.13.x
- **Now stable**: No longer beta
- **New features**:
  - Many new linting rules
  - Better performance
  - Improved error messages

### Mypy 1.18.2 (from 1.5.0)
- **Minor version updates**: Better type checking

## Testing Required

### Critical Tests
1. **Redis Connection**: Test async Redis operations with 6.4.0
2. **SDK Initialization**: Verify SDK connects to Redis successfully
3. **Event Publishing**: Test event publishing to Redis Streams
4. **Policy Sync**: Test policy synchronization via Redis Pub/Sub

### Test Commands

```bash
# Install updated dependencies
cd agion-sdk-python
pip install -e ".[dev]"

# Run SDK tests
pytest tests/ -v

# Test backend integration
cd ../backend
pip install -r requirements.txt
pytest tests/ -v

# Test Redis connection
python -c "
import asyncio
import redis.asyncio as aioredis

async def test():
    r = await aioredis.from_url('redis://localhost:6379')
    await r.ping()
    print('✅ Redis connection successful')
    await r.close()

asyncio.run(test())
"
```

## Migration Notes

### Redis 6.x Migration

The main Redis package has been updated from 5.x to 6.x. Key changes:

**Connection URLs**: Same format
```python
redis://localhost:6379
redis://:password@localhost:6379
redis-sentinel://sentinel1:26379,sentinel2:26379/mymaster
```

**Async Client**: API remains compatible
```python
import redis.asyncio as aioredis

# Still works the same
redis = await aioredis.from_url(url)
await redis.ping()
```

**Potential Issues**:
- Connection pooling may have different defaults
- Some internal APIs may have changed
- Error handling might be different

### Pytest-asyncio 1.x Migration

Major change: `asyncio_mode = "auto"` is now the default.

**Current config** (still works):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

**Test decorators** (no changes needed):
```python
async def test_something():  # Auto-detected
    await async_function()
```

## Rollback Plan

If issues arise, rollback by reverting files:

```bash
git checkout HEAD~1 -- agion-sdk-python/pyproject.toml
git checkout HEAD~1 -- backend/requirements.txt
```

Or manually revert to previous versions:
```toml
# agion-sdk-python/pyproject.toml
dependencies = [
    "redis>=5.0.0",
    "aiohttp>=3.9.0",
    "pydantic>=2.0.0",
]
```

## Deployment Checklist

- [ ] Run SDK tests: `pytest agion-sdk-python/tests/`
- [ ] Run backend tests: `pytest backend/tests/`
- [ ] Test Redis 6.4.0 connection locally
- [ ] Test event publishing to Redis Streams
- [ ] Test policy sync via Redis Pub/Sub
- [ ] Build Docker images with new dependencies
- [ ] Deploy to staging environment
- [ ] Monitor logs for Redis connection issues
- [ ] Verify agent registration works
- [ ] Verify trust score updates work
- [ ] Deploy to production

## Documentation Updates

Updated files:
- ✅ `agion-sdk-python/pyproject.toml` - Core and dev dependencies
- ✅ `backend/requirements.txt` - Redis version
- ✅ Python 3.13 support added

## Support

If issues occur:
1. Check Redis 6.4.0 compatibility: https://redis-py.readthedocs.io/
2. Review pytest-asyncio 1.x migration: https://pytest-asyncio.readthedocs.io/
3. Check agion-sdk tests for failures
4. Review backend integration tests

## Version Verification

To verify installed versions:

```bash
# Check SDK dependencies
cd agion-sdk-python
pip show redis aiohttp pydantic

# Check backend dependencies
cd ../backend
pip show redis

# Check dev tools
pip show pytest pytest-asyncio black ruff mypy
```

Expected output:
```
redis: 6.4.0
aiohttp: 3.12.15
pydantic: 2.11.9
pytest: 8.4.2
pytest-asyncio: 1.2.0
pytest-cov: 7.0.0
black: 25.9.0
ruff: 0.13.2
mypy: 1.18.2
```
