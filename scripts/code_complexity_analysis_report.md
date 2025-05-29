# Code Complexity Analysis Report
==================================================

## Summary
- Total Lines: 2177
- Total Classes: 6
- Total Methods: 34
- Complex Methods (>25 lines): 19

## app/utils/analysis.py
- Lines: 1389
- Classes: 3
- Methods: 18
- Complex Methods: 11

### Complex Methods (>25 lines):
- analyze_song: 286 lines (line 1064)
- _detect_christian_purity_flags: 266 lines (line 635)
- _load_koalaai_label_map: 151 lines (line 387)
- _get_content_moderation_predictions: 118 lines (line 190)
- _process_flag: 95 lines (line 539)
- _calculate_christian_score_and_concern: 87 lines (line 969)
- __init__: 79 lines (line 47)
- _detect_christian_themes: 66 lines (line 902)
- _get_explicit_patterns: 39 lines (line 347)
- _load_models: 37 lines (line 127)
- _get_content_moderation_predictions: 37 lines (line 309)

### Classes:
- SongAnalyzer: 14 methods, 1304 lines
- LyricsFetcher: 1 methods, 4 lines
- BibleClient: 3 methods, 18 lines

## app/utils/analysis_enhanced.py
- Lines: 788
- Classes: 3
- Methods: 16
- Complex Methods: 8

### Complex Methods (>25 lines):
- _setup_enhanced_patterns: 134 lines (line 192)
- _setup_biblical_themes: 117 lines (line 74)
- _analyze_biblical_themes: 97 lines (line 561)
- analyze_song: 93 lines (line 344)
- _generate_comprehensive_explanation: 54 lines (line 713)
- _create_detailed_concern: 51 lines (line 509)
- _analyze_category_comprehensive: 42 lines (line 466)
- _analyze_lyrics_comprehensive: 27 lines (line 438)

### Classes:
- ContentFlag: 0 methods, 8 lines
- AnalysisConfig: 1 methods, 13 lines
- EnhancedSongAnalyzer: 14 methods, 733 lines