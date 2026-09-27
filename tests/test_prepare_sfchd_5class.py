"""Checks for the irreversible class-ID and split decisions in SFCHD prep."""

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "data"))
from prepare_sfchd_5class import RAW_CLASSES, TARGET_CLASSES, prepare  # noqa: E402


class PrepareSFCHD5ClassTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw"
        (self.raw / "images").mkdir(parents=True)
        (self.raw / "labels").mkdir()
        (self.raw / "classes.txt").write_text("\n".join(RAW_CLASSES) + "\n", encoding="utf-8")
        for i in range(10):
            stem = f"frame_{i:02d}"
            (self.raw / "images" / f"{stem}.jpg").write_bytes(b"test-image")
            (self.raw / "labels" / f"{stem}.txt").write_text(
                "0 0.50 0.50 0.20 0.20\n"
                "1 0.50 0.50 0.20 0.20\n"
                "2 0.50 0.50 0.20 0.20\n"
                "3 0.40 0.40 0.20 0.20\n"
                "4 0.50 0.50 0.20 0.20\n"
                "5 0.25 0.25 0.10 0.10\n"
                "6 0.25 0.25 0.10 0.10\n",
                encoding="utf-8",
            )

    def test_class_mapping_and_split_are_stable(self) -> None:
        original_label = (self.raw / "labels" / "frame_00.txt").read_bytes()
        first = prepare(self.raw, self.root / "out_1", image_mode="hardlink")
        second = prepare(self.raw, self.root / "out_2", image_mode="hardlink")

        self.assertEqual(first["classes"], list(TARGET_CLASSES))
        self.assertEqual(first["split_images"], {"train": 8, "val": 1, "test": 1})
        self.assertEqual(first["instances"]["self_clothes"], 10)
        self.assertEqual(first["instances"]["safety_clothes"], 10)
        self.assertEqual(first["split_instances"]["test"]["self_clothes"], 1)
        self.assertEqual(first["split_list_sha256"], second["split_list_sha256"])
        self.assertEqual(first["converted_labels_sha256"], second["converted_labels_sha256"])
        self.assertEqual((self.raw / "labels" / "frame_00.txt").read_bytes(), original_label)

        seen = set()
        for split in ("train", "val", "test"):
            for label in (self.root / "out_1" / "labels" / split).glob("*.txt"):
                self.assertNotIn(label.stem, seen)
                seen.add(label.stem)
                lines = label.read_text(encoding="utf-8").splitlines()
                self.assertEqual([line.split()[0] for line in lines], ["0", "1", "3", "2", "4"])
        self.assertEqual(len(seen), 10)

    def test_rejects_wrong_class_order_before_writing(self) -> None:
        (self.raw / "classes.txt").write_text("helmet\nperson\n", encoding="utf-8")
        output = self.root / "invalid_output"
        with self.assertRaisesRegex(ValueError, "Unexpected raw class order"):
            prepare(self.raw, output, image_mode="hardlink")
        self.assertFalse(output.exists())

    def test_rejects_missing_label_before_writing(self) -> None:
        (self.raw / "labels" / "frame_03.txt").unlink()
        output = self.root / "invalid_output"
        with self.assertRaises(FileNotFoundError):
            prepare(self.raw, output, image_mode="hardlink")
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
