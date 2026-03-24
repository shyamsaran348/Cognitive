import os
from importlib import import_module
import json

# Lazily import the feature extractor for Whisper transcription
spec = os.path.join(os.getcwd(), "03_feature_extractor.py")
extractor = import_module("03_feature_extractor")

class ActiveTestEngine:
    """
    Orchestrates prompted cognitive tasks and scores them using Whisper and keywords.
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
            "keywords": ["dog", "cat", "bird", "lion", "tiger", "elephant", "cow", "pig", "sheep", "horse", "snake", "fish", "monkey", "bear", "rabbit", "deer", "wolf", "fox", "frog", "turtle"],
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
        Transcribes the response and calculates a domain score.
        """
        if task_key not in self.TASKS:
            return 0, ""

        task = self.TASKS[task_key]
        
        # 1. Transcribe with Whisper
        print(f"[TEST_ENGINE] Transcribing response for task: {task_key}")
        try:
            _, transcript = extractor.extract_whisper(audio_path, transcribe=True)
            transcript = transcript.lower()
        except Exception as e:
            print(f"[ERROR] ASR Failed: {e}")
            return 0, "ASR Error"

        # 2. Fuzzy Keyword Matching
        match_count = 0
        found_keywords = []
        for kw in task["keywords"]:
            if kw in transcript:
                match_count += 1
                found_keywords.append(kw)

        # Fluency edge case: count all animal mentions
        if task["type"] == "fluency":
            # For hackathon, we look for any animal keyword. Real app would use a smarter list.
            score = min(task["points"], match_count)
        else:
            score = min(task["points"], match_count)

        print(f"[TEST_ENGINE] Task: {task_key} | Score: {score}/{task['points']} | Matches: {found_keywords}")
        return score, transcript

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
        Normalizes 7-domain active scores into an MMSE-equivalent scale (0-30).
        Total Possible: 3 (Mem) + 5 (Lang) + 10 (Flu) + 5 (Exec) + 5 (Attn) + 3 (Visuo) + 3 (Ori) + 3 (Recall) = 37 points
        """
        if not results: return 30.0
        
        raw_score = 0
        domain_weights = {
            "memory": 1.0, "recall": 2.0,     # Hippocampal proxy (High weight)
            "executive": 1.5, "fluency": 1.0, # Frontal proxy (High weight)
            "attention": 1.0, "language": 1.0, 
            "visuospatial": 1.0, "orientation": 1.0
        }
        
        weighted_sum = 0
        max_weighted = 0
        
        for key, task in self.TASKS.items():
            res = results.get(key, {})
            score = res.get("score", 0)
            weight = domain_weights.get(task["type"], 1.0)
            weighted_sum += score * weight
            max_weighted += task["points"] * weight
            
        # Scale to 30
        final_index = (weighted_sum / max_weighted) * 30.0
        final_index = max(0.0, min(30.0, round(final_index, 1)))
        
        print(f"[TEST_ENGINE] 7-Domain Active Index: {final_index}/30.0 (Raw Weighted: {weighted_sum}/{max_weighted})")
        return final_index

test_engine = ActiveTestEngine()
