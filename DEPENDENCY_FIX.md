# Dependency Fix - pydantic-settings

## Issue

**Error Message**:
```
ModuleNotFoundError: No module named 'pydantic_settings'
```

**Location**: `src\config\loader.py`, line 15

## Root Cause

The code uses `pydantic_settings.BaseSettings` which is a separate package in Pydantic v2:

```python
from pydantic_settings import BaseSettings  # Line 15
```

However, `pydantic-settings` was not listed in `requirements.txt`.

## Solution Applied

### 1. Updated requirements.txt

**Before**:
```text
# Core dependencies
pydantic>=2.0.0
pyyaml>=6.0
python-dotenv>=1.0.0
```

**After**:
```text
# Core dependencies
pydantic>=2.0.0
pydantic-settings>=2.0.0  # ← ADDED
pyyaml>=6.0
python-dotenv>=1.0.0
```

### 2. Installed Package

```bash
pip install pydantic-settings>=2.0.0
```

**Installed Version**: pydantic-settings 2.12.0

## Verification

To verify the fix works:

```bash
# Test import
python -c "from pydantic_settings import BaseSettings; print('✓ OK')"

# Test config loader
python -c "from src.config.loader import ConfigLoader; print('✓ OK')"

# Test web API
python -c "from src.web.api import app; print('✓ OK')"
```

All imports should now work without errors.

## Why This Happened

In Pydantic v2, `BaseSettings` was moved to a separate package (`pydantic-settings`) 
to reduce the main package size and dependencies. This allows applications that 
don't need settings management to avoid installing extra dependencies.

**Reference**: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

## Next Steps

If you encounter similar import errors, check:

1. **requirements.txt** - Is the package listed?
2. **Installed packages** - Run `pip list | grep <package-name>`
3. **Virtual environment** - Are you using the correct venv?

## Date Fixed

2026-02-07 17:45 IST
