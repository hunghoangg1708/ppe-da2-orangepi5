"""Small scenarios covering wrong-person assignment and duplicate alerts."""
import unittest

from app.logic import Detection, EventGate, Person, associate


class AssociationTests(unittest.TestCase):
    def test_ppe_is_assigned_to_the_correct_person(self):
        people = [
            Person(1, (0, 0, 100, 300), 0.9),
            Person(2, (150, 0, 250, 300), 0.9),
        ]
        detections = [
            Detection((15, 0, 80, 75), "NoHelmet", 0.8),
            Detection((165, 85, 235, 210), "Vest", 0.8),
            Detection((290, 150, 350, 220), "Vest", 0.9),  # PPE-like object outside people
        ]
        state = associate(people, detections)
        self.assertEqual(state[1], {"helmet": "violation", "vest": "unknown"})
        self.assertEqual(state[2], {"helmet": "unknown", "vest": "compliant"})

    def test_conflicting_ppe_labels_are_not_used_as_evidence(self):
        person = Person(1, (0, 0, 100, 300), 0.9)
        detections = [
            Detection((10, 0, 70, 60), "Helmet", 0.8),
            Detection((15, 0, 80, 70), "NoHelmet", 0.7),
        ]
        self.assertEqual(associate([person], detections)[1]["helmet"], "unknown")

    def test_ambiguous_overlap_between_people_is_ignored(self):
        people = [Person(1, (0, 0, 100, 300), 0.9),
                  Person(2, (10, 0, 110, 300), 0.9)]
        result = associate(people, [Detection((30, 80, 80, 170), "NoVest", 0.9)])
        self.assertEqual(result[1]["vest"], "unknown")
        self.assertEqual(result[2]["vest"], "unknown")


class EventGateTests(unittest.TestCase):
    def test_repeated_negative_evidence_emits_only_once(self):
        gate = EventGate(window=5, confirm_frames=3)
        self.assertFalse(gate.update(1, "helmet", "violation"))
        self.assertFalse(gate.update(1, "helmet", "unknown"))
        self.assertFalse(gate.update(1, "helmet", "violation"))
        self.assertTrue(gate.update(1, "helmet", "violation"))
        self.assertFalse(gate.update(1, "helmet", "violation"))

    def test_compliant_evidence_blocks_early_alert(self):
        gate = EventGate(window=5, confirm_frames=3)
        for observation in ("violation", "violation", "compliant", "violation"):
            self.assertFalse(gate.update(1, "vest", observation))

    def test_tracker_id_change_does_not_repeat_same_spatial_event(self):
        gate = EventGate(window=3, confirm_frames=3)
        first = (100, 100, 200, 300)
        second = (105, 102, 205, 302)
        for frame in range(2):
            self.assertFalse(gate.update(1, "helmet", "violation", first, frame, 300))
        self.assertTrue(gate.update(1, "helmet", "violation", first, 2, 300))
        for frame in range(3, 5):
            self.assertFalse(gate.update(2, "helmet", "violation", second, frame, 300))
        self.assertFalse(gate.update(2, "helmet", "violation", second, 5, 300))


if __name__ == "__main__":
    unittest.main()
