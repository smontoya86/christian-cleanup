# 🎚️ Theological Discernment & Scoring Framework

**Version 3.1** - Updated January 2025
**Scope**: Universal Music Analysis with Christian Evaluation Criteria
**Architecture**: Direct ML Analysis with Model Caching (Queue System Removed)

## 📋 Framework Overview

This framework provides comprehensive theological analysis for **all music genres**, evaluating lyrical content against biblical standards. The system uses machine learning models for sentiment analysis, content safety, emotion detection, and zero-shot theme classification to provide accurate spiritual discernment.

### **Key Features:**
- **35+ Theological Themes**: Comprehensive coverage of positive and negative spiritual content
- **Weighted Scoring System**: Nuanced point allocation based on theological significance
- **Formational Impact Assessment**: Evaluates how songs shape spiritual formation
- **Scripture-Grounded Analysis**: Every theme anchored in biblical truth
- **Universal Application**: Works for Christian, secular, and mixed-genre content

### **Technical Architecture:**
- **OpenAI API Integration**: Fine-tuned GPT-4o-mini model for analysis
- **Direct API Calls**: Immediate, high-quality theological analysis
- **Batch Processing**: Efficient analysis of multiple songs simultaneously
- **Admin-Only Re-analysis**: Restricted access for quality control

## ✅ Positive Themes (Add to Score)

| Theme | Description | Scripture Anchor | Points |
|-------|-------------|------------------|--------|
| Christ-Centered | Jesus as Savior, Lord, or King | John 14:6 | +10 |
| Gospel Presentation | Cross, resurrection, salvation by grace | 1 Cor. 15:3–4 | +10 |
| Repentance | Turning from sin to God | Acts 3:19 | +7 |
| Redemption | Deliverance by grace | Eph. 1:7 | +7 |
| Worship of God | Reverence, praise, glory to God | Psalm 29:2 | +7 |
| Hope | Trust in God's promises | Rom. 15:13 | +6 |
| Humility | Low view of self, exalted view of God | James 4:6 | +6 |
| Sacrificial Love | Christlike self-giving | John 15:13 | +6 |
| Forgiveness | Offering or receiving mercy | Col. 3:13 | +6 |
| Endurance | Perseverance by faith | James 1:12 | +6 |
| Light vs Darkness | Spiritual clarity and contrast | John 1:5 | +5 |
| Obedience | Willingness to follow God | John 14:15 | +5 |
| Justice | Advocacy for truth and righteousness | Micah 6:8 | +5 |
| Deliverance | Rescue from danger or evil | Psalm 34:17 | +5 |
| Identity in Christ | New creation reality | 2 Cor. 5:17 | +5 |
| Brokenness / Contrition | Humble acknowledgment of sin | Psalm 51:17 | +5 |
| Gratitude | Thankful posture before God | 1 Thess. 5:18 | +4 |
| Discipleship | Following Jesus intentionally | Luke 9:23 | +4 |
| Evangelistic Zeal | Passion to proclaim Christ | Rom. 1:16 | +4 |
| Mercy | Compassion for others | Micah 6:8 | +4 |
| Truth | Moral and doctrinal fidelity | John 8:32 | +4 |
| God's Sovereignty | Acknowledging divine rule | Dan. 4:35 | +4 |
| Victory in Christ | Triumph over sin and death | 1 Cor. 15:57 | +4 |
| Awe / Reverence | Holy fear of the Lord | Prov. 1:7 | +3 |
| Heaven-mindedness | Eternal perspective | Col. 3:1–2 | +3 |
| Reconciliation | Restoration with God or others | 2 Cor. 5:18 | +3 |
| Community / Unity | Gospel-centered fellowship | Acts 2:42 | +3 |
| Transformation | Sanctification and life change | Rom. 12:2 | +3 |
| Selflessness | Putting others before self | Phil. 2:3–4 | +3 |
| Restoration | Healing from brokenness | Joel 2:25 | +3 |
| Prayer | Calling on God in faith | 1 Thess. 5:17 | +3 |
| Peace | Internal and external peace through Christ | John 14:27 | +3 |
| Conviction | Awareness of sin and truth | John 16:8 | +2 |
| Calling / Purpose | Walking in God's mission | Eph. 2:10 | +2 |
| God's Faithfulness | Confidence in God's promises | Lam. 3:22–23 | +2 |
| Joy in Christ | Gospel-rooted joy | Phil. 4:4 | +2 |
| Common Grace Righteousness | Moral clarity w/o gospel | Rom. 2:14–15 | +2 to +4 |
| Gospel Echo | Spiritual longing that aligns with gospel truth | Psalm 38:9 | +2 to +5 |

## ❌ Negative Themes (Subtract from Score)

| Theme | Description | Scripture Anchor | Penalty |
|-------|-------------|------------------|---------|
| Blasphemy | Mocking God or sacred things | Ex. 20:7 | –30 |
| Profanity | Obscene or degrading language | Eph. 4:29 | –30+ |
| Self-Deification | Making self god | Isa. 14:13–14 | –25 |
| Apostasy | Rejection of gospel or faith | Heb. 6:6 | –25 |
| Pride / Arrogance | Self-glorification | Prov. 16:18 | –20 |
| Nihilism | Belief in meaninglessness | Eccl. 1:2 | –20 |
| Despair without Hope | Hopeless fatalism | 2 Cor. 4:8–9 | –20 |
| Suicide Ideation / Death Wish | Wanting death w/o God | Jonah 4:3 | –25 |
| Self-Harm | Encouraging self-injury | 1 Cor. 6:19–20 | –20 |
| Violence Glorified | Exalting brutality | Rom. 12:19 | –20 |
| Hatred / Vengeance | Bitterness, retaliation | Matt. 5:44 | –20 |
| Sexual Immorality | Lust, adultery, etc. | 1 Cor. 6:18 | –20 |
| Drug / Alcohol Glorification | Escapist culture | Gal. 5:21 | –20 |
| Idolatry | Elevating created over Creator | Rom. 1:25 | –20 |
| Sorcery / Occult | Magical or demonic practices | Deut. 18:10–12 | –20 |
| Moral Confusion | Reversing good and evil | Isa. 5:20 | –15 |
| Denial of Sin | Rejecting sinfulness | 1 John 1:8 | –15 |
| Justification of Sin | Excusing rebellion | Isa. 30:10 | –15 |
| Pride in Sin | Boasting in immorality | Jer. 6:15 | –15 |
| Spiritual Confusion | Blending false ideologies | Col. 2:8 | –15 |
| Materialism / Greed | Worship of wealth | 1 Tim. 6:10 | –15 |
| Self-Righteousness | Works-based pride | Luke 18:11–12 | –15 |
| Misogyny / Objectification | Degrading God's image | Gen. 1:27 | –15 |
| Racism / Hatred of Others | Tribalism or supremacy | Gal. 3:28 | –15 |
| Hopeless Grief | Mourning without resurrection | 1 Thess. 4:13 | –15 |
| Vague Spirituality | Undefined spiritual references | 2 Tim. 3:5 | –10 |
| Empty Positivity | Self-help without truth | Jer. 17:5 | –10 |
| Misplaced Faith | Trust in self or fate | Psalm 20:7 | –10 |
| Vanity | Shallow self-focus | Eccl. 2:11 | –10 |
| Fear-Based Control | Spiritual manipulation | 2 Tim. 1:7 | –10 |
| Denial of Judgment | No consequences | Heb. 9:27 | –10 |
| Relativism | "Truth is whatever" | John 17:17 | –10 |
| Aimlessness | Lack of purpose | Prov. 29:18 | –10 |
| Victim Identity | Hopelessness as identity | Rom. 8:37 | –10 |
| Ambiguity | Lyrical confusion | 1 Cor. 14:8 | –5 |

## 🛑 Formational Weight Multiplier (–10)

**When It Applies:**
- 3 or more negative themes, each –15 or worse
- Emotional tone immerses listener in spiritual darkness
- No Gospel Echo, no Common Grace, no redemptive arc

**Explanation (to be included in analysis):**
> This song immerses the listener in spiritually harmful themes (e.g., despair, rage, lust), reinforced by emotionally immersive tone. It presents no redemptive truth or gospel tension, which may form the listener toward spiritual resignation, fatalism, or rebellion.

## 🎯 Theological Significance Weighting

**Core Gospel Themes (1.5x multiplier):**
- Christ-Centered, Gospel Presentation, Redemption, Repentance
- These themes receive enhanced weighting due to their salvific importance

**Character Formation Themes (1.2x multiplier):**
- Hope, Humility, Sacrificial Love, Forgiveness, Endurance, Obedience
- These themes shape Christian character and discipleship

**Common Grace Themes (1.0x multiplier):**
- Justice, Mercy, Truth, Peace, Community
- These reflect God's general revelation and moral order

## 🔄 Analysis Process & Quality Standards

### **ML Pipeline Integration:**
1. **Sentiment Analysis**: Emotional tone evaluation
2. **Content Safety**: Harmful content detection
3. **Emotion Classification**: Psychological impact assessment
4. **Theme Detection**: Zero-shot classification against 35+ theological themes
5. **Scripture Mapping**: Automated biblical reference assignment
6. **Score Calculation**: Weighted point system with multipliers
7. **Verdict Generation**: Summary + Formation guidance

### **Quality Assurance:**
- **100% Accuracy Target**: Perfect scores for legitimate Christian content
- **Concern Level Calibration**: Very Low, Low, Medium, High, Critical
- **Scripture Validation**: All references use Berean Standard Bible (BSB)
- **Formation Impact**: Clear guidance on spiritual influence

## 🧾 Verdict Format

1. **🎯 Summary Verdict** — A 1-line statement about the song's spiritual core.
2. **📌 Spiritual Formation Guidance** — 1–2 sentences explaining what the song might form in a listener and how it should be approached (e.g., conversation only, safe for repetition, redeemable with context).

---

# 📘 Examples for Scoring and Discernment

These examples show how to apply the framework accurately. Every song must be evaluated on themes, tone, and spiritual impact — not just lyric quotes.

---

## ✅ Example: "Shadows" – Wolves At The Gate

### 🎯 Identified Themes:
- Christ-Centered (+10)
- Gospel Presentation (+10)
- Redemption (+7)
- Light vs Darkness (+5)
- Brokenness / Contrition (+5)
- Victory in Christ (+4)

### 📖 Example Scripture Support:
> "In Him we have redemption through His blood, the forgiveness of our trespasses, according to the riches of His grace." — Ephesians 1:7 (BSB)
> "The Light shines in the darkness, and the darkness has not overcome it." — John 1:5 (BSB)

### ⚖️ Final Score: 100 (Capped)

### 🧾 Verdict:
**Summary:** Gospel-rich, theologically grounded, spiritually edifying.
**Spiritual Guidance:** This is worship disguised as a metal anthem. It forms Christ-centered identity, hope, and reverence in the listener.

---

## ❌ Example: "Doomsday" – Architects

### 🎯 Identified Themes:
- Despair without Hope (–20)
- Nihilism (–20)
- Moral Confusion (–15)
- Ambiguity (–5)
- Gospel Echo (+3)
- Common Grace Righteousness (+2)

### 📖 Example Scripture Support:
> "'Futility of futilities,' says the Teacher. 'Futility of futilities! Everything is futile!'" — Ecclesiastles 1:2 (BSB)
> "We are hard pressed on all sides, but not crushed; perplexed, but not in despair." — 2 Corinthians 4:8 (BSB)

### 🛑 Formational Weight Multiplier Applied (–10)
> _This song immerses the listener in despair, futility, and moral confusion with no gospel tension or resolution. Its emotional intensity reinforces spiritual fatalism._

### ⚖️ Final Score: 35

### 🧾 Verdict:
**Summary:** Spiritually crushing and directionless.
**Spiritual Guidance:** Lament without hope becomes spiritual dead weight. This is not a safe companion for sorrow. Avoid for formation; use only as a bridge to gospel conversations.

---

## ⚠️ Example: "I Believe" – Killswitch Engage

### 🎯 Identified Themes:
- Hope (+6)
- Gospel Echo (+3)
- Common Grace Righteousness (+2)
- Vague Spirituality (–10)
- Misplaced Faith (–10)
- Ambiguity (–5)

### 📖 Example Scripture Support:
> "Having a form of godliness but denying its power. Turn away from such as these!" — 2 Timothy 3:5 (BSB)

### ⚖️ Final Score: 86

### 🧾 Verdict:
**Summary:** Morally uplifting, spiritually vague.
**Spiritual Guidance:** Encouraging in tone, but lacks doctrinal clarity or saving truth. Listeners should beware mistaking inspiration for spiritual substance.

---

## 🚀 Future Enhancement Roadmap

### **Completed Enhancements**
- ✅ **Fine-Tuned GPT-4o-mini**: Trained on 1,378 songs with Christian Framework v3.1
- ✅ **80.4% Verdict Accuracy**: High-quality theological analysis
- ✅ **OpenAI API Integration**: Reliable, scalable analysis infrastructure
- ✅ **Comprehensive Dataset**: Multi-genre coverage with biblical evaluation

### **Future Advanced Features**
- **Multilingual Analysis**: Extend to Spanish, Portuguese, and other languages
- **Enhanced Confidence Scoring**: Uncertainty quantification for edge cases
- **Genre-Specific Tuning**: Further refinement for metal, hip-hop, country analysis
- **Batch Optimization**: Performance improvements for large playlist analysis

## 🔧 Technical Implementation Notes

### **Current Architecture:**
- **Framework**: Flask + OpenAI API
- **Model**: Fine-tuned GPT-4o-mini (ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav)
- **Caching**: AnalyzerCache with singleton pattern
- **Processing**: Direct OpenAI API calls with batch support
- **Database**: PostgreSQL with analysis result storage
- **Access Control**: Admin-only re-analysis functionality

### **Fine-Tuned Model Details:**
- **Training Data**: 1,378 songs with Christian Framework v3.1 labels
- **Training Cost**: ~$30 for GPT-4o-mini fine-tuning
- **Inference Cost**: $0.0006 per song (~$6 per 10,000 songs)
- **Performance**: 80.4% verdict accuracy, 4.47 MAE on hold-out set
- **Deployment**: OpenAI-hosted, accessible via API key

## 📚 Usage Guidelines

Use these examples and guidelines to model future analyses. Be thorough, quote full Scripture (BSB), apply score logic fairly, and always offer a pastoral verdict rooted in spiritual formation.

**Important Notes:**
- Scripture references in examples are illustrative - each analysis should use contextually appropriate verses
- All biblical quotations use the Berean Standard Bible (BSB)
- Framework designed for universal music analysis with Christian evaluation criteria
- System optimized for admin-driven re-analysis with immediate batch processing
- Model caching ensures consistent performance without API dependencies

**Training Data Potential:**
This framework and its current analysis results represent a valuable training dataset for custom model development. The combination of lyrical content, theological themes, and formation guidance provides rich supervision for fine-tuning open-source language models specifically for Christian music discernment.

---

# ▲ v3.1 Updates — Enhanced Features

## ▲ v3.1 Update — Dual Scoring System

Added **Purity Score** (0–100) and **Formation Risk** (Very Low → Critical). Only the **Pastoral Verdict** is binding for users.

### **Purity Score (0–100)**
Traditional scoring system based on positive and negative themes with enhanced accuracy.

### **Formation Risk Assessment**
- **Very Low**: Minimal spiritual formation concerns
- **Low**: Minor concerns, generally safe
- **High**: Significant formation risks present
- **Critical**: Severe spiritual formation dangers

## ▲ v3.1 Update — Lament Filter

Distinguishes biblical lament from nihilism. Applies when confidence ≥0.70 based on:

### **Activation Criteria**
1. **Address to God**: Direct or implied communication with the divine
2. **Trajectory toward hope/surrender/plea**: Movement beyond despair
3. **Moral stance acknowledging brokenness**: Recognition of sin/fallenness

### **When Applied**
- Reduces Despair/Nihilism penalties by 50%
- Adds +2 Gospel Echo bonus
- Maintains content in "Context Required" tier minimum

## ▲ v3.1 Update — Narrative Voice Detection

### **Voice Categories**
- **Artist**: Direct personal expression from the musician
- **Character**: Fictional or dramatic persona speaking
- **Ambiguous**: Unclear perspective or mixed voices

### **Impact on Scoring**
- Heavy penalties reduced for **character** voices
- **Artist** voice receives full penalty weight
- **Ambiguous** voice receives moderate penalty reduction

## ▲ v3.1 Update — Ambiguity & Metaphor Handling

**Base Penalty**: –5 for ambiguous content

### **Adjustments**
- **Removed** if metaphors map consistently to orthodox themes
- **Increased to –10** if contradictions exist between metaphors
- **+3 Clarity Anchor** added where direct doctrinal grounding exists

## ▲ v3.1 Update — Penalty Caps & Escalators

### **Penalty Caps**
- **Blasphemy**: –30 (maximum)
- **Suicide, self-harm, sexual exploitation, severe profanity**: –25 (maximum)
- **All other themes**: –20 (maximum)
- **Total penalty cap**: –55

### **Escalators**
- **Frequency multipliers** for repeated themes
- **Context escalators** for particularly egregious content

## ▲ v3.1 Update — Confidence Bands

### **Confidence Levels**
- **High**: ≥0.75
- **Medium**: 0.55–0.74
- **Low**: <0.55

### **Boundary Cases**
Songs within ±3 points of verdict thresholds flagged as **"Needs Review"**

## ▲ v3.1 Update — Doctrinal Clarity Check

**Applied to content marketed as "Christian"**:

### **Clarity Levels**
- **Sound**: Doctrinally accurate (no penalty)
- **Thin**: Lacks depth (–3 Purity)
- **Confused**: Doctrinal errors (–8 Purity, +1 Risk level)

## ▲ v3.1 Update — Spanish Profanity Coverage

### **Enhanced Language Support**
- **English profanity terms**: Comprehensive detection
- **Curated Spanish profanity terms**: Cultural context considerations
- **Profanity ladder applied** to both language sets

## ▲ v3.1 Update — Genre Fairness

### **Style Intensity Handling**
- **Musical genre characteristics** noted but not penalized
- **Heavy metal intensity** ≠ spiritual darkness
- **Aggressive vocals** ≠ sinful content
- **Genre conventions** respected in analysis

## ▲ v3.1 Update — Four-Tier Verdict System

| Verdict | Default Gate | Notes |
|---------|--------------|-------|
| **Freely Listen** | Purity ≥85 & Risk ≤Low | `thin` doctrinal clarity allowed; `confused` → downgrade |
| **Context Required** | 60–84 or Risk=High | Biblical lament maintains this tier minimum |
| **Caution — Limit Exposure** | 40–59 or Risk High/Critical | Severe profanity/sexual exploitation remains here |
| **Avoid for Formation** | Purity <40 or Blasphemy | Low-confidence near 40 → review |

## ▲ v3.1 Update — Enhanced Data Model

```json
{
  "narrative_voice": "artist|character|ambiguous",
  "lament_filter_applied": true,
  "doctrinal_clarity": "sound|thin|confused",
  "purity_score": 0-100,
  "formation_risk": "very_low|low|high|critical",
  "confidence_overall": "high|medium|low",
  "needs_review": true,
  "verdict_tier": "freely_listen|context_required|caution_limit|avoid_formation"
}
```

## ▲ v3.1 Update — Enhanced Examples

### **Updated Example: "Shadows" – Wolves At The Gate**

#### **v3.1 Analysis**
- **Narrative Voice**: Artist
- **Lament Filter**: Not applied
- **Doctrinal Clarity**: Sound
- **Confidence**: High (0.92)

#### **Final Scores**
- **Purity Score**: 100 (Capped)
- **Formation Risk**: Very Low

#### **Verdict**: **Freely Listen**

### **Updated Example: "Doomsday" – Architects**

#### **v3.1 Analysis**
- **Narrative Voice**: Artist
- **Lament Filter**: Not applied (lacks address to God)
- **Doctrinal Clarity**: N/A (secular content)
- **Confidence**: High (0.88)

#### **Final Scores**
- **Purity Score**: 35
- **Formation Risk**: Critical

#### **Verdict**: **Avoid for Formation**

### **Updated Example: "I Believe" – Killswitch Engage**

#### **v3.1 Analysis**
- **Narrative Voice**: Artist
- **Lament Filter**: Not applied
- **Doctrinal Clarity**: Thin (marketed as spiritual content)
- **Confidence**: Medium (0.67)

#### **Final Scores**
- **Purity Score**: 83 (86 - 3 for thin doctrine)
- **Formation Risk**: Low

#### **Verdict**: **Context Required**

## 🧪 Evaluation Schema (v3.1)

Use this schema to validate model outputs consistently:

- **Verdict** (tier): freely_listen | context_required | caution_limit | avoid_formation
- **Score** (0–100): purity score, with caps and multipliers applied
- **Concern Flags**: set of categories with severities (low|medium|high|critical)
- **Scripture Support**: passage references that align with detected themes
- **Formation Risk**: very_low | low | high | critical
- **Doctrinal Clarity**: sound | thin | confused | null
- **Narrative Voice**: artist | character | ambiguous
- **Lament Filter**: applied/not applied (criteria met)

Evaluation Metrics:

- Verdict accuracy (macro‑F1)
- Score correlation (Pearson/Spearman) and MAE
- Concern flag precision/recall/F1 (micro and macro)
- Scripture overlap (Jaccard over references)
- Latency p50/p90/p99 per 100‑song batch

Reviewer Notes:
- Use BSB for verse text when quoting in feedback
- Apply framework caps and escalators; document boundary cases near thresholds
- Flag “Needs Review” when outputs fall within ±3 points of verdict thresholds
