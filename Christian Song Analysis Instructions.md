# Cursor AI Instructions: Improve Christian Song Analysis

## Problem with Current System
The current keyword-based approach in `huggingface_analyzer.py` is inaccurate because:
- It only looks for specific words like "Jesus" or "God" without understanding context
- A song can mention religious terms but promote false theology
- It misses subtle negative themes that don't use explicit language
- The scoring system (100% minus deductions) assumes all content is good by default

## Simple Solution: Better HuggingFace Models + Improved Logic

### 1. Replace Current Models with These Specific HuggingFace Models

**For Theological Content Analysis:**
```python
# Replace the current sentiment models with:
theological_classifier = pipeline("text-classification",
    model="microsoft/DialoGPT-medium")  # Better for understanding religious context

# For detecting harmful content (beyond just profanity):
toxicity_detector = pipeline("text-classification",
    model="unitary/toxic-bert")

# For understanding themes and concepts:
theme_analyzer = pipeline("zero-shot-classification",
    model="facebook/bart-large-mnli")
```

### 2. Update the Analysis Logic in `huggingface_analyzer.py`

**Current Problem:** Looking for keywords like "jesus", "god", "faith"
**Better Approach:** Use theme classification with specific Christian categories

```python
def analyze_christian_themes(self, lyrics):
    # Define specific Christian themes to look for
    christian_themes = [
        "worship and praise of God",
        "salvation through Jesus Christ",
        "biblical love and relationships",
        "spiritual growth and discipleship",
        "biblical hope and comfort",
        "gratitude and thanksgiving"
    ]

    # Define concerning themes
    concerning_themes = [
        "materialism and greed",
        "sexual immorality",
        "violence and aggression",
        "substance abuse",
        "occult or false spirituality",
        "pride and self-worship"
    ]

    # Use zero-shot classification instead of keyword matching
    positive_results = self.theme_analyzer(lyrics, christian_themes)
    negative_results = self.theme_analyzer(lyrics, concerning_themes)

    return positive_results, negative_results
```

### 3. Fix the Scoring System

**Current Problem:** Starts at 100% and subtracts points
**Better Approach:** Start at 0 and earn points for positive content

```python
def calculate_score(self, positive_themes, negative_themes, toxicity_score):
    score = 0

    # Earn points for positive Christian themes (max 70 points)
    for theme in positive_themes:
        if theme['score'] > 0.7:  # High confidence
            score += 15
        elif theme['score'] > 0.5:  # Medium confidence
            score += 8

    # Lose points for concerning themes
    for theme in negative_themes:
        if theme['score'] > 0.7:
            score -= 20
        elif theme['score'] > 0.5:
            score -= 10

    # Factor in toxicity
    if toxicity_score > 0.8:
        score -= 30
    elif toxicity_score > 0.5:
        score -= 15

    # Keep score between 0-100
    return max(0, min(100, score))
```

### 4. Improve Biblical References

**Current Problem:** Generic bible verses
**Better Approach:** Match verses to detected themes

```python
# Create a simple mapping of themes to relevant Bible verses
THEME_VERSES = {
    "worship and praise": [
        {"reference": "Psalm 95:1", "text": "Come, let us sing for joy to the Lord..."},
        {"reference": "Philippians 4:8", "text": "Whatever is true, whatever is noble..."}
    ],
    "materialism": [
        {"reference": "Matthew 6:24", "text": "No one can serve two masters..."},
        {"reference": "1 Timothy 6:10", "text": "For the love of money is a root of all kinds of evil..."}
    ],
    # Add more mappings...
}

def get_relevant_verses(self, detected_themes):
    relevant_verses = []
    for theme in detected_themes:
        if theme['label'] in THEME_VERSES:
            relevant_verses.extend(THEME_VERSES[theme['label']])
    return relevant_verses[:3]  # Return top 3 most relevant
```

### 5. Update the Database Models (Simple Addition)

Add these fields to your existing `Analysis` model:

```python
# Add to your existing models.py
class Analysis(Base):
    # ... existing fields ...

    # Add these new fields:
    detected_themes = Column(JSON)  # Store the themes found
    biblical_references = Column(JSON)  # Store relevant verses
    confidence_score = Column(Float)  # How confident the AI is
```

## What to Tell Cursor AI

"Update the `huggingface_analyzer.py` file to:

1. Replace the current keyword-based Christian theme detection with HuggingFace zero-shot classification using the model `facebook/bart-large-mnli`

2. Change the scoring system from starting at 100% and subtracting points to starting at 0% and earning points for positive Christian themes

3. Add toxicity detection using the `unitary/toxic-bert` model to catch harmful content beyond just profanity

4. Create a simple mapping system that matches detected themes to relevant Bible verses instead of using generic verses

5. Update the database to store detected themes, biblical references, and confidence scores

6. Keep the existing UI but show the detected themes and more relevant Bible verses

The goal is more accurate analysis that understands context and theology, not just keywords."

## Expected Results

- **More Accurate:** Will catch songs that mention God but promote false teaching
- **Better Context:** Will understand when negative words are used appropriately (like in songs about overcoming struggles)
- **Relevant Verses:** Bible references will actually relate to the song content
- **Honest Scoring:** Songs have to earn good scores by having positive content, not just avoiding bad words

## Simple Test Cases

After implementation, test with these examples:

1. **False Positive Fix:** A song that mentions "Jesus" but promotes prosperity gospel should score low
2. **False Negative Fix:** A song about overcoming depression through faith should score high even if it mentions sadness
3. **Context Understanding:** A worship song that uses metaphorical language should be recognized as Christian content

This approach uses proven HuggingFace models with simple logic improvements rather than building complex custom systems.
