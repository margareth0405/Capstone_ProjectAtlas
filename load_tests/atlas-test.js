import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";

const error429 = new Counter("errors_429");
const error409 = new Counter("errors_409");
const serverErrors = new Counter("server_errors");

export const options = {
  stages: [
    { duration: "10s", target: 1 },
    { duration: "20s", target: 10 },
    { duration: "30s", target: 32 },
    { duration: "30s", target: 32 },
    { duration: "10s", target: 0 },
  ],

  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
    errors_429: ["count==0"],
    errors_409: ["count==0"],
  },
};

const BASE_URL = (
  __ENV.BASE_URL || "https://atlas-repository.onrender.com"
).replace(/\/+$/, "");

export default function () {
  const response = http.get(`${BASE_URL}/`);

  if (response.status === 429) {
    error429.add(1);
  }

  if (response.status === 409) {
    error409.add(1);
  }

  if (response.status >= 500) {
    serverErrors.add(1);
  }

  check(response, {
    "website responded successfully": (r) => r.status >= 200 && r.status < 400,

    "no 429 Too Many Requests": (r) => r.status !== 429,

    "no 409 Conflict": (r) => r.status !== 409,

    "response below 2 seconds": (r) => r.timings.duration < 2000,
  });

  sleep(1);
}
