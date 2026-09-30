import { fail } from "k6";

const PROFILES = {
  smoke: [
    { duration: "20s", target: 10 },
    { duration: "1m", target: 10 },
    { duration: "20s", target: 0 },
  ],
  normal: [
    { duration: "30s", target: 25 },
    { duration: "1m", target: 25 },
    { duration: "30s", target: 0 },
  ],
  busy: [
    { duration: "30s", target: 25 },
    { duration: "30s", target: 50 },
    { duration: "2m", target: 50 },
    { duration: "30s", target: 0 },
  ],
  peak: [
    { duration: "30s", target: 10 },
    { duration: "30s", target: 25 },
    { duration: "1m", target: 50 },
    { duration: "1m", target: 75 },
    { duration: "1m", target: 100 },
    { duration: "2m", target: 100 },
    { duration: "30s", target: 50 },
    { duration: "30s", target: 0 },
  ],
  stress: [
    { duration: "30s", target: 100 },
    { duration: "1m", target: 125 },
    { duration: "1m", target: 150 },
    { duration: "2m", target: 150 },
    { duration: "30s", target: 0 },
  ],
};

export function selectedProfile() {
  const name = (__ENV.LOAD_PROFILE || "smoke").toLowerCase();
  if (!PROFILES[name]) {
    throw new Error(
      `Unknown LOAD_PROFILE "${name}". Use smoke, normal, busy, peak, or stress.`,
    );
  }
  return name;
}

export function stagesFor(profileName) {
  return PROFILES[profileName];
}

export function maximumVUs(profileName) {
  return Math.max(...PROFILES[profileName].map((stage) => stage.target));
}

export function baseUrl() {
  return (__ENV.BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");
}

export function guardTarget(url) {
  const isLocal = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/i.test(url);
  if (!isLocal && __ENV.ALLOW_REMOTE !== "true") {
    fail(
      "Remote load testing is disabled. Confirm that you own or are authorized " +
        "to test the target, then rerun with ALLOW_REMOTE=true.",
    );
  }
}

export function extractRepositoryItemId(response) {
  if (__ENV.RESOURCE_ID) {
    return __ENV.RESOURCE_ID;
  }
  const match = response.body && response.body.match(/\/repository\/(\d+)\//);
  return match ? match[1] : null;
}

export function recordStatus(response, metrics) {
  if (metrics.error403) metrics.error403.add(response.status === 403 ? 1 : 0);
  if (metrics.error404) metrics.error404.add(response.status === 404 ? 1 : 0);
  if (metrics.error429) metrics.error429.add(response.status === 429 ? 1 : 0);
  if (metrics.serverErrors) metrics.serverErrors.add(response.status >= 500 ? 1 : 0);
}
