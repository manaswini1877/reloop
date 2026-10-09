# Test Photos

Place test images in this folder for use with `test_bedrock.py`.

## Naming Convention

Use descriptive, lowercase filenames with underscores:

```
<item>_<condition_or_defect>.<ext>
```

Examples: `power_bank_swollen.jpg`, `charger_damaged.png`, `laptop_battery_good.jpeg`

## Expected Routes by Photo Type

| Photo description              | Expected route | Why                                                        |
| ------------------------------ | -------------- | ---------------------------------------------------------- |
| Swollen / bulging battery      | **hazard**     | Swollen battery → always hazard                            |
| Damaged battery (leaking, etc) | **hazard**     | Damaged battery → battery_risk high → hazard               |
| Blurry photo with battery      | **hazard**     | Low confidence (< 0.6) + visible battery → hazard          |
| Damaged item, no battery       | **repair**     | Repairable, no battery danger                              |
| Worn item, no battery          | **repair**     | Still usable with minor repair                             |
| Good item, no battery risk     | **recycle**    | Nothing to repair, safe to recycle                         |
| Unrecognisable / not e-waste   | **hazard**     | Low confidence; if battery possible → hazard (safe default)|

## Adding Photos

1. Drop `.jpg`, `.jpeg`, or `.png` files here.
2. Run a single image:
   ```
   python ai/scripts/test_bedrock.py ai/test_photos/power_bank_swollen.jpg
   ```
3. Run all images in this folder:
   ```
   python ai/scripts/test_bedrock.py --all
   ```
