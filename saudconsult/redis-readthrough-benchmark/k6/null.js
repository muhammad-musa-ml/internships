// DRIVER HEADROOM PROBE. Hits the do-nothing endpoint so the load generator's own
// ceiling is measured with the SAME tool, from the SAME place, as the real arms.
// This is the check that invalidated the first Python driver.
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    level: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS),
      duration: __ENV.DURATION || '8s',
      gracefulStop: '5s',
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const res = http.get(`${__ENV.BASE}/null`);
  check(res, { 'status 200': (r) => r.status === 200 });
}
