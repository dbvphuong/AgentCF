import type { RecordData } from "../../shared/api";

export function filterProjects(projects: RecordData[], status: string, search: string) {
  const query = search.trim().toLocaleLowerCase("vi");
  return projects.filter(
    (project) => {
      const teamText = (project.team ?? []).map((m: RecordData) => m.name).join(" ");
      return (
        (status === "all" || project.status === status) &&
        `${project.name} ${project.description ?? ""} ${project.pm_name ?? ""} ${teamText}`
          .toLocaleLowerCase("vi")
          .includes(query)
      );
    },
  );
}
