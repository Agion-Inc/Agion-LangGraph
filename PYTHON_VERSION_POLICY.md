# Python Version Support Policy

## Current Policy

**Agion SDK requires Python 3.12 or 3.13**

## Rationale

### Why Python 3.12+?

1. **Production Alignment**
   - The Agion LangGraph platform runs on Python 3.13 in production
   - No business need to support older Python versions
   - Development and production environments are aligned

2. **Modern Python Features**
   - Python 3.12+: Better performance (10-60% faster than 3.11)
   - Improved type hints and error messages
   - Better async/await performance
   - New syntax features and standard library improvements

3. **Simplified Maintenance**
   - Only 2 versions to test and support (3.12, 3.13)
   - No legacy compatibility code needed
   - Faster CI/CD pipelines with fewer test matrices

4. **Security and Support**
   - Python 3.12: Supported until October 2028
   - Python 3.13: Supported until October 2029
   - Both have active security updates

### Comparison with Dependencies

| Package | Minimum Python | Our Choice |
|---------|---------------|------------|
| LangGraph | 3.9+ | **3.12+** |
| LangChain | 3.9+ | **3.12+** |
| FastAPI | 3.8+ | **3.12+** |
| Pydantic | 3.8+ | **3.12+** |
| Redis-py | 3.7+ | **3.12+** |
| **Agion SDK** | **N/A** | **3.12+** |

**Decision**: We are more strict than our dependencies, which is fine since we control the deployment environment.

## Python Version Support Timeline

```
Python Version | Release      | End of Support | Agion SDK Support
---------------|--------------|----------------|------------------
3.9            | Oct 2020     | Oct 2025       | ❌ Not supported
3.10           | Oct 2021     | Oct 2026       | ❌ Not supported
3.11           | Oct 2022     | Oct 2027       | ❌ Not supported
3.12           | Oct 2023     | Oct 2028       | ✅ Supported
3.13           | Oct 2024     | Oct 2029       | ✅ Supported
3.14           | Oct 2025     | Oct 2030       | 🔮 Future support
```

## Python 3.12 Key Features

- **60% faster** on some workloads compared to 3.11
- PEP 701: Improved f-string parsing
- PEP 709: Improved comprehensions
- Better error messages with suggestions
- Improved type checking performance

## Python 3.13 Key Features

- **Free-threaded Python** (experimental GIL removal)
- **JIT compilation** (experimental)
- Improved REPL with colors and multiline editing
- Better error messages
- Performance improvements

## Deployment Environments

All environments use Python 3.13:

### Production
```dockerfile
FROM python:3.13-slim
```

### Development
```bash
pyenv install 3.13.1
pyenv local 3.13.1
```

### Docker
- Backend: `python:3.13-slim`
- Frontend: Node.js 22 (not affected)

### Kubernetes
- Azure Kubernetes Service (AKS)
- Python 3.13 runtime in containers

## Migration Path (If Needed)

If we ever need to support older Python versions:

1. **Test compatibility**: Run tests on Python 3.11
2. **Update pyproject.toml**: Change `requires-python = ">=3.11"`
3. **Update classifiers**: Add Python 3.11 classifier
4. **Update tool configs**: Add py311 to Black, Ruff, Mypy
5. **Update CI/CD**: Add Python 3.11 to test matrix
6. **Document changes**: Update README and migration guides

## Developer Requirements

### Local Development

**Required**:
- Python 3.12 or 3.13

**Installation**:
```bash
# Using pyenv (recommended)
pyenv install 3.13.1
pyenv local 3.13.1

# Verify
python --version  # Should show 3.13.x or 3.12.x
```

### SDK Installation

```bash
# Clone repository
cd agion-sdk-python

# Install SDK
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"
```

### Backend Integration

```bash
cd backend
pip install -r requirements.txt
```

## CI/CD Configuration

### Test Matrix

```yaml
strategy:
  matrix:
    python-version: ["3.12", "3.13"]
```

**Note**: We only test on 2 Python versions, keeping CI fast and simple.

### Docker Builds

All Docker images use Python 3.13:
```dockerfile
FROM python:3.13-slim AS builder
# ...
FROM python:3.13-slim
```

## FAQ

### Q: Why not support Python 3.11?
**A**: No business requirement. Our platform runs on 3.13 in production, and 3.12+ provides significant performance benefits.

### Q: What if a user wants to use Python 3.11?
**A**: They can fork the SDK and change `requires-python = ">=3.11"`. The code will likely work, but we don't officially support or test it.

### Q: Will you add Python 3.14 support?
**A**: Yes, once Python 3.14 is released (October 2025), we'll add it to our support matrix and test it in CI.

### Q: What about Python 2.7 or 3.8?
**A**: No. These are end-of-life and have known security vulnerabilities.

### Q: Does this affect LangGraph compatibility?
**A**: No. LangGraph supports 3.9+, and we're using 3.12+, which is a subset. Full compatibility is maintained.

## Summary

✅ **Agion SDK**: Python 3.12 or 3.13 only
✅ **Production**: Python 3.13
✅ **Development**: Python 3.12 or 3.13
✅ **Maintenance**: Simplified with only 2 versions
✅ **Performance**: Better performance with modern Python
✅ **Security**: Both versions have active support until 2028-2029

**Decision**: Python 3.12+ is the right choice for this SDK and platform.
