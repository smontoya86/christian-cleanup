from azlyrics import lyrics
import sys

artist = sys.argv[1]
title = sys.argv[2]

lyrics_text = lyrics.get_lyrics(artist, title)
print(lyrics_text)

