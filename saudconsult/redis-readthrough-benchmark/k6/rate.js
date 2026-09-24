// OPEN-LOOP capacity test at a FIXED ARRIVAL RATE.
//
// WHY THIS EXISTS - the critical finding of two independent adversarial reviews.
// The closed-loop `constant-vus` sweep cannot measure "throughput at a fixed p99":
// with a fixed VU count each VU waits for its own response before issuing the
// next, so when the service slows the generator SILENTLY OFFERS LESS LOAD. The
// tail then never reaches the ceiling, and `sustained()` ends up reporting each
// arm's saturation peak under a cap that never binds - which is a different
// quantity from the one the claim names. That is coordinated omission.
//
// `constant-arrival-rate` fixes the OFFER RATE independently of how fast the
// service replies. Requests that cannot be started are reported as
// `dropped_iterations`, so an arm that cannot keep up is visible instead of
// quietly throttling the load. THIS is the executor that can answer "what
// throughput holds p99 at or under 250 ms".
import http from 'k6/http';
import { check } from 'k6';
import { SharedArray } from 'k6/data';
import { Counter } from 'k6/metrics';

const seq = new SharedArray('seq', function () {
  return JSON.parse(open('/work/results/sequence.json'));
});

const cacheHit = new Counter('cache_hit');
const cacheMiss = new Counter('cache_miss');
const cacheOff = new Counter('cache_off');

export const options = {
  scenarios: {
    rate: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE),
      timeUnit: '1s',
      duration: __ENV.DURATION || '10s',
      // Enough VUs that the arrival rate, not VU starvation, is the constraint.
      preAllocatedVUs: Number(__ENV.PREVUS || 600),
      maxVUs: Number(__ENV.MAXVUS || 2000),
      gracefulStop: '10s',
    },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(95)', 'p(99)', 'max'],
};

export default function () {
  const i = (__VU * 99991 + __ITER * 7919 + Number(__ENV.OFFSET || 0)) % seq.length;
  const res = http.get(`${__ENV.BASE}/config/${seq[i]}`);
  const ok = check(res, { 'status 200': (r) => r.status === 200 });
  if (ok) {
    const c = res.headers['X-Cache'];
    if (c === 'hit') cacheHit.add(1);
    else if (c === 'miss') cacheMiss.add(1);
    else cacheOff.add(1);
  }
}
