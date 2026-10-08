// English UI strings and language helper for ReLoop.
// Telugu is used ONLY for safe steps; all other UI stays English.

export const UI = {
  // Brand & Header
  appName: "ReLoop",
  tagline: "Smart Campus E-Waste Routing",

  // Navigation tabs
  navReport: "Report",
  navItems: "Items",

  // Upload Screen
  uploadTitle: "Report E-Waste",
  uploadDescription: "Snap a photo of old chargers, power banks, batteries, or gadgets. Get immediate safety instructions and drop-off guidance.",
  takePhoto: "Take or choose photo",
  changePhoto: "Change photo",
  analyzeBtn: "Analyze Item",
  analyzingTitle: "Analyzing e-waste...",
  analyzingSubtitle: "Checking for battery swelling, fire hazards, and optimal recycling route.",
  noPhotoSelected: "Please choose or take a photo first.",
  analysisFailed: "Could not analyze the item. Please try again.",
  retryBtn: "Retry",

  // Result Screen
  hazardBanner: "HAZARD - do not put in a bin",
  safeStepsTitle: "Safe Handling Steps",
  langToggleEn: "English",
  langToggleTe: "తెలుగు (Telugu)",
  routeLabel: "Recommended Route",
  conditionLabel: "Condition",
  confidenceLabel: "Confidence",
  batteryRiskLabel: "Battery Risk",
  swollenWarning: "Dangerous swollen battery detected!",
  reasonLabel: "Assessment Reason",
  reportAnotherBtn: "Report Another Item",
  viewAllItemsBtn: "View All Campus Items",

  // Routes
  routes: {
    hazard: {
      name: "HAZARD",
      description: "Critical safety risk. Requires designated hazardous container."
    },
    repair: {
      name: "REPAIR",
      description: "Fixable component. Route to campus repair desk."
    },
    recycle: {
      name: "RECYCLE",
      description: "Safe for standard campus e-waste recycling bins."
    }
  },

  // Admin / Items screen
  adminTitle: "Campus E-Waste List",
  adminSubtitle: "Live feed of reported items from campus hostels.",
  pollStatus: "Live updates active (every 5s)",
  emptyList: "No e-waste items reported yet.",
  tapToView: "Tap any item to see full safe-handling steps."
};

export const SAFE_STEP_LANG = {
  EN: "en",
  TE: "te"
};

/**
 * Returns safe handling steps array based on chosen language.
 * Default is English ('en'), toggleable to Telugu ('te').
 */
export function getSafeSteps(item, lang = SAFE_STEP_LANG.EN) {
  if (!item) return [];
  if (lang === SAFE_STEP_LANG.TE && Array.isArray(item.safe_steps_te)) {
    return item.safe_steps_te;
  }
  return item.safe_steps_en || [];
}
