# Refactoring Execution Plan - OpenAI-Only Architecture

**Date:** October 1, 2025  
**Approved By:** User  
**Status:** In Progress

---

## 🎯 Objectives

1. **Remove Ollama/vLLM support** → OpenAI-only
2. **Remove EnhancedConcernDetector/ScriptureMapper** → Use GPT-4o-mini output directly
3. **Keep batch analysis** but remove HuggingFace-specific logic
4. **Remove dead code** (rules_rag, calibration_service, etc.)

---

## 📋 Execution Steps

### **Step 1: Remove Dead Code Files ✓**
**Risk:** None (unused files)

Files to remove:
- `app/services/rules_rag.py` (imported but never called)
- `app/services/intelligent_llm_router.py` (will be replaced)
- `app/utils/analysis/embedding_index.py` (only used by unused theology_kb)
- `app/utils/analysis/theology_kb.py` (never imported)
- `scripts/utilities/calibration_service.py` (never imported)

Update imports:
- Remove unused imports from `app/routes/api.py`

---

### **Step 2: Simplify RouterAnalyzer to OpenAI-Only**
**Risk:** Low (well-defined API)

**Current:**
```python
from ..intelligent_llm_router import get_intelligent_router

class RouterAnalyzer:
    def __init__(self) -> None:
        self.router = get_intelligent_router()
        provider_config = self.router.get_optimal_provider()
        self.base_url = provider_config.get("api_base", "...")
        self.model = provider_config.get("model", "...")
```

**New:**
```python
import os

class RouterAnalyzer:
    def __init__(self) -> None:
        # OpenAI API only
        self.base_url = "https://api.openai.com/v1"
        self.model = os.environ.get("OPENAI_MODEL", "ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav")
        self.api_key = os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
```

---

### **Step 3: Simplify AnalyzerCache to OpenAI-Only**
**Risk:** Low (remove unused auto-detection)

Remove:
- Lines 45-65: Local LLM auto-detection
- Lines 88-142: Preflight checks for local LLM

Keep:
- Singleton pattern
- Lazy initialization
- Thread safety

**New Implementation:**
```python
def get_analyzer(self):
    """Get the cached analyzer instance, initializing if necessary"""
    if self._analyzer is None:
        with self._initialization_lock:
            if self._analyzer is None and not self._is_initializing:
                self._is_initializing = True
                try:
                    logger.info("🚀 Initializing Router analyzer (OpenAI API)...")
                    self._analyzer = RouterAnalyzer()
                    logger.info("✅ Router analyzer initialized successfully")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize analyzer: {e}")
                    raise
                finally:
                    self._is_initializing = False
    return self._analyzer
```

---

### **Step 4: Simplify ProviderResolver to OpenAI-Only**
**Risk:** None (trivial change)

**Current:**
```python
def get_analyzer() -> Any:
    provider = (os.environ.get("ANALYZER_PROVIDER") or "router").strip().lower()
    if provider in ("router", "default", "openai", "llm"):
        return RouterAnalyzer()
    return RouterAnalyzer()
```

**New:**
```python
def get_analyzer() -> Any:
    """Get the OpenAI-powered RouterAnalyzer instance."""
    return RouterAnalyzer()
```

---

### **Step 5: Remove EnhancedConcernDetector**
**Risk:** Medium (used in SimplifiedChristianAnalysisService)

Files to remove:
- `app/services/enhanced_concern_detector.py` (~329 lines)

Update:
- `SimplifiedChristianAnalysisService.__init__()` (remove initialization)
- `SimplifiedChristianAnalysisService.analyze_song()` (remove concern detection calls)
- `SimplifiedChristianAnalysisService.analyze_songs_batch()` (remove concern detection calls)

**Replacement Logic:**
Use GPT-4o-mini's `concerns` field directly (already in output)

---

### **Step 6: Remove EnhancedScriptureMapper**
**Risk:** Medium (used in SimplifiedChristianAnalysisService)

Files to remove:
- `app/services/enhanced_scripture_mapper.py` (~400-500 lines)

Update:
- `SimplifiedChristianAnalysisService.__init__()` (remove initialization)
- `SimplifiedChristianAnalysisService.analyze_song()` (remove scripture mapping calls)
- `SimplifiedChristianAnalysisService.analyze_songs_batch()` (remove scripture mapping calls)

**Replacement Logic:**
Use GPT-4o-mini's `supporting_scripture` field directly (already in output)

---

### **Step 7: Refactor SimplifiedChristianAnalysisService**
**Risk:** High (core analysis logic)

**Changes:**
1. Remove `self.concern_detector` and `self.scripture_mapper` initialization
2. Simplify `analyze_song()`:
   - Remove concern detection calls
   - Remove scripture mapping calls
   - Use GPT-4o-mini output directly
3. Simplify `analyze_songs_batch()`:
   - Remove HuggingFace-specific fallback logic
   - Use OpenAI concurrent requests
   - Simplify from 287 lines to ~100-150 lines

**Key Insight:**
GPT-4o-mini already returns:
```json
{
  "concerns": [...],
  "supporting_scripture": [...],
  "biblical_themes": [...]
}
```

No need to re-analyze!

---

### **Step 8: Update Documentation**
**Risk:** None

Files to update:
- `docs/biblical_discernment_v2.md` (Line 19: Remove "HuggingFace" reference)
- `docs/christian_framework.md` (Lines 237-273: Remove gpt-oss-20b references)
- `README.md` (Lines 169-186: Update architecture description)
- `app/services/analyzer_cache.py` (Docstrings: Change "HuggingFace" to "OpenAI")

---

### **Step 9: Update Config Files**
**Risk:** Low

`app/config_llm.py`:
```python
# Simplified OpenAI-only config
llm_config = {
    "default": "openai",
    "providers": {
        "openai": {
            "api_base": "https://api.openai.com/v1",
            "model": "ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav"
        }
    }
}
```

---

### **Step 10: Testing Strategy**
**Risk:** Critical (verify nothing breaks)

**Unit Tests:**
1. Test `RouterAnalyzer` initialization with/without API key
2. Test `RouterAnalyzer.analyze_song()` output format
3. Test `AnalyzerCache` singleton behavior

**Integration Tests:**
1. Test full analysis pipeline end-to-end
2. Test batch analysis with 10 songs
3. Test API endpoints (`/api/songs/<id>/analyze`)

**Regression Tests:**
1. Run existing test suite: `pytest tests/ -v`
2. Verify no import errors
3. Verify analysis output structure unchanged

---

## 📊 Expected Impact

### **Code Reduction:**
- Dead code: -700-900 LOC
- EnhancedConcernDetector: -329 LOC
- EnhancedScriptureMapper: -400-500 LOC
- SimplifiedChristianAnalysisService: -200-300 LOC (refactored)
- AnalyzerCache: -150-200 LOC (simplified)
- **Total: ~1,779-2,229 LOC removed**

### **Files Removed:**
1. `app/services/rules_rag.py`
2. `app/services/intelligent_llm_router.py`
3. `app/services/enhanced_concern_detector.py`
4. `app/services/enhanced_scripture_mapper.py`
5. `app/utils/analysis/embedding_index.py`
6. `app/utils/analysis/theology_kb.py`
7. `scripts/utilities/calibration_service.py`

**Total: 7 files removed**

### **Files Refactored:**
1. `app/services/analyzers/router_analyzer.py` (simplified)
2. `app/services/analyzer_cache.py` (simplified)
3. `app/services/provider_resolver.py` (simplified)
4. `app/services/simplified_christian_analysis_service.py` (major refactor)
5. `app/config_llm.py` (simplified)
6. `app/routes/api.py` (remove unused imports)

**Total: 6 files refactored**

---

## ✅ Validation Checklist

Before committing each step:
- [ ] Run `pytest tests/ -v` (all tests pass)
- [ ] Run `python -m app` (application starts without errors)
- [ ] Test analysis endpoint with real song
- [ ] Verify no import errors in logs
- [ ] Verify output structure matches GPT-4o-mini schema

---

**Status:** Ready to execute  
**Estimated Time:** 3-4 hours  
**Risk Level:** Medium (with TDD approach)

