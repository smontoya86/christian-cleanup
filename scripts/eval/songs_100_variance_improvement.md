# 100-Song Variance Improvement List

**Purpose:** Fill gaps in score distribution (50-79 range) to improve dataset variance
**Target:** Achieve std dev >29 for better model training
**Distribution:** 34 songs (50-59) | 36 songs (60-69) | 30 songs (70-79)

---

## SCORE 50-59 RANGE (34 songs)
### Borderline - Upper Caution/Lower Context Required

**Secular Pop - Mild Positive Messages (12 songs)**
- "Hall of Fame" - The Script ft. will.i.am
- "Glorious" - Macklemore ft. Skylar Grey
- "Best Day of My Life" - American Authors
- "On Top of the World" - Imagine Dragons
- "Some Nights" - fun.
- "We Are Young" - fun. ft. Janelle Monáe
- "Carry On" - fun.
- "Dog Days Are Over" - Florence + The Machine
- "Shake It Out" - Florence + The Machine
- "Human" - The Killers
- "Mr. Brightside" - The Killers (cautionary tale)
- "All These Things That I've Done" - The Killers

**Indie/Alternative - Reflective (10 songs)**
- "Rivers and Roads" - The Head and the Heart
- "Lost in My Mind" - The Head and the Heart
- "Let Her Go" - Passenger
- "Heart of Gold" - Neil Young
- "The Cave" - Mumford & Sons (already in dataset, if not add similar)
- "Timshel" - Mumford & Sons
- "After the Storm" - Mumford & Sons
- "Broken Crown" - Mumford & Sons
- "Holland Road" - Mumford & Sons
- "Ghosts That We Knew" - Mumford & Sons

**Country - Positive Values (6 songs)**
- "My Front Porch Looking In" - Lonestar
- "I'm Already There" - Lonestar
- "Amarillo by Morning" - George Strait
- "I Cross My Heart" - George Strait
- "Remember When" - Alan Jackson
- "Small Town Southern Man" - Alan Jackson

**Singer-Songwriter - Storytelling (6 songs)**
- "Fast Car" - Tracy Chapman
- "Talkin' Bout a Revolution" - Tracy Chapman
- "Landslide" - Fleetwood Mac (if not already included)
- "The Story" - Brandi Carlile
- "The Joke" - Brandi Carlile
- "By The Way, I Forgive You" - Brandi Carlile

---

## SCORE 60-69 RANGE (36 songs)
### Acceptable - Context Required (Common Grace, Secular Good)

**Classic Soul/R&B - Inspirational (10 songs)**
- "Lean On Me" - Bill Withers (if not already included, verify)
- "Use Me" - Bill Withers
- "Ain't No Sunshine" - Bill Withers
- "Just the Two of Us" - Bill Withers
- "Soul Man" - Sam & Dave
- "Hold On, I'm Comin'" - Sam & Dave
- "When a Man Loves a Woman" - Percy Sledge
- "Try a Little Tenderness" - Otis Redding
- "These Arms of Mine" - Otis Redding
- "I've Been Loving You Too Long" - Otis Redding

**Folk/Americana - Community & Justice (10 songs)**
- "This Land Is Your Land" - Woody Guthrie
- "Blowin' in the Wind" - Bob Dylan
- "The Times They Are a-Changin'" - Bob Dylan
- "If I Had a Hammer" - Peter, Paul and Mary
- "Puff the Magic Dragon" - Peter, Paul and Mary
- "Where Have All the Flowers Gone" - Pete Seeger
- "Turn! Turn! Turn!" - The Byrds (Ecclesiastes 3)
- "We Shall Overcome" - Joan Baez
- "Amazing Grace" - Judy Collins (secular recording)
- "Both Sides Now" - Joni Mitchell

**Singer-Songwriter - Depth & Meaning (8 songs)**
- "Hallelujah" - Jeff Buckley (if not in dataset - vague spiritual but beautiful)
- "Grace" - Jeff Buckley
- "Lover, You Should've Come Over" - Jeff Buckley
- "Fire and Rain" - James Taylor
- "Carolina in My Mind" - James Taylor
- "Sweet Baby James" - James Taylor
- "The Boxer" - Simon & Garfunkel
- "Bridge Over Troubled Water" - Simon & Garfunkel (if not included)

**Modern Indie - Positive Outlook (8 songs)**
- "Home" - Phillip Phillips
- "Gone, Gone, Gone" - Phillip Phillips
- "Rude" - MAGIC!
- "I Lived" - OneRepublic
- "Love Runs Out" - OneRepublic
- "If I Lose Myself" - OneRepublic
- "Wherever You Will Go" - The Calling
- "Our Lives" - The Calling

---

## SCORE 70-79 RANGE (30 songs)
### Good - Upper Context Required / Lower Freely Listen

**Christian Crossover/Mainstream (10 songs)**
- "I Can Only Imagine" - MercyMe (mainstream version)
- "Oceans" - Hillsong UNITED (if not already multiple times)
- "Reckless Love" - Cory Asbury (if not included)
- "What a Beautiful Name" - Hillsong Worship (verify not duplicate)
- "Good Good Father" - Chris Tomlin
- "This Is Amazing Grace" - Phil Wickham
- "Living Hope" - Phil Wickham (verify not duplicate)
- "Raise a Hallelujah" - Bethel Music
- "You Say" - Lauren Daigle
- "Rescue" - Lauren Daigle (verify not duplicate)

**Positive Country - Faith/Family (8 songs)**
- "God Gave Me You" - Blake Shelton
- "Blessed" - Martina McBride
- "In My Daughter's Eyes" - Martina McBride
- "There Goes My Life" - Kenny Chesney
- "The Good Stuff" - Kenny Chesney
- "Who You'd Be Today" - Kenny Chesney
- "Three Wooden Crosses" - Randy Travis
- "Forever and Ever, Amen" - Randy Travis

**Gospel-Influenced Secular (6 songs)**
- "Oh Happy Day" - Edwin Hawkins Singers (if not included)
- "Lean on Me" - Club Nouveau (gospel version)
- "People Get Ready" - The Impressions (verify not duplicate)
- "Amen" - The Impressions
- "Keep On Pushing" - The Impressions
- "This Is My Country" - The Impressions

**Inspirational Pop - Strong Positive Messages (6 songs)**
- "Unwritten" - Natasha Bedingfield (if not included)
- "Pocketful of Sunshine" - Natasha Bedingfield
- "These Words" - Natasha Bedingfield
- "Beautiful" - Christina Aguilera (body positivity - if not included)
- "The Voice Within" - Christina Aguilera
- "Stronger (What Doesn't Kill You)" - Kelly Clarkson (verify not duplicate)

---

## Summary by Target Score

| Score Range | Songs | Primary Content Type |
|-------------|-------|---------------------|
| **50-59** | 34 | Borderline positive, mild redeeming values |
| **60-69** | 36 | Common grace, secular good, community values |
| **70-79** | 30 | Christian crossover, strong positive messages |
| **TOTAL** | **100** | Targeted variance improvement |

---

## Expected Impact

**Current Stats:**
- Total Songs: 1,081
- Mean Score: 50.8
- Std Dev: 26.5
- Variance Score: 67.4% (POOR)

**After Adding 100 Songs:**
- Total Songs: 1,181
- Expected Mean: 52-53 (slightly higher due to mid-range boost)
- Expected Std Dev: ~29-30
- Expected Variance Score: ~85-90% (GOOD)

**Distribution Improvement:**
- 50-59 range: 20 → 54 songs (170% increase)
- 60-69 range: 72 → 108 songs (50% increase)
- 70-79 range: 25 → 55 songs (120% increase)

---

## Notes

**Duplicates:** Some songs listed may already be in the dataset. The script will skip existing songs automatically via `--skip-existing` flag.

**Genre Balance:** This list maintains genre diversity while filling score gaps:
- Secular pop/indie with positive messages
- Classic soul/R&B with community values
- Folk/Americana with justice themes
- Christian crossover for upper range
- Positive country for family values

**Theological Positioning:**
- 50-59: Songs with some redeeming value but lacking clear Christian foundation
- 60-69: Common grace examples (reflecting God's moral law without explicit faith)
- 70-79: Christian crossover or strong moral/inspirational content

---

**Next Steps:**
1. Convert to JSONL format
2. Label with GPT-4o-mini (concurrency=5)
3. Merge with existing 1,081-song dataset
4. Final dataset: 1,181 songs with improved variance

