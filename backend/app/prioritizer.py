"""Alert Prioritization and Debouncing module for SeeForMe."""
import logging
import time
from typing import List, Dict, Any, Tuple
from backend.app.config import settings

logger = logging.getLogger(__name__)

class AlertPrioritizer:
    def __init__(self):
        # Keeps track of recent alerts: key -> {timestamp, last_distance, bearing}
        # Key is typically f"{class_name}_{bearing}"
        self.recent_alerts: Dict[str, Dict[str, Any]] = {}
        self.cooldown_sec = settings.DEBOUNCE_COOLDOWN_SEC
        self.distance_threshold = settings.DISTANCE_CHANGE_THRESHOLD_M

    def _calculate_urgency(self, obj: Dict[str, Any]) -> float:
        """Computes an urgency score for a detected object."""
        dist = obj.get("estimated_meters", 10.0)
        cls_name = obj.get("class_name", "object")
        in_corridor = obj.get("in_corridor", False)

        # 1. Proximity factor (closer = exponentially more urgent)
        if dist <= 1.2:
            proximity_score = 5.0
        elif dist <= 2.5:
            proximity_score = 3.5
        elif dist <= 4.0:
            proximity_score = 2.0
        else:
            proximity_score = 0.8

        # 2. Path Corridor factor (obstacles in path require immediate avoidance)
        corridor_score = 2.5 if in_corridor else 0.5

        # 3. Hazard Type factor
        hazard_weight = settings.HAZARD_BASE_URGENCY.get(cls_name, 0.3)

        total_score = (proximity_score * 1.5) + (corridor_score * 1.2) + (hazard_weight * 2.0)
        return round(total_score, 2)

    def _should_debounce(self, key: str, current_dist: float) -> bool:
        """
        Returns True if the alert should be suppressed due to recent announcement,
        unless the distance has critically decreased.
        """
        now = time.time()
        if key not in self.recent_alerts:
            return False

        last_record = self.recent_alerts[key]
        time_diff = now - last_record["timestamp"]
        dist_diff = last_record["distance"] - current_dist  # positive if object moved closer

        # If it significantly moved closer (e.g. approaching car/person), re-alert immediately
        if dist_diff >= self.distance_threshold:
            return False

        # If cooldown period has not elapsed, debounce
        if time_diff < self.cooldown_sec:
            return True

        return False

    def _record_alert(self, key: str, dist: float, bearing: str):
        self.recent_alerts[key] = {
            "timestamp": time.time(),
            "distance": dist,
            "bearing": bearing
        }

    def format_alert_phrase(self, obj: Dict[str, Any]) -> str:
        """Generates a natural-sounding concise spoken alert."""
        cls_name = obj["class_name"].capitalize()
        dist_phrase = obj["distance_phrase"]
        bearing = obj["bearing"]

        if obj["estimated_meters"] <= 1.5 and obj["in_corridor"]:
            return f"Caution: {cls_name}, {dist_phrase}, {bearing}."
        else:
            return f"{cls_name}, {dist_phrase}, {bearing}."

    def process(self, fused_objects: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Ranks objects by urgency and generates debounced spoken alerts.
        Returns:
            ranked_objects: list of all objects sorted by urgency.
            spoken_alerts: list of 1-2 alert strings to vocalize right now.
        """
        if not fused_objects:
            return [], []

        # Calculate urgency for each object
        for obj in fused_objects:
            obj["urgency_score"] = self._calculate_urgency(obj)

        # Sort by urgency descending
        ranked_objects = sorted(fused_objects, key=lambda x: x["urgency_score"], reverse=True)

        spoken_alerts = []
        for obj in ranked_objects:
            # We only generate speech for objects within a sensible alert horizon (e.g. <= 6m)
            if obj["estimated_meters"] > 6.0:
                continue

            alert_key = f"{obj['class_name']}_{obj['bearing']}"
            if not self._should_debounce(alert_key, obj["estimated_meters"]):
                phrase = self.format_alert_phrase(obj)
                spoken_alerts.append(phrase)
                self._record_alert(alert_key, obj["estimated_meters"], obj["bearing"])

            if len(spoken_alerts) >= settings.MAX_ALERTS_PER_CYCLE:
                break

        return ranked_objects, spoken_alerts
