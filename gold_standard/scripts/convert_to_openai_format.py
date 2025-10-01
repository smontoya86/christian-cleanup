#!/usr/bin/env python3
"""
Convert the labeled dataset to OpenAI fine-tuning format.

Splits into:
- Training: 80% (1,097 songs)
- Validation: 10% (137 songs)
- Test: 10% (138 songs)

OpenAI fine-tuning format:
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
"""

import json
import random
from pathlib import Path
from typing import Dict, Any

# Seed for reproducibility
random.seed(42)

# Full Christian Framework v3.1 System Prompt (same as generate_training_data.py)
# Using FULL prompt for maximum training quality and consistency
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

def load_dataset(input_file: str) -> list:
    """Load the labeled dataset."""
    songs = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                songs.append(json.loads(line))
    return songs

def create_openai_message(song: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a song to OpenAI fine-tuning format."""
    
    # User message: song info and lyrics
    user_content = f"""Analyze the following song:

Title: {song['title']}
Artist: {song['artist']}

Lyrics:
{song['lyrics']}

Provide a theological analysis using the Christian Framework v3.1. Return ONLY valid JSON with the following structure:
- score (0-100)
- verdict (freely_listen|context_required|caution_limit|avoid_formation)
- formation_risk (low|medium|high)
- narrative_voice (artist|character|collective|God)
- lament_filter_applied (boolean)
- themes_positive (array of theme names with points)
- themes_negative (array of theme names with penalties)
- concerns (array of concern categories with severity)
- scripture_references (array of Bible references, 1-4 required)
- analysis (brief explanation)"""

    # Assistant message: the labeled JSON response
    assistant_content = json.dumps({
        "score": song['label']['score'],
        "verdict": song['label']['verdict'],
        "formation_risk": song['label']['formation_risk'],
        "narrative_voice": song['label']['narrative_voice'],
        "lament_filter_applied": song['label']['lament_filter_applied'],
        "themes_positive": song['label']['themes_positive'],
        "themes_negative": song['label']['themes_negative'],
        "concerns": song['label']['concerns'],
        "scripture_references": song['label']['scripture_references'],
        "analysis": song['label']['analysis']
    }, ensure_ascii=False)

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": assistant_content}
        ]
    }

def split_dataset(songs: list) -> tuple:
    """Split into train/val/test (80/10/10)."""
    # Shuffle for random split
    random.shuffle(songs)
    
    total = len(songs)
    train_size = int(total * 0.8)
    val_size = int(total * 0.1)
    
    train = songs[:train_size]
    val = songs[train_size:train_size + val_size]
    test = songs[train_size + val_size:]
    
    return train, val, test

def save_openai_format(songs: list, output_file: str):
    """Save songs in OpenAI fine-tuning format."""
    with open(output_file, 'w') as f:
        for song in songs:
            openai_format = create_openai_message(song)
            f.write(json.dumps(openai_format, ensure_ascii=False) + '\n')

def main():
    # Paths
    input_file = 'scripts/eval/training_data_1378_final.jsonl'
    output_dir = Path('scripts/eval/openai_finetune')
    output_dir.mkdir(exist_ok=True)
    
    print("=" * 80)
    print("CONVERTING TO OPENAI FINE-TUNING FORMAT")
    print("=" * 80)
    print()
    
    # Load dataset
    print(f"Loading dataset from: {input_file}")
    songs = load_dataset(input_file)
    print(f"✅ Loaded {len(songs)} songs")
    print()
    
    # Split dataset
    print("Splitting dataset (80/10/10)...")
    train, val, test = split_dataset(songs)
    print(f"  • Training:   {len(train):4d} songs (80%)")
    print(f"  • Validation: {len(val):4d} songs (10%)")
    print(f"  • Test:       {len(test):4d} songs (10%)")
    print()
    
    # Convert and save
    print("Converting to OpenAI format...")
    
    train_file = output_dir / 'train.jsonl'
    val_file = output_dir / 'validation.jsonl'
    test_file = output_dir / 'test.jsonl'
    
    save_openai_format(train, str(train_file))
    print(f"  ✅ Training data:   {train_file}")
    
    save_openai_format(val, str(val_file))
    print(f"  ✅ Validation data: {val_file}")
    
    save_openai_format(test, str(test_file))
    print(f"  ✅ Test data:       {test_file}")
    print()
    
    # Show example
    print("=" * 80)
    print("EXAMPLE TRAINING ENTRY (first song)")
    print("=" * 80)
    print()
    example = create_openai_message(train[0])
    print("System:", example['messages'][0]['content'][:100] + "...")
    print()
    print("User:", example['messages'][1]['content'][:200] + "...")
    print()
    print("Assistant:", example['messages'][2]['content'][:200] + "...")
    print()
    
    # Summary
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Upload training file to OpenAI:")
    print(f"   openai api files.create -f {train_file} -p fine-tune")
    print()
    print("2. Upload validation file to OpenAI:")
    print(f"   openai api files.create -f {val_file} -p fine-tune")
    print()
    print("3. Start fine-tuning job:")
    print("   openai api fine_tuning.jobs.create \\")
    print("     -t <training_file_id> \\")
    print("     -v <validation_file_id> \\")
    print("     -m gpt-4o-mini-2024-07-18 \\")
    print("     --suffix christian-discernment-v1")
    print()
    print("4. Monitor training:")
    print("   openai api fine_tuning.jobs.retrieve -i <job_id>")
    print()
    print("Expected fine-tuning cost: ~$10-20")
    print("Expected training time: 1-3 hours")
    print()

if __name__ == '__main__':
    main()

