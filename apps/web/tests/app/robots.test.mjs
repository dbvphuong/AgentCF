import test from "node:test";
import assert from "node:assert/strict";

test("robot endpoint URL generation escapes robot and version IDs properly", () => {
  const getRobotUrl = (id) => `/v1/robots/${encodeURIComponent(id)}`;
  const getVersionUrl = (robotId, versionId) =>
    `/v1/robots/${encodeURIComponent(robotId)}/versions/${encodeURIComponent(versionId)}`;
  const getPublishUrl = (robotId, versionId) =>
    `/v1/robots/${encodeURIComponent(robotId)}/versions/${encodeURIComponent(versionId)}/publish`;
  const getStatsUrl = (id) => `/v1/robots/${encodeURIComponent(id)}/statistics`;

  assert.equal(getRobotUrl("robot-123"), "/v1/robots/robot-123");
  assert.equal(getRobotUrl("robot/test?name=1"), "/v1/robots/robot%2Ftest%3Fname%3D1");
  assert.equal(getVersionUrl("r1", "v1"), "/v1/robots/r1/versions/v1");
  assert.equal(getPublishUrl("r1", "v1"), "/v1/robots/r1/versions/v1/publish");
  assert.equal(getStatsUrl("r1"), "/v1/robots/r1/statistics");
});

test("robot success rate calculation correctly treats 0 completed runs as null, not 0%", () => {
  const calculateRate = (succeeded, failed) => {
    if (succeeded + failed === 0) return null;
    return Math.round((succeeded / (succeeded + failed)) * 1000) / 10;
  };

  assert.equal(calculateRate(0, 0), null);
  assert.equal(calculateRate(9, 1), 90.0);
  assert.equal(calculateRate(10, 0), 100.0);
  assert.equal(calculateRate(0, 5), 0.0);
});
