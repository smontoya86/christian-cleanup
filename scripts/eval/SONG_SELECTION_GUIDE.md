# Song Selection Guide for 1,200-Song Dataset

## Overview
Create a balanced, diverse dataset covering the full spectrum of Christian music analysis.

## Target Distribution (1,200 total)

### By Verdict (Expected Scores)
- **freely_listen (80-100)**: 400 songs (33%)
- **context_required (60-79)**: 400 songs (33%)
- **caution_limit (40-59)**: 250 songs (21%)
- **avoid_formation (0-39)**: 150 songs (13%)

### By Genre Category

#### Christian Music (600 songs = 50%)
1. **Traditional Hymns** (100 songs)
   - Classic hymns (pre-1900)
   - Modern hymns (1900-2000)
   - Contemporary hymns (2000+)

2. **Modern Worship** (200 songs)
   - Hillsong, Bethel, Elevation
   - Passion, Jesus Culture
   - Vineyard, IHOP
   
3. **Gospel/Soul** (100 songs)
   - Traditional gospel
   - Southern gospel
   - Contemporary gospel
   
4. **CCM (Contemporary Christian Music)** (150 songs)
   - Radio hits
   - Christian rock/pop
   - Christian hip-hop
   
5. **Praise & Worship** (50 songs)
   - Corporate worship
   - Spontaneous worship
   - Prophetic worship

#### Secular with Christian Themes (300 songs = 25%)
1. **Inspirational Pop** (100 songs)
   - Clean, uplifting messages
   - Moral themes
   - Hope and perseverance

2. **Character Songs** (100 songs)
   - Biblical narratives
   - Historical Christian figures
   - Spiritual struggle

3. **Lament & Grief** (100 songs)
   - Processing loss
   - Doubt directed to God
   - Honest questions

#### Borderline Content (200 songs = 17%)
1. **Vague Spirituality** (75 songs)
   - Generic "higher power"
   - Unclear theology
   - Syncretism

2. **Questionable Theology** (75 songs)
   - Word of Faith extremes
   - Prosperity gospel
   - Universalism hints

3. **Mixed Messages** (50 songs)
   - Some truth, some error
   - Context-dependent interpretation

#### Problematic Content (100 songs = 8%)
1. **Sexual Immorality** (30 songs)
   - Explicit content
   - Glorifying promiscuity
   - Objectification

2. **Blasphemy/Mockery** (20 songs)
   - Direct attacks on God
   - Mocking Christianity
   - Heresy

3. **Occult/Darkness** (20 songs)
   - Witchcraft themes
   - Satanic imagery
   - Demonic glorification

4. **Violence/Revenge** (15 songs)
   - Glorifying violence
   - Revenge fantasies
   - Murder themes

5. **Substance Abuse** (15 songs)
   - Glorifying drugs
   - Drunkenness celebration
   - Addiction normalization

## Song Selection Criteria

### Must Include:
✅ **Edge Cases**: Songs that challenge the framework
✅ **Famous Songs**: Well-known tracks for validation
✅ **Genre Diversity**: Country, rock, pop, hip-hop, metal, etc.
✅ **Era Diversity**: Classical, 60s-70s, 80s-90s, 2000s, 2010s, 2020s
✅ **Cultural Diversity**: Different cultures, languages (if lyrics available)
✅ **Artist Diversity**: Mix of artists, not over-representing any single one

### Avoid:
❌ Over-sampling one artist
❌ All songs from one era
❌ Only "safe" Christian songs
❌ Only mainstream hits

## Practical Implementation

### Phase 1: Core Christian (300 songs)
Start with the most important Christian worship songs that everyone knows.

### Phase 2: Expand Christian (300 songs)
Add deeper cuts, less-known worship, gospel, hymns.

### Phase 3: Secular Positive (200 songs)
Clean secular songs with moral/inspirational themes.

### Phase 4: Borderline (200 songs)
Songs requiring discernment, mixed messages.

### Phase 5: Problematic (200 songs)
Songs that clearly violate Christian values.

## Quality Checks
- [ ] Lyrics available for all songs
- [ ] Even distribution across categories
- [ ] No duplicate songs
- [ ] Artist diversity (max 10 songs per artist)
- [ ] Era diversity (at least 20% from each: pre-2000, 2000-2010, 2010-2020, 2020+)
- [ ] Genre diversity (at least 10% from each major genre)

## Next Steps
1. Generate initial song list
2. Check lyrics availability
3. Balance categories
4. Review for edge cases
5. Validate diversity
6. Label with GPT-4o-mini
7. QA check labels

