# Analysis Utilities Refactoring Plan

**Date:** May 29, 2025  
**Task:** Task 35 - Optimize Analysis Utilities  
**Current Status:** Planning Phase Complete

## Executive Summary

Based on the complexity analysis, we have identified significant opportunities for refactoring:

- **Total Lines of Code:** 2,177 lines across 2 files
- **Complex Methods:** 19 methods exceeding 25 lines (target: 0)
- **Largest Method:** `analyze_song` with 286 lines (target: <25 lines)
- **Monolithic Classes:** `SongAnalyzer` (1,304 lines), `EnhancedSongAnalyzer` (733 lines)

## Current Issues Identified

### 1. **Extremely Large Methods**
- `analyze_song` (286 lines) - Main orchestration method
- `_detect_christian_purity_flags` (266 lines) - Complex flag detection logic
- `_load_koalaai_label_map` (151 lines) - Hardcoded mapping data
- `_setup_enhanced_patterns` (134 lines) - Pattern setup logic
- `_setup_biblical_themes` (117 lines) - Theme configuration

### 2. **Monolithic Classes**
- `SongAnalyzer` (1,304 lines, 14 methods) - Does everything
- `EnhancedSongAnalyzer` (733 lines, 14 methods) - Duplicate functionality

### 3. **Code Duplication**
- Both classes implement similar analysis logic
- Biblical theme detection exists in both files
- Pattern matching logic is duplicated
- Score calculation algorithms are similar but different

### 4. **Poor Separation of Concerns**
- Model loading mixed with analysis logic
- Configuration mixed with business logic
- Data structures mixed with algorithms
- API integration mixed with core analysis

## Proposed Domain-Driven Design Structure

### Core Domains

#### 1. **Text Processing Domain** (`app/utils/analysis/text/`)
```
text/
├── __init__.py
├── preprocessor.py      # LyricsPreprocessor class
├── tokenizer.py         # TextTokenizer class
└── cleaner.py          # TextCleaner class
```

**Responsibilities:**
- Clean and normalize lyrics text
- Remove timestamps, sections, special characters
- Tokenization and text preparation
- Handle encoding issues

#### 2. **Pattern Detection Domain** (`app/utils/analysis/patterns/`)
```
patterns/
├── __init__.py
├── base_detector.py     # BasePatternDetector interface
├── profanity_detector.py # ProfanityDetector class
├── drug_detector.py     # SubstanceDetector class
├── violence_detector.py # ViolenceDetector class
└── pattern_registry.py  # PatternRegistry for configuration
```

**Responsibilities:**
- Implement specific detection algorithms
- Manage pattern matching rules
- Context-aware detection to reduce false positives
- Configurable sensitivity levels

#### 3. **Biblical Analysis Domain** (`app/utils/analysis/biblical/`)
```
biblical/
├── __init__.py
├── theme_detector.py    # BiblicalThemeDetector class
├── scripture_mapper.py  # ScriptureReferenceMapper class
├── themes_config.py     # Biblical themes and scripture data
└── enhanced_detector.py # Integration with enhanced biblical detector
```

**Responsibilities:**
- Detect biblical themes and references
- Map themes to supporting scripture
- Handle different denominational preferences
- Positive content identification

#### 4. **Scoring Engine Domain** (`app/utils/analysis/scoring/`)
```
scoring/
├── __init__.py
├── calculator.py        # ScoreCalculator class
├── concern_levels.py    # ConcernLevelDeterminer class
├── penalty_system.py    # PenaltySystem class
└── score_config.py      # Scoring configuration and weights
```

**Responsibilities:**
- Calculate final Christian scores
- Apply penalties and bonuses
- Determine concern levels
- Generate scoring explanations

#### 5. **Model Integration Domain** (`app/utils/analysis/models/`)
```
models/
├── __init__.py
├── content_moderator.py # ContentModerationModel class
├── model_manager.py     # ModelManager for loading/caching
└── model_config.py      # Model configuration and mappings
```

**Responsibilities:**
- Manage AI model loading and inference
- Handle model errors and fallbacks
- Cache model predictions
- Abstract model-specific logic

#### 6. **Configuration Domain** (`app/utils/analysis/config/`)
```
config/
├── __init__.py
├── analysis_config.py   # AnalysisConfiguration class
├── user_preferences.py  # UserPreferences class
└── defaults.py          # Default settings and constants
```

**Responsibilities:**
- Manage user-specific analysis settings
- Handle denominational preferences
- Configure sensitivity levels
- Provide default configurations

### Orchestration Layer

#### 7. **Analysis Orchestrator** (`app/utils/analysis/`)
```
analysis/
├── __init__.py
├── orchestrator.py      # AnalysisOrchestrator class
├── legacy_adapter.py    # BackwardCompatibilityAdapter class
└── analysis_result.py   # AnalysisResult data class
```

**Responsibilities:**
- Coordinate analysis workflow
- Maintain backward compatibility
- Handle errors and fallbacks
- Generate comprehensive results

## Detailed Refactoring Strategy

### Phase 1: Extract Core Domains (Subtask 35.2)

1. **Create Text Processing Module**
   - Extract `_preprocess_lyrics` into `LyricsPreprocessor`
   - Create `TextTokenizer` for word-level processing
   - Implement `TextCleaner` for normalization

2. **Create Pattern Detection Module**
   - Extract pattern matching logic from both analyzers
   - Implement strategy pattern for different detectors
   - Consolidate regex patterns and context rules

3. **Create Biblical Analysis Module**
   - Merge biblical theme detection from both files
   - Create unified scripture mapping
   - Integrate with enhanced biblical detector

### Phase 2: Extract Complex Algorithms (Subtask 35.3)

1. **Refactor Score Calculation**
   - Extract scoring logic into dedicated calculator
   - Implement penalty and bonus systems separately
   - Create configurable concern level determination

2. **Simplify Model Integration**
   - Extract model loading into separate manager
   - Implement model prediction caching
   - Create fallback mechanisms for model failures

### Phase 3: Create Orchestration Layer (Subtask 35.4)

1. **Build Analysis Orchestrator**
   - Coordinate workflow between domains
   - Handle cross-cutting concerns (logging, errors)
   - Implement analysis pipeline pattern

2. **Ensure Backward Compatibility**
   - Create adapter for existing `analyze_song` interface
   - Maintain existing return format
   - Provide migration path for dependent code

## Success Metrics

### Code Quality Improvements
- **Method Complexity:** All methods <25 lines (currently 19 methods >25 lines)
- **Class Size:** All classes <200 lines (currently largest is 1,304 lines)
- **Cyclomatic Complexity:** All methods complexity <10
- **Code Duplication:** Eliminate duplicate biblical theme and pattern logic

### Performance Requirements
- **Analysis Speed:** Maintain current performance (<500ms per song)
- **Memory Usage:** No increase in memory footprint
- **Model Loading:** Improve model loading time with caching

### Maintainability Goals
- **Single Responsibility:** Each class has one clear purpose
- **Open/Closed:** Easy to add new detectors without changing existing code
- **Dependency Inversion:** Core logic doesn't depend on external services
- **Interface Segregation:** Small, focused interfaces

## Implementation Timeline

1. **Subtask 35.1** ✅ - Code Analysis Complete
2. **Subtask 35.2** - Extract Core Domains (Est. 4-6 hours)
3. **Subtask 35.3** - Refactor Complex Algorithms (Est. 3-4 hours)
4. **Subtask 35.4** - Error Handling & Logging (Est. 2-3 hours)
5. **Subtask 35.5** - Integration & Testing (Est. 3-4 hours)

**Total Estimated Time:** 12-17 hours

## Risk Mitigation

### Backward Compatibility
- Maintain existing `analyze_song` method signature
- Create comprehensive test suite before refactoring
- Implement adapter pattern for smooth transition

### Performance Regression
- Benchmark current performance before changes
- Profile refactored code for performance impact
- Implement performance tests in CI/CD

### Functionality Loss
- Create regression test suite with current outputs
- Document all behavior changes
- Implement feature flags for gradual rollout

## Next Steps

1. Complete this planning document ✅
2. Create baseline test suite for regression testing
3. Begin implementation of core domain classes
4. Iterate on design based on implementation feedback

---

**Note:** This plan provides a roadmap for transforming 2,177 lines of complex analysis code into a maintainable, modular, and extensible architecture while preserving all existing functionality. 