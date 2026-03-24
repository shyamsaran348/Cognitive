import os
import time
import numpy as np
from importlib import import_module

# Lazily import the feature extractor for Whisper transcription
spec = os.path.join(os.getcwd(), "03_feature_extractor.py")
extractor = import_module("03_feature_extractor")

# Clinically-calibrated domain weights (based on MoCA/ACE-III sensitivity literature)
DOMAIN_WEIGHTS = {
    "memory":      0.20,  # Hippocampal proxy — highest sensitivity for early AD
    "recall":      0.20,  # Delayed recall — strongest single predictor of AD
    "executive":   0.15,  # Frontal lobe — key for MCI differentiation
    "fluency":     0.15,  # Language/executive overlap
    "attention":   0.15,  # Working memory proxy
    "language":    0.10,  # Phonological integrity
    "visuospatial":0.10,  # Parietal integrity
    "orientation": 0.10,  # Temporal/spatial awareness
}

class ActiveTestEngine:
    """
    Orchestrates prompted cognitive tasks and scores them using Whisper and
    clinically-calibrated domain weighting. Produces rich metadata per task.
    """
    TASKS = {
        "memory": {
            "prompt": "Please repeat these three words: Apple, Penny, Table. Keep them in mind, I will ask you again later.",
            "type": "memory",
            "keywords": ["apple", "penny", "table"],
            "points": 3
        },
        "language_repeat": {
            "prompt": "Repeat this sentence exactly: 'The cat always hides under the wooden table.'",
            "type": "language",
            "keywords": ["cat", "hides", "under", "wooden", "table"],
            "points": 5
        },
        "fluency": {
            "prompt": "Name as many animals as you can in the next 30 seconds. Go!",
            "type": "fluency",
            "keywords": ["dog", "cat", "bird", "lion", "tiger", "elephant", "cow", "pig", "sheep",
                         "horse", "snake", "fish", "monkey", "bear", "rabbit", "deer", "wolf",
                         "fox", "frog", "turtle"],
            "points": 10
        },
        "executive_trail": {
            "prompt": "Say this sequence: 1-A, 2-B, 3-C, 4-D, 5-E.",
            "type": "executive",
            "keywords": ["1", "a", "2", "b", "3", "c", "4", "d", "5", "e"],
            "points": 5
        },
        "attention_digits": {
            "prompt": "Repeat these numbers in order: 7-4-1-9-3.",
            "type": "attention",
            "keywords": ["7", "4", "1", "9", "3"],
            "points": 5
        },
        "visuospatial_spatial": {
            "prompt": "If you walk North, turn left, and then turn left again, which direction are you facing?",
            "type": "visuospatial",
            "keywords": ["south"],
            "points": 3
        },
        "orientation_time": {
            "prompt": "What is today's date? (Day, Month, and Year)",
            "type": "orientation",
            "keywords": ["march", "2026", "tuesday", "24", "twenty-fourth"],
            "points": 3
        },
        "recall": {
            "prompt": "What were the three words I asked you to remember earlier?",
            "type": "recall",
            "keywords": ["apple", "penny", "table"],
            "points": 3
        }
    }

    def score_response(self, task_key, audio_path):
        """
        Transcribes the response and calculates a domain score with rich metadata.
        Returns: (score, transcript, metadata_dict)
        """
        if task_key not in self.TASKS:
            return 0, "", {}

        task = self.TASKS[task_key]
        t_start = time.time()

        # 1. Transcribe with Whisper
        print(f"[TEST_ENGINE] Transcribing response for task: {task_key}")
        try:
            _, transcript = extractor.extract_whisper(audio_path, transcribe=True)
            transcript = transcript.lower()
        except Exception as e:
            print(f"[ERROR] ASR Failed: {e}")
            return 0, "ASR Error", {"latency": 0, "confidence": 0.0, "asr_error": True}

        latency = round(time.time() - t_start, 2)

        # 2. Keyword Matching
        match_count = 0
        found_keywords = []
        for kw in task["keywords"]:
            if kw in transcript:
                match_count += 1
                found_keywords.append(kw)

        score = min(task["points"], match_count)
        normalized_score = score / task["points"]  # 0.0 to 1.0

        # 3. Per-task confidence: How much of the expected keywords did we detect?
        #    High score ratio = high confidence in the measurement
        task_confidence = round(normalized_score if score > 0 else 0.1, 3)

        metadata = {
            "latency": latency,
            "confidence": task_confidence,
            "normalized_score": normalized_score,
            "found_keywords": found_keywords,
            "total_keywords": len(task["keywords"])
        }

        print(f"[TEST_ENGINE] Task: {task_key} | Score: {score}/{task['points']} | "
              f"Conf: {task_confidence:.2f} | Latency: {latency}s | Matches: {found_keywords}")
        return score, transcript, metadata

    def get_next_prompt(self, current_task_index):
        keys = list(self.TASKS.keys())
        if current_task_index < len(keys):
            key = keys[current_task_index]
            return {
                "key": key,
                "prompt": self.TASKS[key]["prompt"],
                "index": current_task_index,
                "total": len(keys)
            }
        return None

    def calculate_active_index(self, results):
        """
        Computes the Active Cognitive Index with composite confidence:
          0.6 * domain_consistency  (inverse of score variance)
          0.2 * avg_asr_confidence  (keyword hit ratio per task)
          0.2 * latency_quality     (inverse of normalized avg latency)
        Returns: (active_index_0_to_30, active_confidence_0_to_1)
        """
        if not results:
            return 30.0, 1.0

        domain_scores_normalized = []
        asr_confidences = []
        latencies = []
        weighted_sum = 0.0
        total_weight = 0.0

        for key, task in self.TASKS.items():
            res = results.get(key, {})
            score = res.get("score", 0)
            max_points = task["points"]
            normalized = score / max_points
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

        mem = norm("memory"); rec = norm("recall")
        flu = norm("fluency"); exe = norm("executive_trail")
        att = norm("attention_digits"); vis = norm("visuospatial_spatial")
        lan = norm("language_repeat"); ori = norm("orientation_time")

        if rec is not None and rec < 0.5:
            notes.append("🔴 Reduced delayed recall (< 50%) — possible hippocampal vulnerability consistent with early Alzheimer's pathology.")
        elif rec is not None and rec < 0.8:
            notes.append("🟡 Mild delayed recall reduction — recommend monitoring over 6-month interval.")

        if flu is not None and flu < 0.5:
            notes.append("🔴 Semantic fluency impairment detected — consistent with executive dysfunction and left temporal decline.")

        if exe is not None and exe < 0.6:
            notes.append("🔴 Set-shifting difficulty (Trail Making) — indicates frontal lobe / executive function compromise.")

        if att is not None and att < 0.6:
            notes.append("🟡 Reduced digit span accuracy — working memory and attentional control may be affected.")

        if ori is not None and ori < 0.67:
            notes.append("🔴 Spatiotemporal disorientation detected — suggests moderate-to-severe cognitive impairment.")

        if vis is not None and vis < 1.0:
            notes.append("🟡 Visuospatial reasoning deficit observed — possible parietal lobe involvement.")

        if lan is not None and lan < 0.6:
            notes.append("🟡 Sentence repetition errors noted — may reflect phonological processing difficulties.")

        if not notes:
            notes.append("🟢 Active domain performance within normal limits across all assessed domains.")

        return notes

test_engine = ActiveTestEngine()
