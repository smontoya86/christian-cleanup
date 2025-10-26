# Whitelist/Blacklist Removal Audit

## Files Containing References (8 total):

1. app/models/models.py
   - Whitelist model (lines 495-508)
   - Blacklist model (lines 510-521)
   - User.whitelisted_artists relationship (lines 47-53)
   - User.blacklisted_items relationship (lines 54-60)

2. app/models/__init__.py
   - Imports: Whitelist, Blacklist

3. app/routes/main.py
   - Imports Whitelist
   - Likely has routes (need to find them)
   - Uses is_whitelisted variable (3 matches)

4. app/services/unified_analysis_service.py
   - Imports: Whitelist, Blacklist
   - Uses is_whitelisted (4 matches)

5. app/templates/song_detail.html
   - is_whitelisted variable (2 matches)
   - URL calls: add_to_whitelist, remove_whitelist

6. app/templates/components/playlist/song_card.html
   - is_whitelisted (4 matches)
   - URL: remove_whitelist

7. app/templates/components/playlist/song_row.html
   - is_whitelisted (3 matches)
   - URL: remove_whitelist, whitelist_song

8. app/templates/dashboard.html
   - URL: whitelist_playlist

## Routes to Find/Remove:
- main.add_to_whitelist
- main.remove_whitelist
- main.whitelist_playlist
- main.whitelist_song

## Database Tables to Drop:
- whitelist
- blacklist

## Next Steps:
1. Find all route definitions
2. Remove models
3. Remove routes
4. Remove UI references
5. Create migration
6. Test
