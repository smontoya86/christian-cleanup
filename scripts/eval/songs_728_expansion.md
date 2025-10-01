# 728-Song Dataset Expansion (272 → 1,000 Total)

**Purpose:** Expand baseline dataset from 272 to 1,000 songs for production fine-tuning
**Target Distribution:** Balanced across all verdict categories with diverse edge cases
**Estimated Labeling Cost:** $2.00-2.50 (GPT-4o-mini @ concurrency=5)
**Estimated Time:** 35-40 minutes

---

## Verdict Distribution Target (728 songs)

Based on current 272-song distribution, target for expansion:

| Verdict | Current (272) | Target for 728 | Total (1,000) | % of Total |
|---------|---------------|----------------|---------------|------------|
| **freely_listen** | 74 (27.2%) | 196 | 270 | 27% |
| **context_required** | 32 (11.8%) | 86 | 118 | 12% |
| **caution_limit** | 51 (18.8%) | 137 | 188 | 19% |
| **avoid_formation** | 115 (42.3%) | 309 | 424 | 42% |

---

## FREELY_LISTEN (~196 songs)

### Contemporary Christian Worship (60 songs)
- "Reckless Love" - Cory Asbury
- "Goodness of God" - Bethel Music
- "Way Maker" - Sinach
- "Living Hope" - Phil Wickham
- "The Blessing" - Kari Jobe
- "Great Are You Lord" - All Sons & Daughters
- "Build My Life" - Pat Barrett
- "Graves Into Gardens" - Elevation Worship
- "King of Kings" - Hillsong Worship
- "Yes I Will" - Vertical Worship
- "Build Your Kingdom Here" - Rend Collective
- "Resurrecting" - Elevation Worship
- "O Come to the Altar" - Elevation Worship
- "Christ Is Risen" - Matt Maher
- "Do It Again" - Elevation Worship
- "Here Again" - Elevation Worship
- "Tremble" - Mosaic MSC
- "The Lion and the Lamb" - Big Daddy Weave
- "Surrounded (Fight My Battles)" - Upper Room
- "There Was Jesus" - Zach Williams ft. Dolly Parton
- "Known" - Tauren Wells
- "Run to the Father" - Cody Carnes
- "Million Little Miracles" - Elevation Worship
- "Jireh" - Elevation Worship & Maverick City
- "Man of Your Word" - Maverick City & Chandler Moore
- "Promises" - Maverick City Music
- "Breathe" - Maverick City Music
- "Wait on You" - Elevation Worship & Maverick City
- "Firm Foundation" - Maverick City & Cody Carnes
- "Blessings" - Elevation Worship
- "See A Victory" - Elevation Worship
- "The Proof of Your Love" - For King & Country
- "God of All My Days" - Casting Crowns
- "Glorious Day" - Passion
- "Come As You Are" - Crowder
- "My Victory" - Crowder
- "Red Letters" - Crowder
- "All My Hope" - Crowder
- "I Am" - Crowder
- "Forgiven" - Crowder
- "Lift Your Head Weary Sinner" - Crowder
- "Come Alive" - Lauren Daigle
- "Rescue" - Lauren Daigle
- "Still Rolling Stones" - Lauren Daigle
- "Everything" - Lauren Daigle
- "Power to Redeem" - Lauren Daigle
- "Rebel Heart" - Lauren Daigle
- "Salt & Light" - Lauren Daigle
- "First" - Lauren Daigle
- "Loyal" - Lauren Daigle
- "New" - Lauren Daigle
- "Trust in You" - Lauren Daigle
- "Love Like This" - Lauren Daigle
- "Inevitable" - Anberlin
- "Chain Breaker" - Zach Williams
- "Fear Is a Liar" - Zach Williams
- "Survivor" - Zach Williams
- "Old Church Choir" - Zach Williams
- "Less Like Me" - Zach Williams
- "To the Table" - Zach Williams
- "Rescue Story" - Zach Williams

### Classic Hymns & Traditional Worship (40 songs)
- "Amazing Grace (My Chains Are Gone)" - Chris Tomlin
- "Holy Holy Holy" - Reginald Heber
- "It Is Well" - Kristene DiMarco
- "Nothing But The Blood" - Matt Redman
- "Come Thou Fount" - David Crowder Band
- "Be Thou My Vision" - Audrey Assad
- "Blessed Assurance" - Traditional
- "Great Is Thy Faithfulness" - Thomas Chisholm
- "A Mighty Fortress Is Our God" - Martin Luther
- "All Creatures of Our God and King" - St. Francis of Assisi
- "Crown Him with Many Crowns" - Matthew Bridges
- "Fairest Lord Jesus" - Traditional
- "For the Beauty of the Earth" - Folliott Pierpoint
- "I Surrender All" - Judson Van DeVenter
- "Jesus Paid It All" - Elvina Hall
- "O For a Thousand Tongues" - Charles Wesley
- "Praise to the Lord the Almighty" - Joachim Neander
- "The Old Rugged Cross" - George Bennard
- "What a Friend We Have in Jesus" - Joseph Scriven
- "When I Survey the Wondrous Cross" - Isaac Watts
- "All Hail the Power of Jesus' Name" - Edward Perronet
- "And Can It Be" - Charles Wesley
- "Christ the Lord Is Risen Today" - Charles Wesley
- "Holy, Holy, Holy" - Reginald Heber
- "Immortal, Invisible, God Only Wise" - Walter Smith
- "Joyful, Joyful We Adore Thee" - Henry Van Dyke
- "Love Divine, All Loves Excelling" - Charles Wesley
- "O God Our Help in Ages Past" - Isaac Watts
- "O Worship the King" - Robert Grant
- "Praise My Soul the King of Heaven" - Henry Lyte
- "Praise to the Lord" - Joachim Neander
- "Rejoice, the Lord Is King" - Charles Wesley
- "The Church's One Foundation" - Samuel Stone
- "To God Be the Glory" - Fanny Crosby
- "We Gather Together" - Traditional
- "Abide with Me" - Henry Lyte
- "All Glory Laud and Honor" - Theodulph of Orleans
- "Beautiful Savior" - Münster Gesangbuch
- "Christ Arose" - Robert Lowry
- "In Christ Alone" - Keith Getty & Stuart Townend

### Gospel & Black Gospel (30 songs)
- "Oh Happy Day" - Edwin Hawkins Singers
- "His Eye Is on the Sparrow" - Civilla Martin
- "Take Me to the King" - Tamela Mann
- "I Can Only Imagine" - Tamela Mann
- "God Provides" - Tamela Mann
- "This Place" - Tamela Mann
- "He Did It" - Tye Tribbett
- "If He Did It Before" - Tye Tribbett
- "Victory" - Tye Tribbett
- "Same God" - Tye Tribbett
- "Everything" - Tye Tribbett
- "No Way" - Tye Tribbett
- "Most High" - Tye Tribbett
- "Champion" - Tye Tribbett
- "Gonna Be Alright" - Tye Tribbett
- "Work It Out" - Tye Tribbett
- "Great Is Your Mercy" - Donnie McClurkin
- "We Fall Down" - Donnie McClurkin
- "Stand" - Donnie McClurkin
- "Speak to My Heart" - Donnie McClurkin
- "Holy" - Donnie McClurkin
- "I Call You Faithful" - Donnie McClurkin
- "Awesome" - Pastor Charles Jenkins
- "War" - Charles Jenkins
- "Best Friend" - Kirk Franklin
- "I Smile" - Kirk Franklin
- "Wanna Be Happy?" - Kirk Franklin
- "Love Theory" - Kirk Franklin
- "My World Needs You" - Kirk Franklin
- "123 Victory" - Kirk Franklin

### Christian Contemporary/Pop (30 songs)
- "Oceans (Where Feet May Fail)" - Hillsong UNITED
- "What A Beautiful Name" - Hillsong Worship
- "So Will I" - Hillsong UNITED
- "Who You Say I Am" - Hillsong Worship
- "Whole Heart" - Hillsong UNITED
- "Another In The Fire" - Hillsong UNITED
- "Highlands" - Hillsong UNITED
- "Touch The Sky" - Hillsong UNITED
- "Oceans" - Hillsong UNITED
- "Captain" - Hillsong UNITED
- "Good Grace" - Hillsong UNITED
- "Even When It Hurts" - Hillsong UNITED
- "Empires" - Hillsong UNITED
- "Prince of Peace" - Hillsong UNITED
- "Run To You" - Hillsong UNITED
- "Awake My Soul" - Hillsong UNITED
- "Lead Me To The Cross" - Hillsong UNITED
- "Relentless" - Hillsong UNITED
- "Bones" - Hillsong UNITED
- "Forever Reign" - Hillsong Worship
- "This I Believe" - Hillsong Worship
- "Cornerstone" - Hillsong Worship
- "Hosanna" - Hillsong UNITED
- "Mighty to Save" - Hillsong UNITED
- "All I Need Is You" - Hillsong UNITED
- "From The Inside Out" - Hillsong UNITED
- "With Everything" - Hillsong UNITED
- "Aftermath" - Hillsong UNITED
- "The Stand" - Hillsong UNITED
- "Scandal of Grace" - Hillsong UNITED

### Christian Rock/Alternative (36 songs)
- "Word of God Speak" - MercyMe
- "Flawless" - MercyMe
- "Greater" - MercyMe
- "Shake" - MercyMe
- "Dear Younger Me" - MercyMe
- "Even If" - MercyMe
- "Best News Ever" - MercyMe
- "Grace Got You" - MercyMe
- "Say I Won't" - MercyMe
- "Inhale (Exhale)" - MercyMe
- "Multiply" - Needtobreathe
- "Something Beautiful" - Needtobreathe
- "Brother" - Needtobreathe
- "Testify" - Needtobreathe
- "Difference Maker" - Needtobreathe
- "Hard Love" - Needtobreathe
- "Wasteland" - Needtobreathe
- "Happiness" - Needtobreathe
- "I Wanna Remember" - Needtobreathe
- "Seasons" - Needtobreathe
- "Into the Mystery" - Needtobreathe
- "Who Am I" - Casting Crowns
- "Praise You In This Storm" - Casting Crowns
- "East to West" - Casting Crowns
- "Slow Fade" - Casting Crowns
- "If We Are the Body" - Casting Crowns
- "Courageous" - Casting Crowns
- "Thrive" - Casting Crowns
- "Just Be Held" - Casting Crowns
- "Oh My Soul" - Casting Crowns
- "Only Jesus" - Casting Crowns
- "Nobody" - Casting Crowns
- "Scars in Heaven" - Casting Crowns
- "Start Right Here" - Casting Crowns
- "Healer" - Casting Crowns
- "Until The Whole World Hears" - Casting Crowns

---

## CONTEXT_REQUIRED (~86 songs)

### Secular Inspirational - Common Grace (30 songs)
- "Lean On Me" - Bill Withers
- "Stand By Me" - Ben E. King
- "What a Wonderful World" - Louis Armstrong
- "You've Got a Friend" - James Taylor
- "Count On Me" - Bruno Mars
- "Unwritten" - Natasha Bedingfield
- "Fight Song" - Rachel Platten
- "Brave" - Sara Bareilles
- "Roar" - Katy Perry (instrumental themes)
- "Firework" - Katy Perry (self-worth themes)
- "Hero" - Mariah Carey
- "The Greatest" - Sia
- "Unstoppable" - Sia
- "Try Everything" - Shakira
- "Hall of Fame" - The Script
- "Don't Stop Believin'" - Journey
- "Eye of the Tiger" - Survivor
- "We Are the Champions" - Queen
- "I Will Survive" - Gloria Gaynor
- "Respect" - Aretha Franklin
- "A Change Is Gonna Come" - Sam Cooke
- "People Get Ready" - The Impressions
- "What's Going On" - Marvin Gaye
- "Lean On" - Major Lazer
- "Home" - Phillip Phillips
- "Not Afraid" - Eminem (resilience themes)
- "Lose Yourself" - Eminem (determination)
- "Till I Collapse" - Eminem (perseverance)
- "Stronger" - Kanye West (resilience)
- "Good Life" - Kanye West (gratitude themes)

### Vague Spiritual - Unclear Theology (30 songs)
- "Spirit in the Sky" - Norman Greenbaum
- "Let It Be" - The Beatles
- "My Sweet Lord" - George Harrison
- "Jesus Walks" - Kanye West
- "Ultralight Beam" - Kanye West
- "Jesus Is the One" - Zach Williams (if vague)
- "Blessings" - Chance the Rapper
- "How Great" - Chance the Rapper
- "Waves" - Kanye West
- "Father Stretch My Hands" - Kanye West
- "Only One" - Kanye West
- "Believer" - Imagine Dragons
- "Radioactive" - Imagine Dragons
- "It's Time" - Imagine Dragons
- "Thunder" - Imagine Dragons
- "Whatever It Takes" - Imagine Dragons
- "On Top of the World" - Imagine Dragons
- "Next to Me" - Imagine Dragons
- "Natural" - Imagine Dragons
- "Bad Liar" - Imagine Dragons
- "Higher Power" - Coldplay
- "A Sky Full of Stars" - Coldplay
- "Adventure of a Lifetime" - Coldplay
- "Up&Up" - Coldplay
- "Amazing" - Coldplay
- "Paradise" - Coldplay
- "Every Teardrop Is a Waterfall" - Coldplay
- "Hymn for the Weekend" - Coldplay
- "Something Just Like This" - Chainsmokers & Coldplay
- "Church" - T-Pain

### U2 - Mixed Spiritual Content (16 songs)
- "Desire" - U2
- "The Wanderer" - U2
- "Mysterious Ways" - U2
- "One" - U2
- "Stay (Faraway, So Close!)" - U2
- "Wake Up Dead Man" - U2
- "Grace" - U2
- "Peace on Earth" - U2
- "Walk On" - U2
- "Kite" - U2
- "Stuck in a Moment" - U2
- "Elevation" - U2
- "Vertigo" - U2
- "City of Blinding Lights" - U2
- "Original of the Species" - U2
- "Magnificent" - U2

### Moral Reflection - Secular (10 songs)
- "The Man in the Mirror" - Michael Jackson
- "Heal the World" - Michael Jackson
- "We Are the World" - USA for Africa
- "Imagine" - John Lennon (humanistic)
- "Give Peace a Chance" - John Lennon
- "Redemption Song" - Bob Marley
- "Three Little Birds" - Bob Marley
- "One Love" - Bob Marley
- "Get Up Stand Up" - Bob Marley
- "Waiting on the World to Change" - John Mayer

---

## CAUTION_LIMIT (~137 songs)

### Romance/Relationship - Borderline Idolatry (40 songs)
- "All of Me" - John Legend
- "Thinking Out Loud" - Ed Sheeran
- "Perfect" - Ed Sheeran
- "Shape of You" - Ed Sheeran
- "Photograph" - Ed Sheeran
- "Happier" - Ed Sheeran
- "Castle on the Hill" - Ed Sheeran
- "Hearts Don't Break Around Here" - Ed Sheeran
- "Kiss Me" - Ed Sheeran
- "Drunk" - Ed Sheeran
- "Make You Feel My Love" - Adele
- "Someone Like You" - Adele
- "Hello" - Adele
- "When We Were Young" - Adele
- "Set Fire to the Rain" - Adele
- "Rolling in the Deep" - Adele
- "Rumour Has It" - Adele
- "Turning Tables" - Adele
- "Love Song" - Adele
- "Skyfall" - Adele
- "Say You Love Me" - Fleetwood Mac
- "Dreams" - Fleetwood Mac
- "Landslide" - Fleetwood Mac
- "The Chain" - Fleetwood Mac
- "Go Your Own Way" - Fleetwood Mac
- "Everywhere" - Fleetwood Mac
- "Little Lies" - Fleetwood Mac
- "Sara" - Fleetwood Mac
- "Rhiannon" - Fleetwood Mac
- "You Make My Dreams" - Hall & Oates
- "Can't Help Falling in Love" - Elvis Presley
- "Unchained Melody" - Righteous Brothers
- "At Last" - Etta James
- "Endless Love" - Diana Ross & Lionel Richie
- "I Will Always Love You" - Whitney Houston
- "My Heart Will Go On" - Celine Dion
- "Because You Loved Me" - Celine Dion
- "The Power of Love" - Celine Dion
- "A Thousand Years" - Christina Perri
- "Say Something" - A Great Big World

### Pop - Mild Concerns (30 songs)
- "Shake It Off" - Taylor Swift
- "Blank Space" - Taylor Swift
- "Style" - Taylor Swift
- "Wildest Dreams" - Taylor Swift
- "Bad Blood" - Taylor Swift
- "We Are Never Getting Back Together" - Taylor Swift
- "I Knew You Were Trouble" - Taylor Swift
- "22" - Taylor Swift
- "Mean" - Taylor Swift
- "Love Story" - Taylor Swift
- "You Belong With Me" - Taylor Swift
- "Mine" - Taylor Swift
- "Back to December" - Taylor Swift
- "Sparks Fly" - Taylor Swift
- "Ours" - Taylor Swift
- "Just the Way You Are" - Bruno Mars
- "Grenade" - Bruno Mars
- "The Lazy Song" - Bruno Mars
- "Locked Out of Heaven" - Bruno Mars
- "When I Was Your Man" - Bruno Mars
- "Treasure" - Bruno Mars
- "Uptown Funk" - Bruno Mars
- "24K Magic" - Bruno Mars
- "That's What I Like" - Bruno Mars
- "Finesse" - Bruno Mars
- "Versace on the Floor" - Bruno Mars
- "Marry You" - Bruno Mars
- "Just Give Me a Reason" - P!nk
- "Try" - P!nk
- "What About Us" - P!nk

### Self-Empowerment - Humanistic (30 songs)
- "Stronger (What Doesn't Kill You)" - Kelly Clarkson
- "Since U Been Gone" - Kelly Clarkson
- "Because of You" - Kelly Clarkson
- "Behind These Hazel Eyes" - Kelly Clarkson
- "My Life Would Suck Without You" - Kelly Clarkson
- "Breakaway" - Kelly Clarkson
- "Beautiful" - Christina Aguilera
- "Fighter" - Christina Aguilera
- "Ain't No Other Man" - Christina Aguilera
- "Hurt" - Christina Aguilera
- "Say" - Christina Aguilera
- "Reflection" - Christina Aguilera
- "Born This Way" - Lady Gaga
- "Just Dance" - Lady Gaga
- "Poker Face" - Lady Gaga
- "Bad Romance" - Lady Gaga
- "Alejandro" - Lady Gaga
- "Edge of Glory" - Lady Gaga
- "Million Reasons" - Lady Gaga
- "Shallow" - Lady Gaga
- "You and I" - Lady Gaga
- "Titanium" - David Guetta ft. Sia
- "Chandelier" - Sia
- "Elastic Heart" - Sia
- "Alive" - Sia
- "Bird Set Free" - Sia
- "Cheap Thrills" - Sia
- "Rainbow" - Kacey Musgraves
- "Follow Your Arrow" - Kacey Musgraves
- "High Horse" - Kacey Musgraves

### Alternative/Indie - Mixed Themes (37 songs)
- "Radioactive" - Imagine Dragons
- "Demons" - Imagine Dragons
- "It's Time" - Imagine Dragons
- "On Top of the World" - Imagine Dragons
- "Bleeding Out" - Imagine Dragons
- "Amsterdam" - Imagine Dragons
- "Hear Me" - Imagine Dragons
- "Nothing Left to Say" - Imagine Dragons
- "Riptide" - Vance Joy
- "Mess Is Mine" - Vance Joy
- "Georgia" - Vance Joy
- "Lay It On Me" - Vance Joy
- "Best That I Can" - Vance Joy
- "We're Going Home" - Vance Joy
- "Fire and the Flood" - Vance Joy
- "Somebody That I Used to Know" - Gotye
- "Pompeii" - Bastille
- "Things We Lost in the Fire" - Bastille
- "Flaws" - Bastille
- "Oblivion" - Bastille
- "Laura Palmer" - Bastille
- "Bad Blood" - Bastille
- "Weight of Living" - Bastille
- "Little Lion Man" - Mumford & Sons
- "I Will Wait" - Mumford & Sons
- "The Cave" - Mumford & Sons
- "Hopeless Wanderer" - Mumford & Sons
- "Babel" - Mumford & Sons
- "Lover of the Light" - Mumford & Sons
- "Whispers in the Dark" - Mumford & Sons
- "Believe" - Mumford & Sons
- "Awake My Soul" - Mumford & Sons
- "Sigh No More" - Mumford & Sons
- "Roll Away Your Stone" - Mumford & Sons
- "White Blank Page" - Mumford & Sons
- "Thistle & Weeds" - Mumford & Sons
- "After the Storm" - Mumford & Sons

---

## AVOID_FORMATION (~309 songs)

### Hip-Hop/Rap - Profanity/Content (80 songs)
- "HUMBLE." - Kendrick Lamar
- "DNA." - Kendrick Lamar
- "ELEMENT." - Kendrick Lamar
- "LOYALTY." - Kendrick Lamar
- "FEAR." - Kendrick Lamar
- "GOD." - Kendrick Lamar
- "LOVE." - Kendrick Lamar
- "XXX." - Kendrick Lamar
- "Swimming Pools" - Kendrick Lamar
- "Poetic Justice" - Kendrick Lamar
- "Money Trees" - Kendrick Lamar
- "Backseat Freestyle" - Kendrick Lamar
- "The Art of Peer Pressure" - Kendrick Lamar
- "Alright" - Kendrick Lamar
- "King Kunta" - Kendrick Lamar
- "The Blacker the Berry" - Kendrick Lamar
- "i" - Kendrick Lamar
- "These Walls" - Kendrick Lamar
- "u" - Kendrick Lamar
- "How Much a Dollar Cost" - Kendrick Lamar
- "Sicko Mode" - Travis Scott
- "Goosebumps" - Travis Scott
- "Antidote" - Travis Scott
- "Stargazing" - Travis Scott
- "Highest in the Room" - Travis Scott
- "Butterfly Effect" - Travis Scott
- "Pick Up the Phone" - Travis Scott
- "90210" - Travis Scott
- "3500" - Travis Scott
- "Mamacita" - Travis Scott
- "God's Plan" - Drake
- "In My Feelings" - Drake
- "Nice For What" - Drake
- "Nonstop" - Drake
- "Mob Ties" - Drake
- "Elevate" - Drake
- "Emotionless" - Drake
- "Can't Take a Joke" - Drake
- "8 Out of 10" - Drake
- "March 14" - Drake
- "Started From the Bottom" - Drake
- "Hold On We're Going Home" - Drake
- "Worst Behavior" - Drake
- "From Time" - Drake
- "Own It" - Drake
- "Wu-Tang Forever" - Drake
- "Pound Cake" - Drake
- "The Motto" - Drake
- "HYFR" - Drake
- "Crew Love" - Drake
- "Take Care" - Drake
- "Marvin's Room" - Drake
- "Hotline Bling" - Drake
- "One Dance" - Drake
- "Controlla" - Drake
- "Too Good" - Drake
- "Feel No Ways" - Drake
- "Hype" - Drake
- "Weston Road Flows" - Drake
- "Redemption" - Drake
- "Lose Yourself" - Eminem (character voice, but profanity)
- "Not Afraid" - Eminem
- "Love the Way You Lie" - Eminem
- "The Monster" - Eminem
- "Rap God" - Eminem
- "Berzerk" - Eminem
- "Survival" - Eminem
- "Legacy" - Eminem
- "Asshole" - Eminem
- "So Far" - Eminem
- "Kamikaze" - Eminem
- "The Ringer" - Eminem
- "Greatest" - Eminem
- "Lucky You" - Eminem
- "Fall" - Eminem
- "Venom" - Eminem
- "Good Guy" - Eminem
- "Nice Guy" - Eminem
- "Stepping Stone" - Eminem
- "Normal" - Eminem

### Pop - Sexual Content (50 songs)
- "Blurred Lines" - Robin Thicke
- "Get Lucky" - Daft Punk
- "We Can't Stop" - Miley Cyrus
- "Wrecking Ball" - Miley Cyrus
- "Bangerz" - Miley Cyrus
- "Adore You" - Miley Cyrus
- "SMS (Bangerz)" - Miley Cyrus
- "4x4" - Miley Cyrus
- "My Darlin'" - Miley Cyrus
- "Rooting for My Baby" - Miley Cyrus
- "Love Money Party" - Miley Cyrus
- "Get It Right" - Miley Cyrus
- "#GETITRIGHT" - Miley Cyrus
- "Drive" - Miley Cyrus
- "FU" - Miley Cyrus
- "Do My Thang" - Miley Cyrus
- "Maybe You're Right" - Miley Cyrus
- "Someone Else" - Miley Cyrus
- "Rooting for My Baby" - Miley Cyrus
- "On My Own" - Miley Cyrus
- "Hands of Love" - Miley Cyrus
- "Tainted Love" - Soft Cell
- "I Want Your Sex" - George Michael
- "Careless Whisper" - George Michael
- "Father Figure" - George Michael
- "Freedom! '90" - George Michael
- "Fastlove" - George Michael
- "Outside" - George Michael
- "Amazing" - George Michael
- "Freeek!" - George Michael
- "Pony" - Ginuwine
- "Ignition (Remix)" - R. Kelly
- "Bump N' Grind" - R. Kelly
- "Your Body's Callin'" - R. Kelly
- "12 Play" - R. Kelly
- "It Seems Like You're Ready" - R. Kelly
- "Sex Me" - R. Kelly
- "Slow Dance" - R. Kelly
- "Summer Bunnies" - R. Kelly
- "Freak Dat Body" - R. Kelly
- "I Like the Crotch on You" - R. Kelly
- "SexyBack" - Justin Timberlake
- "My Love" - Justin Timberlake
- "What Goes Around" - Justin Timberlake
- "LoveStoned" - Justin Timberlake
- "Suit & Tie" - Justin Timberlake
- "Mirrors" - Justin Timberlake
- "Pusher Love Girl" - Justin Timberlake
- "Don't Hold the Wall" - Justin Timberlake
- "Tunnel Vision" - Justin Timberlake

### Rock - Rebellion/Darkness (60 songs)
- "Smells Like Teen Spirit" - Nirvana
- "Come As You Are" - Nirvana
- "Lithium" - Nirvana
- "In Bloom" - Nirvana
- "Heart-Shaped Box" - Nirvana
- "All Apologies" - Nirvana
- "Rape Me" - Nirvana
- "Dumb" - Nirvana
- "Pennyroyal Tea" - Nirvana
- "About a Girl" - Nirvana
- "Enter Sandman" - Metallica
- "Master of Puppets" - Metallica
- "One" - Metallica
- "Nothing Else Matters" - Metallica
- "The Unforgiven" - Metallica
- "Fade to Black" - Metallica
- "For Whom the Bell Tolls" - Metallica
- "Creeping Death" - Metallica
- "Ride the Lightning" - Metallica
- "Welcome Home (Sanitarium)" - Metallica
- "Smooth Criminal" - Alien Ant Farm
- "Breaking the Habit" - Linkin Park
- "Numb" - Linkin Park
- "In the End" - Linkin Park
- "Crawling" - Linkin Park
- "One Step Closer" - Linkin Park
- "Faint" - Linkin Park
- "Papercut" - Linkin Park
- "Somewhere I Belong" - Linkin Park
- "Leave Out All the Rest" - Linkin Park
- "Shadow of the Day" - Linkin Park
- "What I've Done" - Linkin Park
- "Given Up" - Linkin Park
- "Bleed It Out" - Linkin Park
- "No More Sorrow" - Linkin Park
- "Waiting for the End" - Linkin Park
- "The Catalyst" - Linkin Park
- "Burning in the Skies" - Linkin Park
- "Iridescent" - Linkin Park
- "Boulevard of Broken Dreams" - Green Day
- "American Idiot" - Green Day
- "Holiday" - Green Day
- "Wake Me Up When September Ends" - Green Day
- "Jesus of Suburbia" - Green Day
- "Letterbomb" - Green Day
- "Whatsername" - Green Day
- "Basket Case" - Green Day
- "When I Come Around" - Green Day
- "Longview" - Green Day
- "Welcome to Paradise" - Green Day
- "She" - Green Day
- "Brain Stew" - Green Day
- "Jaded" - Green Day
- "Geek Stink Breath" - Green Day
- "Stuck with Me" - Green Day
- "Walking Contradiction" - Green Day
- "Warning" - Green Day
- "Minority" - Green Day
- "Waiting" - Green Day
- "Church on Sunday" - Green Day

### EDM/Party - Substance/Materialism (40 songs)
- "Animals" - Martin Garrix
- "Scared to Be Lonely" - Martin Garrix
- "In the Name of Love" - Martin Garrix
- "There for You" - Martin Garrix
- "Byte" - Martin Garrix
- "Now That I've Found You" - Martin Garrix
- "High on Life" - Martin Garrix
- "Summer Days" - Martin Garrix
- "These Are the Times" - Martin Garrix
- "Hold On & Believe" - Martin Garrix
- "Don't You Worry Child" - Swedish House Mafia
- "Save the World" - Swedish House Mafia
- "One" - Swedish House Mafia
- "Greyhound" - Swedish House Mafia
- "Antidote" - Swedish House Mafia
- "Miami 2 Ibiza" - Swedish House Mafia
- "Levels" - Avicii
- "Wake Me Up" - Avicii
- "Hey Brother" - Avicii
- "Addicted to You" - Avicii
- "The Days" - Avicii
- "The Nights" - Avicii
- "Waiting for Love" - Avicii
- "Without You" - Avicii
- "You Make Me" - Avicii
- "Lay Me Down" - Avicii
- "Titanium" - David Guetta
- "Where Them Girls At" - David Guetta
- "Turn Me On" - David Guetta
- "Without You" - David Guetta
- "She Wolf" - David Guetta
- "Play Hard" - David Guetta
- "Bad" - David Guetta
- "Dangerous" - David Guetta
- "Hey Mama" - David Guetta
- "Light My Body Up" - David Guetta
- "This One's for You" - David Guetta
- "2U" - David Guetta
- "Flames" - David Guetta
- "Don't Leave Me Alone" - David Guetta

### Metal - Occult/Darkness (30 songs)
- "Number of the Beast" - Iron Maiden
- "Run to the Hills" - Iron Maiden
- "The Trooper" - Iron Maiden
- "Hallowed Be Thy Name" - Iron Maiden
- "Fear of the Dark" - Iron Maiden
- "Aces High" - Iron Maiden
- "Wasted Years" - Iron Maiden
- "Powerslave" - Iron Maiden
- "Rime of the Ancient Mariner" - Iron Maiden
- "Children of the Damned" - Iron Maiden
- "War Pigs" - Black Sabbath
- "Paranoid" - Black Sabbath
- "Iron Man" - Black Sabbath
- "N.I.B." - Black Sabbath
- "Black Sabbath" - Black Sabbath
- "Sweet Leaf" - Black Sabbath
- "Children of the Grave" - Black Sabbath
- "Fairies Wear Boots" - Black Sabbath
- "Electric Funeral" - Black Sabbath
- "Hand of Doom" - Black Sabbath
- "Angel of Death" - Slayer
- "Raining Blood" - Slayer
- "South of Heaven" - Slayer
- "Seasons in the Abyss" - Slayer
- "Dead Skin Mask" - Slayer
- "Hell Awaits" - Slayer
- "Postmortem" - Slayer
- "Chemical Warfare" - Slayer
- "Mandatory Suicide" - Slayer
- "Disciple" - Slayer

### Country - Drinking/Partying (30 songs)
- "Friends in Low Places" - Garth Brooks
- "The Thunder Rolls" - Garth Brooks
- "Two Pina Coladas" - Garth Brooks
- "Callin' Baton Rouge" - Garth Brooks
- "Papa Loved Mama" - Garth Brooks
- "Shameless" - Garth Brooks
- "The River" - Garth Brooks
- "We Shall Be Free" - Garth Brooks
- "Standing Outside the Fire" - Garth Brooks
- "The Dance" - Garth Brooks
- "Drunk on You" - Luke Bryan
- "Country Girl (Shake It for Me)" - Luke Bryan
- "Crash My Party" - Luke Bryan
- "Play It Again" - Luke Bryan
- "That's My Kind of Night" - Luke Bryan
- "Drink a Beer" - Luke Bryan
- "Fast" - Luke Bryan
- "I See You" - Luke Bryan
- "Kick the Dust Up" - Luke Bryan
- "Strip It Down" - Luke Bryan
- "Cruise" - Florida Georgia Line
- "Get Your Shine On" - Florida Georgia Line
- "Round Here" - Florida Georgia Line
- "Stay" - Florida Georgia Line
- "This Is How We Roll" - Florida Georgia Line
- "Sun Daze" - Florida Georgia Line
- "Dirt" - Florida Georgia Line
- "Sippin' on Fire" - Florida Georgia Line
- "Anything Goes" - Florida Georgia Line
- "Confession" - Florida Georgia Line

### Trap/Modern Rap - Explicit (19 songs)
- "Mask Off" - Future
- "March Madness" - Future
- "Jumpin on a Jet" - Future
- "Life Is Good" - Future
- "Crushed Up" - Future
- "First Off" - Future
- "Rocket Ship" - Future
- "Trapped in the Sun" - Future
- "St. Lucia" - Future
- "Harlem Shake" - Future
- "Bad (feat. Lil Wayne)" - XXXTentacion
- "Moonlight" - XXXTentacion
- "SAD!" - XXXTentacion
- "Jocelyn Flores" - XXXTentacion
- "Changes" - XXXTentacion
- "Hope" - XXXTentacion
- "Revenge" - XXXTentacion
- "Look at Me!" - XXXTentacion
- "Roll In Peace" - XXXTentacion

---

## Summary Statistics

| Category | Songs | % of 728 |
|----------|-------|----------|
| **Freely Listen** | 196 | 26.9% |
| **Context Required** | 86 | 11.8% |
| **Caution Limit** | 137 | 18.8% |
| **Avoid Formation** | 309 | 42.4% |
| **TOTAL** | **728** | **100%** |

---

## Next Steps

1. Convert this markdown to JSONL format
2. Run `generate_training_data.py` with concurrency=5
3. Expected time: ~35-40 minutes
4. Expected cost: ~$2.00-2.50
5. Merge with existing 272 songs for 1,000 total dataset

