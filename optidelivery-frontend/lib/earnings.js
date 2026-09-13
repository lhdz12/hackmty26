const KEY = "optidelivery_completed_deliveries";

export function getCompletedDeliveries() {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(window.localStorage.getItem(KEY) || "[]");
  } catch (err) {
    return [];
  }
}

export function addCompletedDelivery(entry) {
  if (typeof window === "undefined") return;
  const current = getCompletedDeliveries();
  const next = [...current, entry];
  window.localStorage.setItem(KEY, JSON.stringify(next));
}
