// Mock items representing realistic campus e-waste for Phase 1 testing.
// Follows the ReLoop Contract exactly. Sorted newest first by created_at.

export const MOCK_ITEMS = [
  {
    id: "9f4d1e2a-7b3c-4d5e-8f90-1a2b3c4d5e6f",
    image_key: "uploads/9f4d1e2a-7b3c-4d5e-8f90-1a2b3c4d5e6f.jpg",
    created_at: "2026-10-08T08:15:00.000Z",
    item: "Anker 10000mAh Power Bank",
    condition: "damaged",
    battery_risk: "high",
    swollen_battery: true,
    route: "hazard",
    confidence: 0.94,
    reason: "Battery casing shows severe bulging and seam separation; high thermal hazard.",
    safe_steps_en: [
      "Do not plug in, charge, or attempt to power on this device.",
      "Place the device in a bucket of dry sand away from all flammable items.",
      "Notify campus security or staff immediately for hazardous e-waste disposal."
    ],
    safe_steps_te: [
      "ఈ పరికరాన్ని ఛార్జ్ చేయవద్దు లేదా ఆన్ చేయడానికి ప్రయత్నించవద్దు.",
      "దీనిని మండే వస్తువులకు దూరంగా, పొడి ఇసుక ఉన్న పాత్రలో ఉంచండి.",
      "ప్రమాదకర వ్యర్థాల తొలగింపు కోసం వెంటనే క్యాంపస్ సెక్యూరిటీ లేదా సిబ్బందికి సమాచారం ఇవ్వండి."
    ],
    status: "reported"
  },
  {
    id: "e8b2c1d3-4a5f-6e7b-8c9d-0e1f2a3b4c5d",
    image_key: "uploads/e8b2c1d3-4a5f-6e7b-8c9d-0e1f2a3b4c5d.jpg",
    created_at: "2026-10-08T07:45:00.000Z",
    item: "Generic Li-ion Battery Pack",
    condition: "worn",
    battery_risk: "medium",
    swollen_battery: false,
    route: "hazard",
    confidence: 0.45,
    reason: "Unclear battery labeling with visible wear; routed to hazard for staff verification.",
    safe_steps_en: [
      "Handle with care and avoid dropping, puncturing, or crushing the casing.",
      "Cover the exposed metal connector pins with non-conductive tape.",
      "Place in a cool, ventilated area until verified by campus e-waste staff."
    ],
    safe_steps_te: [
      "జాగ్రత్తగా పట్టుకోండి; కేసింగ్‌ను పగలగొట్టడం లేదా నొక్కడం చేయవద్దు.",
      "బహిర్గతమైన మెటల్ కనెక్టర్ పిన్‌లపై విద్యుత్ నిరోధక టేపును వేయండి.",
      "క్యాంపస్ సిబ్బంది పరిశీలించే వరకు చల్లని, గాలి ఆడే ప్రదేశంలో ఉంచండి."
    ],
    status: "reported"
  },
  {
    id: "b7a6c5d4-3e2f-1a0b-9c8d-7e6f5a4b3c2d",
    image_key: "uploads/b7a6c5d4-3e2f-1a0b-9c8d-7e6f5a4b3c2d.jpg",
    created_at: "2026-10-08T06:30:00.000Z",
    item: "65W USB-C Fast Charger",
    condition: "worn",
    battery_risk: "none",
    swollen_battery: false,
    route: "repair",
    confidence: 0.88,
    reason: "Frayed outer cable sleeve near strain relief; internal wiring and adapter housing intact.",
    safe_steps_en: [
      "Disconnect the charger from the electrical outlet before handling.",
      "Do not bend or yank the frayed cable section to prevent internal short circuits.",
      "Bring to the campus student repair desk for heat-shrink reinforcement."
    ],
    safe_steps_te: [
      "పట్టుకునే ముందు ఛార్జర్‌ను ఎలక్ట్రికల్ సాకెట్ నుండి డిస్‌కనెక్ట్ చేయండి.",
      "షార్ట్ సర్క్యూట్‌లను నివారించడానికి దెబ్బతిన్న కేబుల్‌ను వంచవద్దు లేదా లాగవద్దు.",
      "వైరును భద్రపరచడానికి క్యాంపస్ విద్యార్థి రిపేర్ డెస్క్‌కు తీసుకురండి."
    ],
    status: "reported"
  },
  {
    id: "5d4c3b2a-1f0e-9d8c-7b6a-5e4f3a2b1c0d",
    image_key: "uploads/5d4c3b2a-1f0e-9d8c-7b6a-5e4f3a2b1c0d.jpg",
    created_at: "2026-10-07T14:20:00.000Z",
    item: "Dell USB Membrane Keyboard",
    condition: "damaged",
    battery_risk: "none",
    swollen_battery: false,
    route: "recycle",
    confidence: 0.91,
    reason: "Missing keycaps and cracked casing; no hazardous battery; recyclable ABS plastic and PCB.",
    safe_steps_en: [
      "Unplug the USB cord and coil it neatly around the keyboard body.",
      "Do not dispose of this electronic hardware in general dormitory trash bins.",
      "Deposit directly into the designated blue e-waste bin in the hostel lobby."
    ],
    safe_steps_te: [
      "USB తీగను తొలగించి, కీబోర్డ్ చుట్టూ చక్కగా చుట్టండి.",
      "ఈ ఎలక్ట్రానిక్ పరికరాన్ని సాధారణ హాస్టల్ చెత్త బుట్టలలో పారవేయవద్దు.",
      "హాస్టల్ లాబీలోని కేటాయించిన నీలిరంగు ఇ-వ్యర్థాల బిన్‌లో నేరుగా వేయండి."
    ],
    status: "reported"
  }
];
