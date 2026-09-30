import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate } from "k6/metrics";

import {
  baseUrl,
  extractRepositoryItemId,
  guardTarget,
  maximumVUs,
  recordStatus,
  selectedProfile,
  stagesFor,
} from "./config.js";

const error403 = new Counter("errors_403");
const error404 = new Counter("errors_404");
const error429 = new Counter("errors_429");
const loginFailures = new Counter("login_failures");
const serverErrors = new Counter("server_errors");
const pageFailures = new Rate("page_failures");

const PROFILE = selectedProfile();
const BASE_URL = baseUrl();
const USER_PREFIX = __ENV.TEST_USER_PREFIX || "loadtest";
const USER_DOMAIN = __ENV.TEST_USER_DOMAIN || "example.com";
const USER_COUNT = Number.parseInt(__ENV.TEST_USER_COUNT || "100", 10);
const PASSWORD = __ENV.TEST_PASSWORD || "";
const ROLE = __ENV.TEST_ROLE === "teacher" ? "teacher" : "student";
const METRICS = { error403, error404, error429, serverErrors };

export const options = {
  stages: stagesFor(PROFILE),
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
    login_failures: ["count==0"],
    errors_403: ["count==0"],
    errors_404: ["count==0"],
    errors_429: ["count==0"],
    server_errors: ["count==0"],
    page_failures: ["rate<0.01"],
  },
};

export function setup() {
  guardTarget(BASE_URL);
  if (!PASSWORD) {
    throw new Error("TEST_PASSWORD is required for authenticated load tests.");
  }
  if (!Number.isInteger(USER_COUNT) || USER_COUNT < 1) {
    throw new Error("TEST_USER_COUNT must be a positive integer.");
  }
  if (
    USER_COUNT < maximumVUs(PROFILE) &&
    __ENV.ALLOW_SHARED_ACCOUNTS !== "true"
  ) {
    throw new Error(
      `The ${PROFILE} profile needs at least ${maximumVUs(PROFILE)} accounts. ` +
        "Create a matching pool or explicitly set ALLOW_SHARED_ACCOUNTS=true.",
    );
  }
}

function testPage(path, name) {
  const response = http.get(`${BASE_URL}${path}`, {
    redirects: 0,
    tags: { page: name },
  });
  recordStatus(response, METRICS);
  const success = check(response, {
    [`${name}: status 200`]: (r) => r.status === 200,
    [`${name}: response below 2 seconds`]: (r) => r.timings.duration < 2000,
    [`${name}: no server error`]: (r) => r.status < 500,
  });
  pageFailures.add(!success);
  return response;
}

function csrfTokenFrom(response) {
  return response
    .html()
    .find('input[name="csrfmiddlewaretoken"]')
    .first()
    .attr("value");
}

function accountEmail() {
  const accountNumber = ((__VU - 1) % USER_COUNT) + 1;
  return `${USER_PREFIX}${String(accountNumber).padStart(3, "0")}@${USER_DOMAIN}`;
}

function login() {
  const jar = http.cookieJar();
  jar.clear(BASE_URL);

  const loginUrl = `${BASE_URL}/login/?role=${ROLE}`;
  const loginPage = http.get(loginUrl, {
    redirects: 0,
    tags: { page: "Login Page" },
  });
  recordStatus(loginPage, METRICS);
  const pageLoaded = check(loginPage, {
    "login page loads": (r) => r.status === 200,
  });
  const csrfToken = pageLoaded ? csrfTokenFrom(loginPage) : null;
  if (!csrfToken) {
    loginFailures.add(1);
    pageFailures.add(true);
    return false;
  }

  const loginResponse = http.post(
    `${BASE_URL}/login/`,
    {
      csrfmiddlewaretoken: csrfToken,
      email: accountEmail(),
      password: PASSWORD,
      role: ROLE,
      privacy_consent: "1",
    },
    {
      headers: { Referer: loginUrl },
      redirects: 0,
      tags: { page: "Login Submit" },
    },
  );
  recordStatus(loginResponse, METRICS);
  const loggedIn = check(loginResponse, {
    "login redirects after authentication": (r) => r.status === 302,
    "login redirects to dashboard": (r) =>
      (r.headers.Location || "").includes("/dashboard/"),
  });
  if (!loggedIn) {
    loginFailures.add(1);
    pageFailures.add(true);
  }
  return loggedIn;
}

function logout() {
  const jar = http.cookieJar();
  const cookies = jar.cookiesForURL(BASE_URL);
  const csrfToken = cookies.csrftoken && cookies.csrftoken[0];
  if (csrfToken) {
    const response = http.post(`${BASE_URL}/logout/`, null, {
      headers: {
        Referer: `${BASE_URL}/dashboard/`,
        "X-CSRFToken": csrfToken,
      },
      redirects: 0,
      tags: { page: "Logout" },
    });
    recordStatus(response, METRICS);
  }
  jar.clear(BASE_URL);
}

export default function () {
  if (!login()) {
    sleep(1);
    return;
  }

  testPage("/dashboard/", "Student Dashboard");
  sleep(2);

  const repository = testPage("/repository/", "Repository");
  sleep(3);

  testPage("/repository/?q=research", "Repository Search");
  sleep(2);

  const itemId = extractRepositoryItemId(repository);
  if (itemId) {
    testPage(`/repository/${itemId}/`, "Resource Details");
    sleep(2);

    if (__ENV.TEST_RESOURCE_READER === "true") {
      testPage(
        `/repository/${itemId}/resource-abstract/read/`,
        "Resource Abstract Reader",
      );
      sleep(2);
    }
  }

  testPage("/favorites/", "Bookmarks");
  sleep(2);
  testPage("/announcements/", "Announcements");
  sleep(2);

  logout();
}
