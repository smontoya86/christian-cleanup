# Song Examples - Theological Analysis Reference

This directory contains 31 example song analyses demonstrating the Christian Framework v3.1 in action.

---

## 📋 Song Categories

### ✅ Freely Listen (High Quality Worship/Hymns)
**Score: 80-100 | Verdict: freely_listen**

Classic hymns and theologically sound contemporary worship:
- `amazing_grace.md` - Classic hymn on grace and redemption
- `be_thou_my_vision.md` - Celtic hymn on God-centered living
- `crown_him_with_many_crowns.md` - Christological worship
- `good_good_father.md` - God's character as Father
- `great_is_thy_faithfulness.md` - God's faithfulness
- `holy_holy_holy.md` - Trinitarian worship
- `how_deep_the_fathers_love.md` - Atonement and sacrifice
- `how_great_thou_art.md` - Creation and majesty
- `in_christ_alone.md` - Gospel-centered theology
- `it_is_well_with_my_soul.md` - Suffering and faith
- `the_lion_and_the_lamb.md` - Christ's dual nature
- `what_a_beautiful_name.md` - Incarnation and exaltation
- `what_a_friend_we_have_in_jesus.md` - Prayer and intimacy

### ⚠️ Context Required (Mixed Content)
**Score: 60-79 | Verdict: context_required**

Songs with helpful content but requiring discernment:
- `build_my_life.md` - Dedication and surrender
- `jireh.md` - God's provision (possible prosperity undertones)
- `king_of_my_heart.md` - Worship with emotional focus
- `living_hope.md` - Resurrection and hope
- `o_come_to_the_altar.md` - Invitation and response
- `oceans_where_feet_may_fail.md` - Faith and trust (vague at times)
- `way_maker.md` - Miracles and God's power (potential for misuse)

### 🚨 Caution/Limit (Significant Concerns)
**Score: 40-59 | Verdict: caution_limit**

Songs with theological issues or problematic content:
- `reckless_love.md` - Mischaracterization of God's love
- `theological_ambiguity_example.md` - Unclear theology
- `self_focused_contemporary.md` - Self-centered worship

### 🛑 Avoid Formation (Harmful Content)
**Score: 0-39 | Verdict: avoid_formation**

Songs promoting false teaching or harmful worldviews:
- `emotional_manipulation_example.md` - Manipulative worship techniques
- `monster.md` - Dark themes without redemptive message
- `prosperity_gospel_example.md` - Wealth and health gospel
- `self_focused_example.md` - Extreme self-focus
- `universalist_themes_example.md` - Universalism and pluralism

---

## 🎯 How to Use These Examples

### For Understanding the Framework
Each file demonstrates:
- ✅ Positive themes identified and scored
- ❌ Negative themes/concerns flagged
- 📖 Scripture references for theological justification
- 🎭 Narrative voice analysis (artist vs character)
- 💭 Lament filter application (when appropriate)
- 📊 Final score and verdict with reasoning

### For Training Data Validation
Compare model predictions against these reference analyses to check:
- Score accuracy (within 5-10 points)
- Verdict alignment
- Theme detection consistency
- Scripture citation quality

### For Manual Review
Use as templates when manually reviewing edge cases or disputed songs.

---

## 📚 File Format

Each song analysis follows this structure:

```markdown
# [Song Title]

**Artist:** [Artist Name]  
**Score:** [0-100]  
**Verdict:** [freely_listen|context_required|caution_limit|avoid_formation]  
**Formation Risk:** [Low|Medium|High]

## Lyrics
[Full lyrics or representative excerpt]

## Analysis

### Positive Themes
- Theme Name (+X points): Explanation

### Concerns
- Category (Severity): Explanation

### Scripture References
- Book Chapter:Verse - Connection to lyrics

### Verdict Rationale
[Detailed explanation of score and verdict]
```

---

## 🔍 Notable Edge Cases

### Lament Filter Applied
- `it_is_well_with_my_soul.md` - Grief expressed to God (not penalized)

### Character Voice Reduction
- `monster.md` - Dark narrative from character's perspective (reduced penalties)

### Common Grace Recognition
- Some secular songs (if added) would demonstrate moral good without explicit God-focus

### Vague Spirituality Cap
- `oceans_where_feet_may_fail.md` - Demonstrates the 45-point cap for unclear theology with God-language

---

## 📝 Notes

- These examples were created manually to represent key theological distinctions
- They informed the creation of the 1,378-song training dataset
- Use them as reference points when the fine-tuned model produces unexpected results
- Not all examples were included in the training data verbatim

---

**See Also:**
- `../documentation/SONG_SELECTION_GUIDE.md` - Guidelines for choosing evaluation songs
- `../documentation/FINETUNE_4O_MINI_RESULTS.md` - Model performance on these types of songs

