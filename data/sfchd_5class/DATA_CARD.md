# SFCHD five-class derivative

This dataset is generated from the original SFCHD YOLO files. No raw image or
label is changed. The output class order is:

| ID | Class | Raw SFCHD ID |
|---:|---|---:|
| 0 | `person` | 0 |
| 1 | `helmet` | 1 |
| 2 | `safety_clothes` | 3 |
| 3 | `self_clothes` | 2 |
| 4 | `head` | 4 |

Raw classes `blur_head` (5) and `blur_clothes` (6) are excluded from the labels.
Images are linked from the raw source. The split uses the same sorted filenames,
`random.Random(42)` shuffle and 80/10/10 slicing as `prepare_sfchd.py`, so it
matches the previous seven-class split when the same raw files are provided.

Run from the repository root after placing the source at `data/sfchd/raw/`:

```bash
python scripts/data/prepare_sfchd_5class.py
```

Alternatively, specify `--raw /path/to/sfchd/raw`. The source directory must
contain `classes.txt`, `images/` and `labels/`. The script refuses to overwrite
existing output. On systems without symlink permission, `--image-mode auto`
tries hard links on the same filesystem. It never silently copies the image set.

The output includes `dataset.yaml`, class and split lists, and `manifest.json`
with class counts and split fingerprints. Keep the split fixed for all baseline
and proposed-model comparisons. This split is **not** the original paper's
train/test partition, so paper mAP values cannot be compared directly.

For the download previously audited in the project guide, the expected output
is 12,372 images (9,897 train / 1,237 val / 1,238 test) and 48,096 retained
boxes. The expected five-class totals are `person` 17,009, `helmet` 14,297,
`safety_clothes` 14,812, `self_clothes` 779, and `head` 1,199. A different
download may have different counts; inspect the generated manifest and sample
labels before training. In particular, inspect the scarce `self_clothes`
examples in every split.

Source: [SFCHD paper](../../references/papers/sfchd_scale_2023yu.pdf)
and [original data card](../sfchd/DATA_CARD.md).
