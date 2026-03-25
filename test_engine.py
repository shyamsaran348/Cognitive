import os
import time
import numpy as np
from importlib import import_module

# Lazily import the feature extractor for Whisper transcription
spec = os.path.join(os.getcwd(), "03_feature_extractor.py")
extractor = import_module("03_feature_extractor")

# Clinically-calibrated domain weights (based on MoCA/ACE-III sensitivity literature)
# These apply per-domain, averaged across the domain's 2 tests.
DOMAIN_WEIGHTS = {
    "memory":       0.20,   # Hippocampal proxy — highest sensitivity for early AD
    "recall":       0.20,   # Delayed recall — strongest single predictor of AD
    "executive":    0.15,   # Frontal lobe — key for MCI differentiation
    "fluency":      0.15,   # Language/executive overlap
    "attention":    0.15,   # Working memory proxy
    "language":     0.10,   # Phonological integrity
    "visuospatial": 0.10,   # Parietal integrity
    "orientation":  0.10,   # Temporal/spatial awareness
}

class ActiveTestEngine:
    """
    Orchestrates prompted cognitive tasks and scores them using Whisper and
    clinically-calibrated domain weighting. Produces rich metadata per task.
    """
    # ── 2 Tests Per Domain — Full Clinical Battery ────────────────────────────
    TASKS = {
        # ── DOMAIN 1: MEMORY (Registration) ────────────────────────────────────
        "memory": {
            "prompt": "Please repeat these three words: Apple, Penny, Table. Keep them in mind — I will ask you again later.",
            "type": "memory",
            "keywords": ["apple", "penny", "table"],
            "points": 3,
            "domain_label": "Memory – Registration"
        },
        "story_recall": {
            "prompt": ("Listen carefully to this short story, then repeat it back to me in your own words: "
                       "'A woman named Anna went to the market on a rainy Tuesday. She bought bread, eggs, and milk, then returned home.'"),
            "type": "memory",
            "keywords": ["anna", "market", "tuesday", "bread", "eggs", "milk", "rainy", "home"],
            "points": 8,
            "domain_label": "Memory – Story Recall"
        },

        # ── DOMAIN 2: LANGUAGE ──────────────────────────────────────────────────
        "language_repeat": {
            "prompt": "Repeat this sentence exactly: 'The cat always hides under the wooden table.'",
            "type": "language",
            "keywords": ["cat", "hides", "under", "wooden", "table"],
            "points": 5,
            "domain_label": "Language – Sentence Repetition"
        },
        "language_naming": {
            "prompt": ("I will describe three objects. Tell me what each one is called. "
                       "First: something used to keep food cold. "
                       "Second: something you use to tell the time. "
                       "Third: something you use to write."),
            "type": "language",
            "keywords": ["fridge", "refrigerator", "clock", "watch", "pen", "pencil"],
            "points": 6,
            "domain_label": "Language – Naming"
        },

        # ── DOMAIN 3: FLUENCY ───────────────────────────────────────────────────
        "fluency": {
            "prompt": "Name as many animals as you can in the next 30 seconds. Start now!",
            "type": "fluency",
            "keywords": ["dog", "cat", "bird", "lion", "tiger", "elephant", "cow", "pig", "sheep",
                         "horse", "snake", "fish", "monkey", "bear", "rabbit", "deer", "wolf",
                         "fox", "frog", "turtle", "chicken", "duck", "goat", "rat", "whale"],
            "points": 10,
            "domain_label": "Fluency – Semantic"
        },
        "fluency_phonemic": {
            "prompt": "Say as many words as you can that start with the letter F. You have 30 seconds. Go!",
            "type": "fluency",
            "keywords": ["fan", "fire", "fish", "foot", "farm", "flag", "face", "fast", "fall",
                         "feel", "find", "fold", "food", "five", "fork", "fly", "far", "fun",
                         "fill", "fact", "form", "flow", "ford", "fair", "film"],
            "points": 10,
            "domain_label": "Fluency – Phonemic (F-words)"
        },

        # ── DOMAIN 4: EXECUTIVE FUNCTION ────────────────────────────────────────
        "executive_trail": {
            "prompt": "Say this alternating sequence out loud: 1-A, 2-B, 3-C, 4-D, 5-E.",
            "type": "executive",
            "keywords": ["1", "a", "2", "b", "3", "c", "4", "d", "5", "e"],
            "points": 5,
            "domain_label": "Executive – Verbal Trail Making"
        },
        "executive_abstract": {
            "prompt": "I will name two things. Tell me how they are similar. First: How are a banana and an orange similar? Second: How are a train and a bicycle similar?",
            "type": "executive",
            "keywords": ["fruit", "food", "yellow", "transport", "vehicle", "ride", "travel", "wheels"],
            "points": 4,
            "domain_label": "Executive – Abstract Reasoning"
        },

        # ── DOMAIN 5: ATTENTION ─────────────────────────────────────────────────
        "attention_digits": {
            "prompt": "Repeat these numbers in the exact order I say them: 7 — 4 — 1 — 9 — 3.",
            "type": "attention",
            "keywords": ["7", "4", "1", "9", "3", "seven", "four", "one", "nine", "three"],
            "points": 5,
            "domain_label": "Attention – Digit Span"
        },
        "attention_serial7": {
            "prompt": "Starting from 100, subtract 7 and keep going. Say each answer out loud: 100 minus 7 is... and continue.",
            "type": "attention",
            "keywords": ["93", "86", "79", "72", "65"],
            "points": 5,
            "domain_label": "Attention – Serial 7s"
        },

        # ── DOMAIN 6: VISUOSPATIAL ──────────────────────────────────────────────
        "visuospatial_spatial": {
            "prompt": "If you walk facing North, then turn left, and then turn left again — which direction are you now facing?",
            "type": "visuospatial",
            "keywords": ["south"],
            "points": 3,
            "domain_label": "Visuospatial – Spatial Reasoning"
        },
        "visuospatial_clock": {
            "prompt": "Describe what a clock looks like. Think about its shape, what is on its face, and what goes around it.",
            "type": "visuospatial",
            "keywords": ["round", "circle", "numbers", "hands", "twelve", "tick", "face", "hour", "minute"],
            "points": 5,
            "domain_label": "Visuospatial – Object Description"
        },

        # ── DOMAIN 7: ORIENTATION ───────────────────────────────────────────────
        "orientation_time": {
            "prompt": "What is today's date? Tell me the day, month, and year.",
            "type": "orientation",
            "keywords": ["march", "2026", "tuesday", "25", "twenty-fifth"],
            "points": 3,
            "domain_label": "Orientation – Time"
        },
        "orientation_place": {
            "prompt": "Where are you right now? Please describe the place — the city, and if you can, the type of place you are in.",
            "type": "orientation",
            "keywords": ["india", "home", "house", "hospital", "clinic", "room", "office", "building", "city"],
            "points": 3,
            "domain_label": "Orientation – Place"
        },

        # ── MEMORY RECALL (Delayed — always last) ──────────────────────────────
        "recall": {
            "prompt": "Earlier I asked you to remember three words. What were they?",
            "type": "recall",
            "keywords": ["apple", "penny", "table"],
            "points": 3,
            "domain_label": "Memory – Delayed Recall"
        },
    }

    # ── ACE-III Task Battery (Addenbrooke's Cognitive Examination III) ─────────
    ACE3_TASKS = {
        "ace3_attention_count": {
            "prompt": "Count backwards from 100 to 91. Say each number out loud.",
            "type": "attention",
            "keywords": ["99", "98", "97", "96", "95", "94", "93", "92", "91"],
            "points": 9,
            "domain_label": "Clinical Battery – Attention: Counting",
            "input_mode": "voice"
        },
        "ace3_attention_serial": {
            "prompt": "Subtract 7 from 100, then keep subtracting 7. Give me five answers.",
            "type": "attention",
            "keywords": ["93", "86", "79", "72", "65"],
            "points": 5,
            "domain_label": "Clinical Battery – Attention: Serial 7s",
            "input_mode": "voice"
        },
        "ace3_memory_registration": {
            "prompt": "I will say three words. Please repeat them: Lemon, Key, Ball.",
            "type": "memory",
            "keywords": ["lemon", "key", "ball"],
            "points": 3,
            "domain_label": "Clinical Battery – Memory: Registration",
            "input_mode": "voice",
            "should_speak": True,
            "hide_text": True
        },
        "ace3_fluency_letters": {
            "prompt": "Say as many words as you can beginning with the letter P. You have 60 seconds.",
            "type": "fluency",
            "keywords": ["pen", "paper", "pink", "park", "pet", "path", "plan", "plug",
                         "pay", "pace", "pole", "pool", "pot", "port", "part", "palm", "past", "pill"],
            "points": 14,
            "domain_label": "Clinical Battery – Fluency: Letter P",
            "input_mode": "voice"
        },
        "ace3_fluency_animals": {
            "prompt": "Now name as many animals as you can. You have 60 seconds.",
            "type": "fluency",
            "keywords": ["dog", "cat", "horse", "cow", "pig", "sheep", "lion", "tiger", "bird",
                         "fish", "snake", "rabbit", "bear", "wolf", "fox", "elephant", "monkey",
                         "frog", "turtle", "deer", "whale", "eagle"],
            "points": 22,
            "domain_label": "Clinical Battery – Fluency: Animals",
            "input_mode": "voice"
        },
        "ace3_language_repeat": {
            "prompt": "Repeat after me: 'The cat always hid beneath the garden table.'",
            "type": "language",
            "keywords": ["cat", "hid", "beneath", "garden", "table"],
            "points": 5,
            "domain_label": "Clinical Battery – Language: Repetition",
            "input_mode": "voice",
            "should_speak": True,
            "hide_text": True
        },
        "ace3_language_naming": {
            "prompt": ("I will describe something — tell me what it is. "
                       "First: a flat surface you write on at school. "
                       "Second: something that controls a lock. "
                       "Third: something you use to cut bread."),
            "type": "language",
            "keywords": ["blackboard", "board", "key", "knife"],
            "points": 4,
            "domain_label": "Clinical Battery – Language: Naming",
            "input_mode": "text"
        },
        "ace3_visuospatial": {
            "prompt": ("Describe the clock on a typical analogue clock face — what numbers are at "
                       "the top, left, right, and bottom?"),
            "type": "visuospatial",
            "keywords": ["twelve", "twelve", "three", "six", "nine", "top", "bottom"],
            "points": 5,
            "domain_label": "Clinical Battery – Visuospatial: Clock Face",
            "input_mode": "text"
        },
        "ace3_memory_recall": {
            "prompt": "Do you remember the three words I asked you to repeat earlier? Please say them.",
            "type": "recall",
            "keywords": ["lemon", "key", "ball"],
            "points": 3,
            "domain_label": "Clinical Battery – Memory: Delayed Recall",
            "input_mode": "text"
        },
        "ace3_orientation": {
            "prompt": "What year is it? What month? What day of the week? And what city are you in?",
            "type": "orientation",
            "keywords": ["2026", "march", "tuesday", "india"],
            "points": 4,
            "domain_label": "Clinical Battery – Orientation",
            "input_mode": "text"
        },
        "ace3_trail_making": {
            "prompt": "Connect the numbers and letters in alternating order: 1-A, 2-B, 3-C, 4-D, 5-E.",
            "type": "executive",
            "keywords": ["success"],
            "points": 1,
            "domain_label": "Clinical Battery – Executive: Trail Making B",
            "input_mode": "visual"
        },
        "ace3_digit_span_back": {
            "prompt": "Repeat these numbers in REVERSE order: 7 — 4 — 2.",
            "type": "attention",
            "keywords": ["2", "4", "7"],
            "points": 1,
            "domain_label": "Clinical Battery – Attention: Digits Backward",
            "input_mode": "text"
        },
        "ace3_abstraction_sim1": {
            "prompt": "In what way are an ORANGE and a BANANA similar?",
            "type": "executive",
            "keywords": ["fruit", "food", "eat", "peel", "healthy"],
            "points": 1,
            "domain_label": "Clinical Battery – Executive: Abstraction 1",
            "input_mode": "text"
        },
        "ace3_abstraction_sim2": {
            "prompt": "In what way are a TRAIN and a BICYCLE similar?",
            "type": "executive",
            "keywords": ["vehicle", "transport", "travel", "ride", "wheels", "move"],
            "points": 1,
            "domain_label": "Clinical Battery – Executive: Abstraction 2",
            "input_mode": "text"
        },
        "ace3_language_repeat_complex": {
            "prompt": "Repeat after me: 'I only know that John is the one to help today.'",
            "type": "language",
            "keywords": ["john", "one", "help", "today"],
            "points": 1,
            "domain_label": "Clinical Battery – Language: Complex Repetition",
            "input_mode": "voice",
            "should_speak": True,
            "hide_text": True
        },
    }

    # ── MoCA Task Battery (Montreal Cognitive Assessment) ─────────────────────
    MOCA_TASKS = {
        "moca_trail": {
            "prompt": "Say this alternating sequence: 1-A, 2-B, 3-C, 4-D, 5-E.",
            "type": "executive",
            "keywords": ["1", "a", "2", "b", "3", "c", "4", "d", "5", "e"],
            "points": 1,
            "domain_label": "MoCA – Trail Making B"
        },
        "moca_digit_span_forward": {
            "prompt": "Repeat these numbers: 2 — 1 — 8 — 5 — 4.",
            "type": "attention",
            "keywords": ["2", "1", "8", "5", "4", "two", "one", "eight", "five", "four"],
            "points": 1,
            "domain_label": "MoCA – Digit Span Forward"
        },
        "moca_digit_span_backward": {
            "prompt": "Now repeat these numbers in REVERSE order: 7 — 4 — 2.",
            "type": "attention",
            "keywords": ["2", "4", "7"],
            "points": 1,
            "domain_label": "MoCA – Digit Span Backward"
        },
        "moca_vigilance": {
            "prompt": ("I will read a list. Tap or say 'yes' every time you hear the letter A: "
                       "F — B — A — C — M — N — A — A — J — K — L — B — A — F — A — K."),
            "type": "attention",
            "keywords": ["yes", "a"],
            "points": 1,
            "domain_label": "MoCA – Vigilance (Letter A)"
        },
        "moca_serial7": {
            "prompt": "Starting from 100, subtract 7 repeatedly. Give me five answers.",
            "type": "attention",
            "keywords": ["93", "86", "79", "72", "65"],
            "points": 3,
            "domain_label": "MoCA – Serial 7s"
        },
        "moca_repeat_sentence1": {
            "prompt": "Repeat exactly: 'I only know that John is the one to help today.'",
            "type": "language",
            "keywords": ["john", "help", "today", "only", "know"],
            "points": 1,
            "domain_label": "MoCA – Sentence Repetition 1"
        },
        "moca_repeat_sentence2": {
            "prompt": "Now repeat: 'The cat always hid beneath the garden table.'",
            "type": "language",
            "keywords": ["cat", "hid", "beneath", "garden", "table"],
            "points": 1,
            "domain_label": "MoCA – Sentence Repetition 2"
        },
        "moca_fluency": {
            "prompt": "Say as many words as you can that start with the letter F. You have 60 seconds.",
            "type": "fluency",
            "keywords": ["fan", "fire", "fish", "foot", "farm", "flag", "face", "fast", "fall",
                         "feel", "find", "fold", "food", "five", "fork", "fly", "far", "fun"],
            "points": 1,
            "domain_label": "MoCA – Verbal Fluency (F-words)"
        },
        "moca_abstraction1": {
            "prompt": "How are a train and a bicycle similar?",
            "type": "executive",
            "keywords": ["vehicle", "transport", "travel", "ride", "wheels", "move"],
            "points": 1,
            "domain_label": "MoCA – Abstraction 1"
        },
        "moca_abstraction2": {
            "prompt": "How are a ruler and a watch similar?",
            "type": "executive",
            "keywords": ["measure", "tool", "instrument", "time", "length"],
            "points": 1,
            "domain_label": "MoCA – Abstraction 2"
        },
        "moca_registration": {
            "prompt": "I will say five words. Please repeat them all: Face — Velvet — Church — Daisy — Red.",
            "type": "memory",
            "keywords": ["face", "velvet", "church", "daisy", "red"],
            "points": 0,
            "domain_label": "MoCA – Memory Registration (no score)"
        },
        "moca_delayed_recall": {
            "prompt": "What were the five words I asked you to remember? Please say all of them.",
            "type": "recall",
            "keywords": ["face", "velvet", "church", "daisy", "red"],
            "points": 5,
            "domain_label": "MoCA – Delayed Recall"
        },
        "moca_orientation": {
            "prompt": "Tell me today's date, month, year, day of the week, the place you are in, and the city.",
            "type": "orientation",
            "keywords": ["march", "2026", "tuesday", "25", "india"],
            "points": 6,
            "domain_label": "MoCA – Full Orientation"
        },
    }

    def get_tasks_for_type(self, test_type: str) -> dict:
        """Returns the task registry for the given test type."""
        if test_type in ("ace3", "active", "battery"):
            return self.ACE3_TASKS
        return self.TASKS  # default: CogniSense battery

    def score_response(self, task_key, audio_path=None, test_type: str = "cogni", text_response: str = None):
        """
        Transcribes the response (or uses text input) and calculates a domain score with rich metadata.
        Returns: (score, transcript, metadata_dict)
        """
        task_registry = self.get_tasks_for_type(test_type)
        if task_key not in task_registry:
            # Fallback: try the main TASKS dict
            if task_key not in self.TASKS:
                return 0, "", {}
            task_registry = self.TASKS

        task = task_registry[task_key]
        t_start = time.time()

        # 1. Obtain Transcript ───────────────────────────────────────────────────
        if text_response:
            print(f"[TEST_ENGINE] Using direct text response for task: {task_key}")
            transcript = text_response.lower().strip()
        elif audio_path:
            print(f"[TEST_ENGINE] Transcribing response for task: {task_key}")
            try:
                # Use faster 'base' model for active tasks to ensure smooth transitions
                _, transcript = extractor.extract_whisper(audio_path, transcribe=True, model_size="base")
                transcript = transcript.lower().strip()
            except Exception as e:
                print(f"[ERROR] ASR Failed: {e}")
                return 0, "ASR Error", {"latency": 0, "confidence": 0.0, "asr_error": True}
        else:
            return 0, "No input provided", {}

        latency = round(time.time() - t_start, 2)
        domain_type  = task.get("type", "generic")
        keywords     = task["keywords"]
        max_points   = task["points"]
        words_in_transcript = set(transcript.replace(",", " ").replace(".", " ").split())

        # ── 2a. MEMORY / RECALL — Order-preserved + Intrusion penalty ────────────
        if domain_type in ("memory", "recall"):
            # Count correctly recalled words
            correct_words = [kw for kw in keywords if kw in transcript]
            correct_count = len(correct_words)

            # Order preservation: check if found words appear in sequence
            order_score = 0
            last_pos = -1
            for kw in keywords:
                pos = transcript.find(kw)
                if pos > last_pos and pos != -1:
                    order_score += 1
                    last_pos = pos
            order_bonus = round(order_score / max(1, len(keywords)), 2)

            # Intrusion penalty: words spoken that are NOT keywords
            expected_set = set(keywords)
            spoken_content_words = {w for w in words_in_transcript if len(w) > 3}
            intrusions = spoken_content_words - expected_set
            intrusion_penalty = min(correct_count, len(intrusions) // 3)  # 1 penalty per 3 intrusions

            raw_score  = max(0, correct_count - intrusion_penalty)
            score      = min(max_points, raw_score)
            found_keywords = correct_words
            scoring_method = "order_preserved_memory"
            extra_meta = {"order_bonus": order_bonus, "intrusions_detected": len(intrusions)}

        # ── 2b. LANGUAGE (repetition) — Edit Distance scoring ────────────────────
        elif domain_type == "language" and any(kw in task.get("prompt", "").lower() for kw in ["repeat", "say exactly", "repeat exactly"]):
            from difflib import SequenceMatcher
            # Extract the sentence to repeat from the prompt (after the colon/quote)
            prompt = task.get("prompt", "")
            target = " ".join(keywords)  # keywords are the key words in the target sentence

            ratio = SequenceMatcher(None, target, transcript).ratio()
            # Also check keyword coverage
            keyword_hits = sum(1 for kw in keywords if kw in transcript)
            keyword_ratio = keyword_hits / max(1, len(keywords))

            # Blended score: 60% edit distance, 40% keyword coverage
            blended = 0.6 * ratio + 0.4 * keyword_ratio
            score   = round(blended * max_points)
            score   = int(np.clip(score, 0, max_points))
            found_keywords = [kw for kw in keywords if kw in transcript]
            scoring_method = "edit_distance_language"
            extra_meta = {"edit_similarity": round(ratio, 3), "keyword_ratio": round(keyword_ratio, 3)}

        # ── 2c. LANGUAGE (naming) — Keyword + Latency quality ────────────────────
        elif domain_type == "language":
            found_keywords = [kw for kw in keywords if kw in transcript]
            keyword_hits   = len(found_keywords)
            # Latency quality: penalize very slow responses (>5s)
            latency_quality = float(np.clip(1.0 - (latency - 2.0) / 10.0, 0.5, 1.0))
            score = min(max_points, int(keyword_hits * latency_quality + 0.5))
            scoring_method = "keyword_latency_naming"
            extra_meta = {"latency_quality": round(latency_quality, 3)}

        # ── 2d. FLUENCY — Unique valid words + Semantic clustering ───────────────
        elif domain_type == "fluency":
            # Semantic clusters for animal fluency
            CLUSTERS = {
                "pets":       {"dog", "cat", "rabbit", "hamster", "guinea", "fish", "bird"},
                "farm":       {"cow", "pig", "sheep", "horse", "chicken", "duck", "goat"},
                "wild_big":   {"lion", "tiger", "elephant", "bear", "wolf", "rhino", "hippo"},
                "wild_small": {"fox", "deer", "rabbit", "squirrel", "rat", "mouse"},
                "aquatic":    {"fish", "whale", "dolphin", "shark", "seal", "turtle"},
                "birds":      {"eagle", "parrot", "crow", "owl", "penguin", "flamingo"},
            }
            found_keywords = [kw for kw in keywords if kw in transcript]
            unique_valid   = list(dict.fromkeys(found_keywords))  # preserve order, deduplicate

            # Cluster bonus: extra point for switching between clusters
            active_clusters = []
            for cluster_name, cluster_words in CLUSTERS.items():
                if any(w in cluster_words for w in unique_valid):
                    active_clusters.append(cluster_name)
            cluster_bonus = min(2, len(active_clusters))  # max +2 bonus for diverse clustering

            raw_score = len(unique_valid) + cluster_bonus
            score     = min(max_points, raw_score)
            scoring_method = "fluency_unique_cluster"
            extra_meta = {"unique_words": len(unique_valid), "clusters_activated": active_clusters,
                          "cluster_bonus": cluster_bonus}

        # ── 2e. ATTENTION — Exact sequence order matching ────────────────────────
        elif domain_type == "attention":
            # For digit span and serial 7s: order matters
            expected_seq = keywords  # e.g. ["7", "4", "1", "9", "3"]
            spoken_sequence = []
            for token in transcript.replace(",", " ").replace("-", " ").split():
                if token in expected_seq or any(
                    tok == token for tok in ["one","two","three","four","five","six","seven","eight","nine","zero","93","86","79","72","65"]
                ):
                    spoken_sequence.append(token)

            # Score: how many consecutive elements from expected appear in order
            correct_in_order = 0
            exp_idx = 0
            for spoken in spoken_sequence:
                if exp_idx < len(expected_seq) and (spoken == expected_seq[exp_idx] or
                   spoken in {"one":"1","two":"2","three":"3","four":"4","five":"5",
                               "six":"6","seven":"7","eight":"8","nine":"9","zero":"0"}.get(spoken, "")):
                    correct_in_order += 1
                    exp_idx += 1
                elif spoken in expected_seq:
                    correct_in_order += 1  # correct word, wrong order: partial credit
                    exp_idx = expected_seq.index(spoken) + 1

            # Also count simple keyword hits as fallback
            keyword_hits = sum(1 for kw in expected_seq if kw in transcript)
            # Use the max of sequence matching and simple keyword matching
            score = min(max_points, max(correct_in_order, keyword_hits))
            found_keywords = [kw for kw in expected_seq if kw in transcript]
            scoring_method = "sequence_order_attention"
            extra_meta = {"correct_in_order": correct_in_order, "keyword_hits": keyword_hits}

        # ── 2f. ORIENTATION — Partial match (each item scored independently) ─────
        elif domain_type == "orientation":
            found_keywords = [kw for kw in keywords if kw in transcript]
            # Each keyword is an independent orientation item (date, month, year, place)
            partial_score = len(found_keywords)
            score = min(max_points, partial_score)
            scoring_method = "partial_match_orientation"
            extra_meta = {"items_correct": partial_score, "items_total": len(keywords)}

        # ── 2g. EXECUTIVE — Category detection (abstract reasoning) ──────────────
        elif domain_type == "executive":
            # For trail making: sequence matching
            # For abstract reasoning: category/concept keyword detection
            found_keywords = [kw for kw in keywords if kw in transcript]
            keyword_hits   = len(found_keywords)

            # Category depth bonus: "fruit" is better than just "yellow" for banana/orange
            HIGH_LEVEL_CATEGORIES = {"fruit", "food", "vehicle", "transport", "tool", "instrument",
                                      "measure", "animal", "plant", "color", "shape"}
            category_hit = any(cat in transcript for cat in HIGH_LEVEL_CATEGORIES)
            bonus = 1 if category_hit and keyword_hits > 0 else 0

            score = min(max_points, keyword_hits + bonus)
            scoring_method = "category_executive"
            extra_meta = {"category_detected": category_hit, "category_bonus": bonus}

        # ── 2h. GENERIC fallback — Keyword count ─────────────────────────────────
        else:
            found_keywords = [kw for kw in keywords if kw in transcript]
            score          = min(max_points, len(found_keywords))
            scoring_method = "keyword_count"
            extra_meta     = {}

        # ── 3. Compute confidence ─────────────────────────────────────────────────
        normalized_score = score / max_points if max_points > 0 else 0.0
        task_confidence  = round(max(0.1, normalized_score), 3)

        metadata = {
            "latency":          latency,
            "confidence":       task_confidence,
            "normalized_score": round(normalized_score, 3),
            "found_keywords":   found_keywords,
            "total_keywords":   len(keywords),
            "scoring_method":   scoring_method,
            **extra_meta
        }

        print(f"[TEST_ENGINE] Task: {task_key} | Score: {score}/{max_points} | Method: {scoring_method} | "
              f"Conf: {task_confidence:.2f} | Latency: {latency}s")
        return score, transcript, metadata

    def get_next_prompt(self, current_task_index, test_type: str = "cogni"):
        task_registry = self.get_tasks_for_type(test_type)
        keys = list(task_registry.keys())
        if current_task_index < len(keys):
            key = keys[current_task_index]
            return {
                "key": key,
                "prompt": task_registry[key]["prompt"],
                "points": task_registry[key]["points"],
                "domain_label": task_registry[key].get("domain_label", key),
                "input_mode": task_registry[key].get("input_mode", "voice"),
                "should_speak": task_registry[key].get("should_speak", False),
                "hide_text": task_registry[key].get("hide_text", False),
                "index": current_task_index,
                "total": len(keys)
            }
        return None

    def calculate_active_index(self, results, test_type: str = "cogni"):
        """
        Computes the Active Cognitive Index with composite confidence:
          0.6 * domain_consistency  (inverse of score variance)
          0.2 * avg_asr_confidence  (keyword hit ratio per task)
          0.2 * latency_quality     (inverse of normalized avg latency)
        Returns: (active_index_0_to_30, active_confidence_0_to_1)
        """
        if not results:
            return 30.0, 1.0

        task_registry = self.get_tasks_for_type(test_type)
        domain_scores_normalized = []
        asr_confidences = []
        latencies = []
        weighted_sum = 0.0
        total_weight = 0.0

        for key, task in task_registry.items():
            res = results.get(key, {})
            score = res.get("score", 0)
            max_points = task["points"]
            normalized = score / max_points if max_points > 0 else 1.0
            weight = DOMAIN_WEIGHTS.get(task["type"], 0.1)

            weighted_sum += normalized * weight
            total_weight += weight
            domain_scores_normalized.append(normalized)
            asr_confidences.append(res.get("confidence", normalized))
            latencies.append(res.get("latency", 1.5))  # default 1.5s if unknown

        # Active Index on 0–30 scale
        active_ratio = weighted_sum / total_weight if total_weight > 0 else 0.0
        active_index = round(active_ratio * 30.0, 1)
        active_index = max(0.0, min(30.0, active_index))

        # ── Composite Active Confidence ────────────────────────────────────────
        # 1. Domain Consistency (60% weight): low variance = reliable
        variance = float(np.var(domain_scores_normalized))
        consistency = float(np.clip(1.0 - variance, 0.0, 1.0))

        # 2. ASR Confidence (20% weight): avg keyword hit ratio
        avg_asr_conf = float(np.clip(np.mean(asr_confidences), 0.0, 1.0))

        # 3. Latency Quality (20% weight): avg latency normalized to [0,1]
        #    Typical ASR takes 0.5–4s. Cap at 6s.
        avg_latency = float(np.clip(np.mean(latencies), 0.0, 6.0))
        latency_quality = float(1.0 - (avg_latency / 6.0))

        active_confidence = round(
            0.6 * consistency + 0.2 * avg_asr_conf + 0.2 * latency_quality,
            3
        )
        active_confidence = float(np.clip(active_confidence, 0.05, 1.0))

        print(f"[TEST_ENGINE] Active Index: {active_index}/30 | "
              f"Conf: {active_confidence:.3f} "
              f"(consistency={consistency:.2f}, asr={avg_asr_conf:.2f}, latency_q={latency_quality:.2f})")
        return active_index, active_confidence

    def detect_failure_modes(self, results):
        """
        Inspects task metadata for signs of poor-quality assessments.
        Returns a list of clinical warning flags.
        """
        flags = []
        asr_errors = [k for k, v in results.items() if v.get("asr_error")]
        low_asr_tasks = [k for k, v in results.items() if v.get("confidence", 1.0) < 0.2 and not v.get("asr_error")]
        high_latency_tasks = [k for k, v in results.items() if v.get("latency", 0) > 4.0]
        blank_responses = [k for k, v in results.items() if v.get("score", -1) == 0 and v.get("transcript", "asr error") == ""]

        if asr_errors:
            flags.append({"code": "ASR_FAILURE", "severity": "critical",
                          "message": f"ASR failed on {len(asr_errors)} task(s). Results may be unreliable."})
        if len(low_asr_tasks) > 2:
            flags.append({"code": "LOW_AUDIO_QUALITY", "severity": "warning",
                          "message": "Low keyword detection across multiple tasks. Check microphone quality."})
        if len(high_latency_tasks) > 1:
            flags.append({"code": "DELAYED_RESPONSES", "severity": "info",
                          "message": "Elevated response latency detected. May reflect processing slowdown or fatigue."})
        if blank_responses:
            flags.append({"code": "INCOMPLETE_RESPONSES", "severity": "warning",
                          "message": f"No response captured for {len(blank_responses)} task(s). Encourage re-assessment."})
        return flags

    def generate_clinical_narrative(self, results):
        """
        Produces domain-specific clinical insights from active assessment performance.
        """
        notes = []
        def norm(key):
            res = results.get(key, {})
            task = self.TASKS.get(key)
            if task and res:
                return res.get("score", 0) / task["points"]
            return None

        mem = norm("memory"); rec = norm("recall"); sto = norm("story_recall")
        flu = norm("fluency"); flu_ph = norm("fluency_phonemic")
        exe = norm("executive_trail"); exe_ab = norm("executive_abstract")
        att = norm("attention_digits"); att_s7 = norm("attention_serial7")
        vis = norm("visuospatial_spatial"); vis_cl = norm("visuospatial_clock")
        lan = norm("language_repeat"); lan_nm = norm("language_naming")
        ori = norm("orientation_time"); ori_pl = norm("orientation_place")

        # Average across 2 tests per domain where both are available
        def avg(*vals): 
            valid = [v for v in vals if v is not None]
            return sum(valid) / len(valid) if valid else None

        mem_avg = avg(mem, sto)
        rec_avg = rec
        flu_avg = avg(flu, flu_ph)
        exe_avg = avg(exe, exe_ab)
        att_avg = avg(att, att_s7)
        vis_avg = avg(vis, vis_cl)
        lan_avg = avg(lan, lan_nm)
        ori_avg = avg(ori, ori_pl)

        # ── Memory ───────────────────────────────────────────────────────────────
        if rec_avg is not None and rec_avg < 0.34:
            notes.append("🔴 Severely impaired delayed recall (< 34%) — strong indicator of hippocampal atrophy consistent with Alzheimer's disease.")
        elif rec_avg is not None and rec_avg < 0.67:
            notes.append("🟡 Reduced delayed recall — possible hippocampal vulnerability. Recommend 6-month longitudinal monitoring.")
        if sto is not None and sto < 0.5:
            notes.append("🔴 Story recall deficit — impaired narrative memory encoding suggests medial temporal dysfunction.")

        # ── Semantic & Phonemic Fluency ──────────────────────────────────────────
        if flu_avg is not None and flu_avg < 0.4:
            notes.append("🔴 Combined fluency impairment (semantic + phonemic) — consistent with fronto-temporal decline and reduced lexical access.")
        elif flu is not None and flu < 0.5:
            notes.append("🔴 Semantic fluency impairment — consistent with left temporal and executive dysfunction.")
        if flu_ph is not None and flu_ph < 0.4:
            notes.append("🟡 Phonemic fluency below threshold — may indicate reduced phonological processing speed.")

        # ── Executive Function ───────────────────────────────────────────────────
        if exe_avg is not None and exe_avg < 0.5:
            notes.append("🔴 Executive dysfunction confirmed across trail making and abstract reasoning — frontal lobe compromise likely.")
        elif exe is not None and exe < 0.6:
            notes.append("🔴 Set-shifting difficulty (Trail Making) — indicates frontal executive function compromise.")
        if exe_ab is not None and exe_ab < 0.5:
            notes.append("🟡 Abstract reasoning deficit — reduced ability to identify categorical similarities (banana/orange).")

        # ── Attention ────────────────────────────────────────────────────────────
        if att_avg is not None and att_avg < 0.5:
            notes.append("🔴 Combined attentional deficit (digit span + serial 7s) — working memory and sustained attention both compromised.")
        elif att is not None and att < 0.6:
            notes.append("🟡 Reduced digit span accuracy — working memory and attentional control may be affected.")
        if att_s7 is not None and att_s7 < 0.4:
            notes.append("🟡 Serial 7s impairment — difficulty with sustained mental arithmetic suggests prefrontal vulnerability.")

        # ── Visuospatial ─────────────────────────────────────────────────────────
        if vis_avg is not None and vis_avg < 0.5:
            notes.append("🔴 Visuospatial impairment (spatial reasoning + object description) — possible parietal lobe involvement.")
        elif vis is not None and vis < 1.0:
            notes.append("🟡 Spatial reasoning deficit observed. May indicate parietal lobe involvement.")
        if vis_cl is not None and vis_cl < 0.4:
            notes.append("🟡 Impaired clock description — difficulty with structured object visualization.")

        # ── Language ─────────────────────────────────────────────────────────────
        if lan_avg is not None and lan_avg < 0.5:
            notes.append("🔴 Language impairment across repetition and naming — possible left hemisphere dysfunction.")
        elif lan is not None and lan < 0.6:
            notes.append("🟡 Sentence repetition errors noted — may reflect phonological processing difficulties.")
        if lan_nm is not None and lan_nm < 0.5:
            notes.append("🟡 Object naming difficulties — anomia may reflect temporal lobe lexical retrieval failure.")

        # ── Orientation ──────────────────────────────────────────────────────────
        if ori_avg is not None and ori_avg < 0.5:
            notes.append("🔴 Disorientation in both time and place — suggests moderate-to-severe global cognitive impairment.")
        elif ori is not None and ori < 0.67:
            notes.append("🔴 Temporal disorientation detected — suggests moderate cognitive impairment.")
        if ori_pl is not None and ori_pl < 0.34:
            notes.append("🔴 Place disorientation — patient unable to identify current location. High concern for advanced dementia.")

        if not notes:
            notes.append("🟢 Active domain performance within normal limits across all 7 assessed domains (14 tasks).")

        return notes

test_engine = ActiveTestEngine()
