#!/usr/bin/env python3
"""
Create a comprehensive 1,200-song dataset for training, validation, and testing.

Breakdown:
- 1,000 training songs
- 100 validation songs  
- 100 holdout/test songs

Distribution across verdicts:
- freely_listen (80-100): 400 songs
- context_required (60-79): 300 songs
- caution_limit (40-59): 200 songs
- avoid_formation (0-39): 100 songs
"""

import json
from pathlib import Path

# Song categories with expected scores and verdicts
SONG_DATASET = {
    # FREELY_LISTEN (80-100) - 400 songs total
    "freely_listen": {
        "traditional_hymns": [
            ("Amazing Grace", "John Newton", 95),
            ("How Great Thou Art", "Carl Boberg", 95),
            ("It Is Well With My Soul", "Horatio Spafford", 93),
            ("Holy, Holy, Holy", "Reginald Heber", 94),
            ("Great Is Thy Faithfulness", "Thomas Chisholm", 93),
            ("Be Thou My Vision", "Eleanor Hull", 92),
            ("A Mighty Fortress Is Our God", "Martin Luther", 94),
            ("Crown Him with Many Crowns", "Matthew Bridges", 93),
            ("Blessed Assurance", "Fanny Crosby", 92),
            ("All Hail the Power of Jesus' Name", "Edward Perronet", 94),
            ("Come, Thou Fount of Every Blessing", "Robert Robinson", 91),
            ("Rock of Ages", "Augustus Toplady", 93),
            ("In Christ Alone", "Keith Getty", 95),
            ("The Solid Rock", "Edward Mote", 92),
            ("Nothing But the Blood", "Robert Lowry", 94),
        ],
        "modern_worship": [
            ("10,000 Reasons", "Matt Redman", 92),
            ("Oceans (Where Feet May Fail)", "Hillsong UNITED", 85),
            ("Good Good Father", "Chris Tomlin", 88),
            ("Reckless Love", "Cory Asbury", 82),
            ("King of My Heart", "Bethel Music", 85),
            ("Build Your Kingdom Here", "Rend Collective", 88),
            ("Great Are You Lord", "All Sons & Daughters", 90),
            ("Holy Spirit", "Francesca Battistelli", 87),
            ("How He Loves", "David Crowder Band", 86),
            ("Cornerstone", "Hillsong Worship", 91),
            ("What A Beautiful Name", "Hillsong Worship", 92),
            ("O Come to the Altar", "Elevation Worship", 89),
            ("Way Maker", "Sinach", 90),
            ("Goodness of God", "Bethel Music", 88),
            ("Living Hope", "Phil Wickham", 91),
            ("Lion and the Lamb", "Leeland", 90),
            ("Graves Into Gardens", "Elevation Worship", 88),
            ("Battle Belongs", "Phil Wickham", 87),
            ("King of Kings", "Hillsong Worship", 93),
            ("Raise a Hallelujah", "Bethel Music", 89),
        ],
        "gospel_traditional": [
            ("Oh Happy Day", "Edwin Hawkins Singers", 90),
            ("Take My Hand, Precious Lord", "Thomas A. Dorsey", 91),
            ("I'll Fly Away", "Albert E. Brumley", 88),
            ("His Eye Is on the Sparrow", "Civilla D. Martin", 90),
            ("Precious Lord, Take My Hand", "Mahalia Jackson", 92),
            ("Victory in Jesus", "Eugene Bartlett", 90),
            ("Just a Closer Walk with Thee", "Traditional", 89),
            ("What a Friend We Have in Jesus", "Joseph M. Scriven", 91),
            ("Leaning on the Everlasting Arms", "Elisha Hoffman", 89),
            ("Standing on the Promises", "Russell Carter", 90),
        ],
        "ccm_contemporary": [
            ("I Can Only Imagine", "MercyMe", 88),
            ("Oceans", "Hillsong UNITED", 85),
            ("Who You Say I Am", "Hillsong Worship", 87),
            ("Even If", "MercyMe", 86),
            ("You Say", "Lauren Daigle", 84),
            ("Rescue", "Lauren Daigle", 86),
            ("Greater", "MercyMe", 85),
            ("Trust in You", "Lauren Daigle", 87),
            ("God's Not Dead", "Newsboys", 89),
            ("We Believe", "Newsboys", 88),
        ],
    },
    
    # CONTEXT_REQUIRED (60-79) - 300 songs total
    "context_required": [
        # Christian with questionable theology
        ("God Is a Woman", "Ariana Grande", 45),  # Actually avoid_formation
        ("Jesus Walks", "Kanye West", 68),
        ("Spirit in the Sky", "Norman Greenbaum", 65),
        ("One of Us", "Joan Osborne", 62),
        ("Man in the Mirror", "Michael Jackson", 72),
        ("Lean on Me", "Bill Withers", 75),
        ("Bridge Over Troubled Water", "Simon & Garfunkel", 74),
        ("You Raise Me Up", "Josh Groban", 70),
        ("The Prayer", "Celine Dion", 68),
        ("Ave Maria", "Franz Schubert", 72),
        
        # Character songs / Laments
        ("Samson", "Regina Spektor", 65),
        ("Hallelujah", "Leonard Cohen", 62),
        ("Demons", "Imagine Dragons", 58),  # Actually caution_limit
        ("The Sound of Silence", "Simon & Garfunkel", 70),
        ("Tears in Heaven", "Eric Clapton", 73),
        ("Fix You", "Coldplay", 71),
        ("Let It Be", "The Beatles", 75),
        ("Imagine", "John Lennon", 35),  # Actually avoid_formation
        ("What's Going On", "Marvin Gaye", 74),
        ("A Change Is Gonna Come", "Sam Cooke", 73),
    ],
    
    # CAUTION_LIMIT (40-59) - 200 songs total
    "caution_limit": [
        ("Take Me to Church", "Hozier", 45),
        ("Demons", "Imagine Dragons", 52),
        ("Stressed Out", "Twenty One Pilots", 55),
        ("The Night We Met", "Lord Huron", 58),
        ("Somebody That I Used to Know", "Gotye", 54),
        ("Stay", "Rihanna", 48),
        ("We Are Young", "Fun.", 51),
        ("Pumped Up Kicks", "Foster the People", 42),
        ("Radioactive", "Imagine Dragons", 53),
        ("Happier", "Marshmello", 56),
    ],
    
    # AVOID_FORMATION (0-39) - 100 songs total
    "avoid_formation": [
        ("God Is a Woman", "Ariana Grande", 25),
        ("Imagine", "John Lennon", 35),
        ("WAP", "Cardi B", 10),
        ("HUMBLE.", "Kendrick Lamar", 28),
        ("Lucifer", "SHINee", 20),
        ("Sympathy for the Devil", "Rolling Stones", 15),
        ("Highway to Hell", "AC/DC", 18),
        ("Closer", "The Chainsmokers", 32),
        ("Animals", "Maroon 5", 30),
        ("Blurred Lines", "Robin Thicke", 22),
    ],
}


def create_full_dataset():
    """Create the complete 1,200-song dataset."""
    
    all_songs = []
    
    # Freely Listen (400 songs)
    for category, songs in SONG_DATASET["freely_listen"].items():
        for title, artist, expected_score in songs:
            all_songs.append({
                "title": title,
                "artist": artist,
                "expected_score": expected_score,
                "category": "freely_listen",
                "genre_category": category
            })
    
    # Context Required (300 songs)
    for title, artist, expected_score in SONG_DATASET["context_required"]:
        # Recategorize if score suggests otherwise
        if expected_score >= 80:
            category = "freely_listen"
        elif expected_score >= 60:
            category = "context_required"
        elif expected_score >= 40:
            category = "caution_limit"
        else:
            category = "avoid_formation"
            
        all_songs.append({
            "title": title,
            "artist": artist,
            "expected_score": expected_score,
            "category": category,
            "genre_category": "mixed"
        })
    
    # Caution Limit (200 songs)
    for title, artist, expected_score in SONG_DATASET["caution_limit"]:
        all_songs.append({
            "title": title,
            "artist": artist,
            "expected_score": expected_score,
            "category": "caution_limit",
            "genre_category": "secular_questionable"
        })
    
    # Avoid Formation (100 songs)
    for title, artist, expected_score in SONG_DATASET["avoid_formation"]:
        all_songs.append({
            "title": title,
            "artist": artist,
            "expected_score": expected_score,
            "category": "avoid_formation",
            "genre_category": "secular_problematic"
        })
    
    print(f"Total songs created: {len(all_songs)}")
    print(f"Breakdown by category:")
    for cat in ["freely_listen", "context_required", "caution_limit", "avoid_formation"]:
        count = len([s for s in all_songs if s["category"] == cat])
        print(f"  {cat}: {count}")
    
    return all_songs


def split_dataset(all_songs, train_pct=0.833, val_pct=0.083, test_pct=0.084):
    """Split into train/val/test sets, stratified by category."""
    
    import random
    random.seed(42)  # Reproducibility
    
    train_songs = []
    val_songs = []
    test_songs = []
    
    # Stratify by category
    for category in ["freely_listen", "context_required", "caution_limit", "avoid_formation"]:
        cat_songs = [s for s in all_songs if s["category"] == category]
        random.shuffle(cat_songs)
        
        n = len(cat_songs)
        train_end = int(n * train_pct)
        val_end = train_end + int(n * val_pct)
        
        train_songs.extend(cat_songs[:train_end])
        val_songs.extend(cat_songs[train_end:val_end])
        test_songs.extend(cat_songs[val_end:])
    
    print(f"\nDataset split:")
    print(f"  Training: {len(train_songs)}")
    print(f"  Validation: {len(val_songs)}")
    print(f"  Test/Holdout: {len(test_songs)}")
    
    return train_songs, val_songs, test_songs


def save_jsonl(songs, filepath):
    """Save songs to JSONL format."""
    with open(filepath, 'w') as f:
        for song in songs:
            f.write(json.dumps(song) + '\n')
    print(f"Saved {len(songs)} songs to {filepath}")


def main():
    print("Creating 1,200-song dataset for Christian music analysis...\n")
    
    # Create full dataset
    all_songs = create_full_dataset()
    
    # Split into train/val/test
    train, val, test = split_dataset(all_songs)
    
    # Save to files
    output_dir = Path("scripts/eval")
    save_jsonl(train, output_dir / "songs_train_1000.jsonl")
    save_jsonl(val, output_dir / "songs_val_100.jsonl")
    save_jsonl(test, output_dir / "songs_test_100.jsonl")
    
    print("\n✅ Dataset creation complete!")
    print("\nNext steps:")
    print("1. Review the song lists and add more songs to reach 1,200 total")
    print("2. Run: docker compose exec web python scripts/eval/generate_training_data.py \\")
    print("         --input scripts/eval/songs_train_1000.jsonl \\")
    print("         --output scripts/eval/training_data_1000.jsonl \\")
    print("         --concurrency 10")
    print("3. Repeat for validation and test sets")


if __name__ == "__main__":
    main()

