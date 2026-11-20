import test from "node:test";
import assert from "node:assert/strict";
import { filterProjects } from "../../src/features/projects/filterProjects.ts";

const projects = [
  { id: "a", name: "Cốt truyện", status: "active", description: "Video", pm_name: "Biên kịch", team: [{ id: "t1", name: "Agent Kịch Bản" }] },
  { id: "b", name: "Bản nháp", status: "archived", description: "Video cũ", pm_name: "PM", team: [] },
];

test("Project status filter includes both lifecycle states under All", () => {
  assert.deepEqual(filterProjects(projects, "all", ""), projects);
  assert.deepEqual(filterProjects(projects, "active", ""), [projects[0]]);
  assert.deepEqual(filterProjects(projects, "archived", ""), [projects[1]]);
});

test("All and lifecycle filters combine with search by name, description, PM or team member", () => {
  assert.deepEqual(filterProjects(projects, "all", " VIDEO "), projects);
  assert.deepEqual(filterProjects(projects, "all", "BẢN NHÁP"), [projects[1]]);
  assert.deepEqual(filterProjects(projects, "all", "biên kịch"), [projects[0]]);
  assert.deepEqual(filterProjects(projects, "all", "Kịch Bản"), [projects[0]]);
  assert.deepEqual(filterProjects(projects, "active", "cũ"), []);
});
