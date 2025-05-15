import logging

logger = logging.getLogger(__name__)

def get_christian_rubric():
    """
    Provides the definitive Christian rubric for song analysis.
    This includes scoring, themes, purity flags, and scripture mappings (keywords for now).
    """
    rubric = {
        "baseline_score": 100,
        "score_min_cap": 0,
        "score_max_cap": 100,
        "negative_theme_penalty": 10, # Points deducted per distinct negative theme
        "positive_theme_points": 5,    # Points added per distinct positive theme

        "concern_thresholds": {
            "low_starts_at": 70,    # Score >= 70 and no purity flags = Low
            "medium_starts_at": 40, # Score 40-69 and no purity flags = Medium
                                    # Score < 40 or any purity flag = High
        },

        "purity_flag_definitions": {
            # Mappings for CardiffNLP model outputs to our defined flags and penalties
            "cardiffnlp_model_map": {
                "hate": {
                    "flag_name": "Hate Speech Detected",
                    "penalty": 75,
                    "description": "Content classified as hate speech by the model."
                },
                "offensive": {
                    "flag_name": "Explicit Language / Corrupting Talk",
                    "penalty": 50,
                    "description": "Content classified as offensive by the model (not hate speech)."
                }
                # 'not-offensive' from CardiffNLP implies no penalty from this model.
            },
            # Definitions for other purity flags (currently MVP, may require more complex detection)
            # These penalties can stack if different conditions are met.
            "other_flags_mvp": {
                "sexual_content_overt": {
                    "flag_name": "Sexual Content / Impurity (overt)",
                    "penalty": 50,
                    "description": "Overt sexual content or impurity. MVP: Assumed if 'offensive' label from CardiffNLP is present and context strongly implies sexual themes (manual review for now, future: specific keywords/model). Stacks if applicable."
                },
                "glorification_drugs_violence_flesh": {
                    "flag_name": "Glorification of Drugs / Violence / Works of Flesh (overt)",
                    "penalty": 25,
                    "description": "Overt glorification of drugs, violence, or other works of the flesh. MVP: Assumed if 'offensive' label from CardiffNLP is present and context implies these themes (manual review for now, future: specific keywords/model). Stacks if applicable."
                }
            }
        },

        "positive_themes_config": [
            {"id": "worship_glorifying_god", "name": "Worship / Glorifying God", "keywords": ["worship", "praise", "glory", "glorify", "adore", "exalt", "honor", "magnify", "thanks", "thankful", "grateful", "gratitude", "hallelujah", "holy", "lord", "almighty", "hosanna"], "threshold": 1, "scripture_keywords": ["Psalm 95:6", "Psalm 100", "Revelation 4:11"]},
            {"id": "holiness_of_god", "name": "Holiness of God", "keywords": ["holy", "holiness", "sacred", "pure", "righteous god", "set apart"], "threshold": 1, "scripture_keywords": ["Isaiah 6:3", "1 Peter 1:16"]},
            {"id": "goodness_faithfulness_god", "name": "Goodness & Faithfulness of God", "keywords": ["good god", "god is good", "faithful god", "faithfulness", "mercy endures", "never fails"], "threshold": 1, "scripture_keywords": ["Psalm 107:1", "Lamentations 3:22-23"]},
            {"id": "faith_trust_god", "name": "Faith / Trust in God", "keywords": ["faith", "trust", "believe", "rely", "depend on god", "confidence in god"], "threshold": 1, "scripture_keywords": ["Proverbs 3:5-6", "Hebrews 11:1"]},
            {"id": "hope_in_christ_eternal_life", "name": "Hope in Christ / Eternal Life", "keywords": ["hope", "eternal life", "heaven", "new jerusalem", "resurrection", "christ our hope"], "threshold": 1, "scripture_keywords": ["Titus 2:13", "1 Peter 1:3"]},
            {"id": "love_godly_compassion", "name": "Love / Godly Compassion", "keywords": ["love", "agape", "compassion", "grace", "mercy", "kindness"], "threshold": 1, "scripture_keywords": ["1 Corinthians 13", "John 3:16"]},
            {"id": "truth_biblical_wisdom", "name": "Truth / Biblical Wisdom", "keywords": ["truth", "wisdom", "word of god", "scripture", "discernment", "understanding"], "threshold": 1, "scripture_keywords": ["John 14:6", "Proverbs 2:6"]},
            {"id": "redemption_grace_christ", "name": "Redemption / Grace through Christ", "keywords": ["redeemed", "redemption", "grace", "forgiven", "forgiveness", "salvation", "blood of christ", "cross", "atonement"], "threshold": 1, "scripture_keywords": ["Ephesians 1:7", "Romans 3:24"]},
            {"id": "peace_gods_comfort_presence", "name": "Peace / God's Comfort & Presence", "keywords": ["peace", "comfort", "presence of god", "god with us", "rest", "refuge", "strength"], "threshold": 1, "scripture_keywords": ["Philippians 4:6-7", "John 14:27"]},
            {"id": "spiritual_growth_discipleship_sanctification", "name": "Spiritual Growth / Discipleship / Sanctification", "keywords": ["grow in christ", "discipleship", "sanctification", "transformed", "follow jesus", "walk with god", "bear fruit"], "threshold": 1, "scripture_keywords": ["2 Peter 3:18", "Philippians 1:6"]}
        ],

        "negative_themes_config": [
            {"id": "worldliness_idolatry", "name": "Worldliness / Idolatry", "keywords": ["world", "worldly", "idolatry", "idol", "materialism", "riches", "fame", "fortune", "mammon"], "threshold": 1, "scripture_keywords": ["1 John 2:15-17", "Matthew 6:24"]},
            {"id": "pride_self_glorification", "name": "Pride / Self-Glorification", "keywords": ["pride", "boast", "arrogant", "self-glorification", "haughty", "ego", "self-sufficient"], "threshold": 1, "scripture_keywords": ["Proverbs 16:18", "James 4:6"]},
            {"id": "lust_impurity_message", "name": "Lust / Impurity (as a message)", "keywords": ["lust", "immorality", "impure thoughts", "sexual sin", "sensual"], "threshold": 1, "scripture_keywords": ["Matthew 5:28", "1 Thessalonians 4:3-5"]},
            {"id": "selfishness_greed_covetousness", "name": "Selfishness / Greed / Covetousness", "keywords": ["selfish", "greed", "covet", "envy", "possessions", "avarice"], "threshold": 1, "scripture_keywords": ["Luke 12:15", "Hebrews 13:5"]},
            {"id": "hopelessness_despair_apart_from_god", "name": "Hopelessness / Despair (apart from God)", "keywords": ["hopeless", "despair", "no hope", "meaningless", "empty apart from god"], "threshold": 1, "scripture_keywords": ["Ephesians 2:12", "Psalm 42:11"]},
            {"id": "rebellion_disobedience_god", "name": "Rebellion / Disobedience to God", "keywords": ["rebel", "disobey", "defy god", "lawless", "sinful rebellion"], "threshold": 1, "scripture_keywords": ["1 Samuel 15:23", "Romans 6:23"]},
            {"id": "unjust_anger_strife_malice_message", "name": "Unjust Anger / Strife / Malice (as a message)", "keywords": ["hate", "anger", "wrath", "bitter", "malice", "strife", "discord", "unforgiveness"], "threshold": 1, "scripture_keywords": ["Ephesians 4:31", "James 1:19-20"]},
            {"id": "deception_falsehood_message", "name": "Deception / Falsehood (as a message)", "keywords": ["deceive", "lie", "falsehood", "mislead", "false prophet", "false teacher"], "threshold": 1, "scripture_keywords": ["Proverbs 12:22", "John 8:44"]}
        ],
        
        "scripture_api_config": {
            "base_url": "https://api.scripture.api.bible/v1",
            "bsb_bible_id": "04dc1c2b8e506282-01", # Berean Standard Bible (BSB)
            "kjv_bible_id": "de4e12af7f28f599-01"  # King James Version (KJV)
        }
    }
    logger.debug("Christian rubric loaded.")
    return rubric

if __name__ == '__main__':
    # Example of how to access the rubric
    logging.basicConfig(level=logging.DEBUG)
    rubric_data = get_christian_rubric()
    logger.info(f"Baseline score: {rubric_data['baseline_score']}")
    logger.info(f"First positive theme: {rubric_data['positive_themes_config'][0]['name']}")
    logger.info(f"Hate speech penalty: {rubric_data['purity_flag_definitions']['cardiffnlp_model_map']['hate']['penalty']}")
