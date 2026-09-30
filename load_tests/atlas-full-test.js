import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate } from "k6/metrics";

import {
  baseUrl,
  extractRepositoryItemId,
  guardTarget,
  recordStatus,
  selectedProfile,
  stagesFor,
} from "./config.js";

const error403 = new Counter("errors_403");
const error404 = new Counter("errors_404");
const error429 = new Counter("errors_429");
const serverErrors = new Counter("server_errors");
const pageFailures = new Rate("page_failures");

const PROFILE = selectedProfile();
const BASE_URL = baseUrl();
const METRICS = { error403, error404, error429, serverErrors };

export const options = {
  stages: stagesFor(PROFILE),
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
    errors_403: ["count==0"],
    errors_404: ["count==0"],
    errors_429: ["count==0"],
    server_errors: ["count==0"],
    page_failures: ["rate<0.01"],
  },
};

export function setup() {
  guardTarget(BASE_URL);
}

function testPage(path, name, expectedStatuses = [200]) {
  const response = http.get(`${BASE_URL}${path}`, {
    redirects: 0,
    tags: { page: name },
  });
  recordStatus(response, METRICS);

  const success = check(response, {
    [`${name}: expected status`]: (r) => expectedStatuses.includes(r.status),
    [`${name}: response below 2 seconds`]: (r) => r.timings.duration < 2000,
    [`${name}: no server error`]: (r) => r.status < 500,
  });
  pageFailures.add(!success);
  return response;
}

export default function () {
  testPage("/", "Homepage");
  sleep(2);

  const repository = testPage("/repository/", "Repository");
  sleep(3);

  const searchTerms = [
    "research",
    "science",
    "english",
    "mathematics",
    "technology",
    "education",
  ];
  const searchTerm = searchTerms[Math.floor(Math.random() * searchTerms.length)];
  testPage(
    `/repository/?q=${encodeURIComponent(searchTerm)}`,
    "Repository Search",
  );
  sleep(2);

  const itemId = extractRepositoryItemId(repository);
  if (itemId) {
    testPage(`/repository/${itemId}/`, "Resource Details");
    sleep(2);
  }

  testPage("/announcements/", "Announcements");
  sleep(2);

  // Anonymous visitors should be redirected to the role-aware login page.
  testPage("/dashboard/", "Dashboard Login Redirect", [302]);
  sleep(2);
}
