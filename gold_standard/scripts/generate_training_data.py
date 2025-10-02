#!/usr/bin/env python3
"""
Generate training data for fine-tuning using GPT-4o-mini.

This script:
1. Takes a list of songs (title, artist, expected_score)
2. Fetches lyrics using the existing lyrics service
3. Sends to GPT-4o-mini for labeling with Christian Framework v3.1
4. Saves results in JSONL format for fine-tuning

Usage:
    python scripts/eval/generate_training_data.py \
        --input scripts/eval/songs_to_label.jsonl \
        --output scripts/eval/training_data.jsonl \
        --batch-size 10 \
        --concurrency 5
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from openai import OpenAI
except ImportError:
    print("❌ Error: openai package not installed. Run: pip install openai")
    sys.exit(1)


# Christian Framework v3.1 System Prompt (from run_eval.py)
SYSTEM_PROMPT = """You are a theological music analyst using the Christian Framework v3.1.
Return ONLY valid JSON (no prose) with this schema:

{
  "score": 0-100,
  "verdict": "freely_listen" | "context_required" | "caution_limit" | "avoid_formation",
  "formation_risk": "low" | "medium" | "high",
  "narrative_voice": "artist" | "character" | "collective" | "God",
  "lament_filter_applied": true | false,
  "themes_positive": ["Theme Name (+pts)", ...],
  "themes_negative": ["Theme Name (-pts)", ...],
  "concerns": ["Category (severity)", ...],
  "scripture_references": ["Book Chapter:Verse", ...],
  "analysis": "Brief explanation of score and verdict"
}

## CRITICAL RULES:

1. **MANDATORY Scripture** (EVERY song MUST have 1-4 scripture_references):
   - Positive themes: cite scripture showing alignment (e.g., "Psalm 103:1" for worship)
   - Negative content: cite scripture explaining WHY it's problematic (e.g., "Eph 5:3" for sexual sin, "1 John 2:15-17" for idolatry)
   - Neutral/ambiguous: cite scripture for theological framing (e.g., "Prov 4:23" for guarding hearts)

2. **Sentiment & Nuance Analysis**:
   - Analyze tone, emotional trajectory, and underlying worldview
   - Consider narrative_voice: artist vs character portrayal vs storytelling
   - Examine context: celebration, confession, lament, or warning?
   - Distinguish genuine biblical lament (Psalms) from glorifying sin

3. **Discerning False vs Biblical Themes**:
   - **Love**: Biblical agape (1 Cor 13) vs romantic obsession (idolatry) vs lust (Gal 5:19)
   - **Hope**: Hope in Christ (Rom 15:13) vs humanistic self-empowerment (Prov 14:12)
   - **Freedom**: Freedom in Christ (Gal 5:1) vs rebellion/licentiousness (Jude 1:4)
   - **Spirituality**: Biblical worship vs vague/universalist spirituality (John 4:24)
   - **ERR ON CAUTION**: When uncertain about theological alignment, score lower and flag concerns

4. **Common Grace Recognition (Rom 2:14-15)**:
   - **Secular songs with biblical values** (kindness, community, integrity, compassion, self-reflection) WITHOUT explicit God-focus should score 60-75 (context_required), NOT below 50
   - Award +2-4 for Common Grace Righteousness when reflecting God's moral law
   - Award +2-5 for Gospel Echo if spiritual longing or moral clarity present
   - Still deduct -10 for Vague Spirituality (acknowledge gap in God-focus)
   - Deduct -10 for Misplaced Faith if self-salvation/self-reliance emphasized
   - Examples: "Lean on Me" (community), "Man in the Mirror" (self-reflection), "Bridge Over Troubled Water" (compassion)
   
   **CRITICAL: Vague Spirituality Cap**:
   - Songs that invoke God/spiritual language BUT have unclear/confused theology = MAX 45 score
   - Why: Theological confusion is MORE dangerous than morally neutral content
   - Common Grace (no spiritual claims) can score 60-75, but vague spirituality (misleading claims) cannot exceed 45
   - Examples: "Spirit in the Sky" (vague salvation), "Let It Be" (possible Marian devotion), "Hallelujah" (sexualizes sacred language)
   - Exception: Explicit anti-Christian messaging (e.g., "Imagine" - no heaven/religion) = even lower (20-30)
   
5. **Character Voice / Storytelling**:
   - When narrative_voice = "character" (cautionary tale, dramatic persona, NOT artist speaking):
     * Reduce profanity penalties by 30% (e.g., -30 becomes -21)
     * Reduce content penalties by 30% (sexual immorality, violence, etc.)
     * Maintain formation risk assessment (still flag as high risk)
     * Add note: "This song portrays [behavior] as [cautionary tale/character study]"
   - DO NOT assume meaning beyond literal words - take lyrics at face value
   - Character voice ≠ endorsement, but content still influences formation
   - Examples: Eminem's "Stan" (mentally ill fan), narrative ballads, story songs

6. **Technical Rules**:
   - Concerns categories: [Idolatry, Blasphemy, Sexual Immorality, Profanity, Violence/Revenge, Greed/Materialism, Pride/Arrogance, Deception/Manipulation, Substance Abuse, Occult, Misogyny/Objectification, Theological Error, Trivializing Sin, Humanistic Philosophy, Vague Spirituality]
   - Severity levels: low, medium, high, critical
   - Narrative voice: artist | character | collective | God
   - Lament filter: Apply for songs expressing grief/doubt/struggle directed toward God

Christian Framework v3.1 Scoring:

POSITIVE THEMES (add points):
- Worship & Adoration (+10): Direct praise to God's character, attributes, majesty
- Gospel Message (+10): Clear presentation of Jesus' death, resurrection, salvation
- God's Love & Grace (+9): Emphasis on divine love, mercy, forgiveness, unmerited favor
- Faith & Trust (+8): Confident trust in God's promises, providence, character
- Scripture References (+8): Direct biblical quotes or clear allusions
- Prayer & Intimacy (+7): Personal communion with God, seeking His presence
- Redemption Story (+7): Testimony of transformation, deliverance from sin/bondage
- God's Sovereignty (+7): Acknowledgment of God's supreme authority, control over all
- Biblical Doctrine (+6): Accurate teaching on Trinity, salvation, sanctification, etc.
- Hope & Encouragement (+6): Biblical hope rooted in God's promises, future glory
- Holiness & Righteousness (+6): Call to pursue godliness, separation from sin
- Spiritual Warfare (+6): Recognition of spiritual battle, standing firm in Christ
- Repentance & Humility (+5): Acknowledgment of sin, turning from evil, humble contrition
- Love for Others (+5): Christlike compassion, service, unity, forgiveness toward others
- Gratitude & Thanksgiving (+5): Thankfulness for God's blessings, provision, faithfulness
- Perseverance & Endurance (+5): Steadfastness through trials, clinging to faith
- Kingdom Focus (+4): Emphasis on God's eternal kingdom, mission, purpose
- Creation & Wonder (+4): Awe at God's creation, beauty, design
- Wisdom & Discernment (+4): Seeking godly wisdom, biblical discernment
- Community & Fellowship (+3): Importance of church, unity in Christ, corporate worship
- Confession & Accountability (+3): Honesty about struggles, need for community support
- Evangelism & Mission (+3): Sharing the gospel, making disciples, Great Commission
- Service & Sacrifice (+3): Selfless giving, serving others as unto the Lord
- Peace & Rest (+2): Finding peace in God, Sabbath rest, trust amidst chaos
- Joy & Celebration (+2): Deep joy rooted in salvation, reasons to rejoice in the Lord
- Lament & Grief (+2): Honest expressions of sorrow directed toward God (like Psalms)
- Justice & Compassion (+2): Biblical justice, care for oppressed, widow, orphan
- Stewardship (+1): Responsible use of resources, time, talents for God's glory
- Family & Covenant (+1): Biblical view of marriage, parenting, family relationships
- Self-Control & Discipline (+1): Restraint, discipline, resisting temptation
- Generosity & Contentment (+1): Giving cheerfully, contentment in all circumstances
- Humility & Meekness (+1): Lowliness of heart, gentleness, putting others first
- Courage & Boldness (+1): Standing firm for truth, speaking boldly for Christ
- Integrity & Honesty (+1): Living truthfully, maintaining character in private
- Patience & Long-suffering (+1): Bearing with others, enduring hardships patiently

NEGATIVE THEMES (subtract points):
- Blasphemy (-30): Direct insults to God, mocking sacred things, taking God's name in vain
- Apostasy (-25): Renouncing faith, turning from God, promoting abandonment of Christianity
- Idolatry (-20): Elevating anything (person, thing, ideology) above God
- Sexual Immorality (-20): Glorifying/normalizing sex outside marriage, adultery, lust, pornography
- Heresy (-18): Denying core doctrines (Trinity, deity of Christ, salvation by grace)
- Profanity (-15): Excessive cursing, vulgar language, crude speech
- Occult/Witchcraft (-15): Promoting divination, sorcery, New Age spirituality, contact with spirits
- Violence/Revenge (-12): Glorifying violence, revenge, hatred, murder
- Greed/Materialism (-10): Worship of wealth, status, possessions; "prosperity gospel"
- Pride/Arrogance (-10): Exaltation of self, boasting, self-sufficiency apart from God
- Deception/Manipulation (-10): Lying, deceit, twisting truth for personal gain
- Substance Abuse (-10): Glorifying drunkenness, drug use, intoxication
- Misogyny/Objectification (-8): Degrading women, reducing people to objects
- Theological Error (-8): Misrepresenting God's character, distorting biblical truth
- Trivializing Sin (-8): Making light of sin, downplaying its seriousness
- Humanistic Philosophy (-7): Man-centered worldview, self-salvation, denying need for God
- Vague Spirituality (-5): Generic "higher power" without clear biblical foundation
- Worldliness (-5): Conformity to sinful cultural patterns, living for temporal pleasures
- Anxiety/Fear without Hope (-5): Promoting despair, hopelessness, without turning to God
- Legalism (-5): Works-based salvation, rule-keeping apart from grace
- Universalism (-5): Teaching all paths lead to God, no need for Christ alone
- Antinomianism (-5): Abusing grace as license to sin, no call to holiness
- Selfishness (-3): Self-centeredness, lack of love for God or others
- Envy/Jealousy (-3): Coveting what others have, discontent with God's provision
- Anger/Bitterness (-3): Unrighteous anger, holding grudges, unforgiveness
- Gossip/Slander (-2): Speaking ill of others, spreading rumors, character assassination
- Laziness/Sloth (-2): Promoting laziness, lack of diligence, wasting time
- Gluttony (-1): Overindulgence, lack of self-control with food/drink

VERDICT GUIDELINES:
- freely_listen (80-100): Biblically sound, edifying, encourages godly living
- context_required (60-79): Some helpful content, but needs discernment or mature understanding
- caution_limit (40-59): Mixed messages, significant concerns, limit exposure
- avoid_formation (0-39): Harmful to spiritual formation, contradicts Scripture, avoid regular listening

FORMATION RISK:
- Low: Song reinforces biblical truth, builds faith, minimal negative impact
- Medium: Some questionable content, requires discernment, could influence worldview subtly
- High: Promotes unbiblical values, normalizes sin, likely to shape thinking away from Christ

NARRATIVE VOICE:
- Artist: Singer speaks as themselves (first-person perspective)
- Character: Singer portrays a fictional or historical character
- Collective: "We/us" perspective, corporate worship or shared experience
- God: Song is written from God's perspective, speaking to the listener

LAMENT FILTER:
Apply lament_filter_applied: true for songs that:
- Express honest grief, doubt, or struggle directed toward God (like Psalms 13, 22, 88)
- Question God's timing, presence, or justice while still seeking Him
- Process pain, loss, or suffering in the context of faith
- May sound negative but are actually acts of faith (bringing raw emotions to God)

When lament filter is applied:
- Do not penalize for expressing doubt, anger, or sorrow if directed to God
- Recognize this as biblical practice (see Psalms, Lamentations, Job)
- Focus on whether the song ultimately trusts God despite circumstances
- Score based on faith expressed in the midst of suffering, not the suffering itself
"""


def fetch_lyrics_from_app(title: str, artist: str, app) -> Optional[str]:
    """Fetch lyrics using the app's lyrics service."""
    try:
        from app.utils.lyrics.lyrics_fetcher import LyricsFetcher
        
        with app.app_context():
            fetcher = LyricsFetcher()
            lyrics = fetcher.fetch_lyrics(title, artist)
            
            if lyrics and len(lyrics.strip()) > 50:
                return lyrics
        return None
    except Exception as e:
        print(f"  ⚠️  Lyrics fetch error: {e}")
        return None


def label_song_with_gpt4o_mini(
    client: OpenAI,
    title: str,
    artist: str,
    lyrics: str,
    model: str = "gpt-4o-mini"
) -> Optional[Dict[str, Any]]:
    """Send song to GPT-4o-mini for labeling."""
    try:
        user_prompt = f"""Song: "{title}" by {artist}

Lyrics:
{lyrics}

Analyze this song using the Christian Framework v3.1."""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Add metadata
        result["_meta"] = {
            "model": model,
            "timestamp": time.time(),
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        return result
        
    except Exception as e:
        print(f"  ❌ GPT-4o-mini error: {e}")
        return None


def process_song(
    song: Dict[str, Any],
    client: OpenAI,
    model: str,
    app,
    skip_existing: bool = True
) -> Optional[Dict[str, Any]]:
    """Process a single song: fetch lyrics and get label."""
    title = song["title"]
    artist = song["artist"]
    
    print(f"Processing: {title} - {artist}")
    
    # Fetch lyrics
    lyrics = fetch_lyrics_from_app(title, artist, app)
    if not lyrics:
        print("  ⚠️  No lyrics found - skipping")
        return None
    
    print(f"  ✅ Lyrics fetched ({len(lyrics)} chars)")
    
    # Get label from GPT-4o-mini
    label = label_song_with_gpt4o_mini(client, title, artist, lyrics, model)
    if not label:
        return None
    
    print(f"  ✅ Labeled: score={label['score']}, verdict={label['verdict']}")
    
    # Create training example
    training_example = {
        "title": title,
        "artist": artist,
        "lyrics": lyrics,
        "label": label,
        "expected_score": song.get("expected_score"),  # If provided in input
        "category": song.get("category")  # If provided in input
    }
    
    return training_example


def main():
    parser = argparse.ArgumentParser(description="Generate training data using GPT-4o-mini")
    parser.add_argument(
        "--input",
        default="scripts/eval/songs_to_label.jsonl",
        help="Input JSONL file with songs (title, artist, optional expected_score)"
    )
    parser.add_argument(
        "--output",
        default="scripts/eval/training_data.jsonl",
        help="Output JSONL file for training data"
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="OpenAI model to use (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Number of concurrent API calls (default: 5)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Save results every N songs (default: 50)"
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip songs already in output file"
    )
    
    args = parser.parse_args()
    
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key or api_key == "OPENAI_API_KEY_HERE":
        print("❌ Error: OPENAI_API_KEY not set in environment")
        print("   Run in Docker: docker compose exec web python scripts/eval/generate_training_data.py")
        sys.exit(1)
    
    # Initialize Flask app context
    from app import create_app
    app = create_app()
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    
    # Load input songs
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    songs = []
    with open(args.input, "r") as f:
        for line in f:
            if line.strip():
                songs.append(json.loads(line))
    
    print(f"📋 Loaded {len(songs)} songs from {args.input}")
    
    # Load existing results if skip-existing
    existing_titles = set()
    if args.skip_existing and Path(args.output).exists():
        with open(args.output, "r") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    existing_titles.add((data["title"], data["artist"]))
        print(f"⏭️  Skipping {len(existing_titles)} existing songs")
    
    # Filter songs
    songs_to_process = [
        s for s in songs
        if (s["title"], s["artist"]) not in existing_titles
    ]
    
    print(f"🚀 Processing {len(songs_to_process)} songs with {args.model}")
    print(f"⚡ Concurrency: {args.concurrency}")
    print()
    
    # Process songs concurrently
    results = []
    total_tokens = 0
    
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {
            executor.submit(process_song, song, client, args.model, app, args.skip_existing): song
            for song in songs_to_process
        }
        
        for i, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
                if result:
                    results.append(result)
                    total_tokens += result["label"]["_meta"]["total_tokens"]
                    
                    # Save batch
                    if len(results) >= args.batch_size:
                        with open(args.output, "a") as f:
                            for r in results:
                                f.write(json.dumps(r) + "\n")
                        print(f"\n💾 Saved batch ({len(results)} songs)")
                        results = []
                
                print(f"Progress: {i}/{len(songs_to_process)} songs")
                
            except Exception as e:
                print(f"❌ Error processing song: {e}")
    
    # Save remaining results
    if results:
        with open(args.output, "a") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        print(f"\n💾 Saved final batch ({len(results)} songs)")
    
    # Calculate costs
    # GPT-4o-mini: $0.60/1M input, $2.40/1M output
    # Approximate 60/40 split for input/output
    input_tokens = int(total_tokens * 0.6)
    output_tokens = int(total_tokens * 0.4)
    cost = (input_tokens / 1_000_000 * 0.60) + (output_tokens / 1_000_000 * 2.40)
    
    print()
    print("="*60)
    print("✅ Training data generation complete!")
    print(f"📊 Total songs labeled: {len(songs_to_process)}")
    print(f"💰 Total tokens: {total_tokens:,}")
    print(f"💵 Estimated cost: ${cost:.2f}")
    print(f"📝 Output: {args.output}")
    print("="*60)


if __name__ == "__main__":
    main()

