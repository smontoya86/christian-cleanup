# Database Relationship Audit

## Model Relationship Reference

### User Model
- ✅ `playlists` → Playlist (back_populates="owner")
- ✅ `whitelisted_artists` → Whitelist
- ✅ `blacklisted_items` → Blacklist

### Playlist Model
- ✅ `owner` → User (back_populates="playlists")
- ✅ `song_associations` → PlaylistSong (back_populates="playlist")
- ✅ `snapshots` → PlaylistSnapshot (back_populates="playlist")

### Song Model
- ✅ `playlist_associations` → PlaylistSong (back_populates="song")
- ✅ `analysis_result` → AnalysisResult (singular, uselist=False)
- ✅ `analysis_results` → AnalysisResult (plural, lazy="dynamic")

### AnalysisResult Model
- ✅ `song_rel` → Song (back_populates="analysis_results")

### PlaylistSong Model (Junction Table)
- ✅ `playlist` → Playlist (back_populates="song_associations")
- ✅ `song` → Song (back_populates="playlist_associations")

### PlaylistSnapshot Model
- ✅ `playlist` → Playlist (back_populates="snapshots")

### LyricsCache Model
- ✅ `song` → Song (backref="lyrics_cache")

## Correct Usage Patterns

### Query Songs from a Playlist
```python
# ✅ CORRECT
playlist.song_associations  # Returns PlaylistSong objects
for ps in playlist.song_associations:
    song = ps.song
```

### Query Playlists from a Song
```python
# ✅ CORRECT
song.playlist_associations  # Returns PlaylistSong objects
for ps in song.playlist_associations:
    playlist = ps.playlist
```

### Join Song → Playlist
```python
# ✅ CORRECT
Song.query.join(Song.playlist_associations).join(PlaylistSong.playlist)
```

### Join AnalysisResult → Song
```python
# ✅ CORRECT
AnalysisResult.query.join(AnalysisResult.song_rel)
```

### Get Analysis for a Song
```python
# ✅ CORRECT (singular)
analysis = song.analysis_result  # Returns one AnalysisResult or None

# ✅ CORRECT (plural for querying)
analyses = song.analysis_results.filter_by(status='completed').all()
```

## Common Mistakes to Avoid

### ❌ WRONG: Direct Many-to-Many Access
```python
song.playlists  # DOESN'T EXIST - must go through playlist_associations
playlist.songs  # DOESN'T EXIST - must go through song_associations
```

### ❌ WRONG: Using 'song' instead of 'song_rel' for AnalysisResult
```python
AnalysisResult.song  # DOESN'T EXIST
# Use: AnalysisResult.song_rel
```

## Audit Status: ✅ VERIFIED & FIXED

### Issues Found and Fixed:

1. ✅ **main.py line 33** - `Song.playlists` → `Song.playlist_associations`
2. ✅ **main.py line 41** - `AnalysisResult.song` → `AnalysisResult.song_rel`
3. ✅ **unified_analysis_service.py line 385** - `AnalysisResult.song` → `AnalysisResult.song_rel`
4. ✅ **unified_analysis_service.py line 397** - `AnalysisResult.song` → `AnalysisResult.song_rel`
5. ✅ **unified_analysis_service.py line 442** - `AnalysisResult.song` → `AnalysisResult.song_rel`

### Verification Complete:
- ❌ No `Song.playlists` references found
- ❌ No `Playlist.songs` references found
- ❌ No `AnalysisResult.song` references found
- ✅ All relationships now use correct names from models.py

All relationship names have been verified and corrected against the models.py definitions.

