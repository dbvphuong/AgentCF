import { useEffect, useRef, useState } from "react";
import {
  Modal,
  Notice,
  PageHead,
  useResource,
} from "../../../shared/ui";
import { request, resource } from "../../../shared/api";
import type { RecordData } from "../../../shared/api";
import { NewProjectSkill } from "../../skills";
import { RunForm } from "../../runs";
import { NodeForm } from "./NodeForm";
import { TechnicalDetails } from "../../../shared/TechnicalDetails";

export function ProcessEditor({
  processId,
  project,
  onBack,
}: {
  processId: string;
  project: RecordData;
  onBack: () => void;
}) {
  const path = resource("/v1/processes", processId);
  const process = useResource<RecordData>(path + "/configuration");
  const agents = useResource<RecordData[]>("/v1/agents?status=active");
  const models = useResource<RecordData[]>("/v1/settings/ai-tool-models?status=active");
  const skills = useResource<RecordData[]>(`/v1/skills?status=active&project_id=${encodeURIComponent(project.id)}`);
  const runners = useResource<RecordData[]>("/v1/runners");
  const robots = useResource<RecordData[]>("/v1/robots");
  const [robotVersions, setRobotVersions] = useState<RecordData[]>([]);
  const [version, setVersion] = useState<RecordData | null>(null);
  const [graph, setGraph] = useState<RecordData>({
    tasks: [],
    dependencies: [],
    session_mode: "shared_per_tool",
  });
  const [selected, setSelected] = useState("");
  const [selectedEdge, setSelectedEdge] = useState<{
    source_task_id: string;
    target_task_id: string;
  } | null>(null);
  const [dirty, setDirty] = useState(false);
  const [past, setPast] = useState<RecordData[]>([]);
  const [future, setFuture] = useState<RecordData[]>([]);
  const [node, setNode] = useState<RecordData | null>(null);
  const [creatingSkill, setCreatingSkill] = useState(false);
  const [kind, setKind] = useState("agent");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [draggingId, setDraggingId] = useState<string | null>(null);
  const [pendingDropPos, setPendingDropPos] = useState<{ x: number; y: number } | null>(null);
  const [wireDraft, setWireDraft] = useState<{
    sourceTaskId: string;
    sourceTaskName: string;
    startX: number;
    startY: number;
    currentX: number;
    currentY: number;
  } | null>(null);
  const [hoveredTargetId, setHoveredTargetId] = useState<string | null>(null);
  const surface = useRef<HTMLDivElement>(null);
  const editable = !!version;
  const availableModels = models.data ?? [];
  const loadVersion = (v: RecordData) => {
    setVersion(v);
    const def = structuredClone(v.definition);
    if (!def.session_mode) {
      def.session_mode = "shared_per_tool";
    }
    setGraph(def);
    setDirty(false);
    setSelected("");
  };
  useEffect(() => {
    if (process.data) loadVersion(process.data);
  }, [process.data]);
  useEffect(() => {
    let cancelled = false;
    Promise.all(
      (robots.data ?? [])
        .filter((r) => r.status === "active")
        .map(async (r) => {
          const versions = await request<RecordData[]>(
            `${resource("/v1/robots", r.id)}/versions`,
          );
          return versions
            .filter((v) => v.status === "published")
            .map((v) => ({ ...v, name: `${r.name} · v${v.version_number}` }));
        }),
    )
      .then((items) => {
        if (!cancelled) setRobotVersions(items.flat());
      })
      .catch((e) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, [robots.data]);
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) e.preventDefault();
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") return;

      // Undo: Ctrl+Z / Cmd+Z (without shift)
      if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === "z") {
        e.preventDefault();
        undo();
        return;
      }

      // Redo: Ctrl+Y or Ctrl+Shift+Z
      if (
        ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "y") ||
        ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === "z")
      ) {
        e.preventDefault();
        redo();
        return;
      }

      // Escape: Cancel wire dragging or deselect
      if (e.key === "Escape") {
        if (wireDraft) {
          setWireDraft(null);
          setHoveredTargetId(null);
          setMessage("Đã hủy nối dây.");
        } else {
          setSelected("");
          setSelectedEdge(null);
        }
        return;
      }

      // Delete or Backspace: Delete selected wire or node
      if (e.key === "Delete" || e.key === "Backspace") {
        if (selectedEdge) {
          e.preventDefault();
          const sId = selectedEdge.source_task_id;
          const tId = selectedEdge.target_task_id;
          const sName = graph.tasks.find((t: RecordData) => t.id === sId)?.name || "Bước nguồn";
          const tName = graph.tasks.find((t: RecordData) => t.id === tId)?.name || "Bước đích";
          commitChange({
            ...graph,
            dependencies: graph.dependencies.filter(
              (d: RecordData) => !(d.source_task_id === sId && d.target_task_id === tId),
            ),
          }, `Đã xóa dây nối: ${sName} → ${tName}`);
          setSelectedEdge(null);
        } else if (selected && selected !== "__start__" && editable && !busy) {
          e.preventDefault();
          const targetTask = graph.tasks.find((t: RecordData) => t.id === selected);
          if (targetTask) {
            commitChange({
              ...graph,
              tasks: graph.tasks.filter((t: RecordData) => t.id !== selected),
              dependencies: graph.dependencies.filter(
                (d: RecordData) => d.source_task_id !== selected && d.target_task_id !== selected,
              ),
            }, `Đã xóa bước: ${targetTask.name}`);
            setSelected("");
          }
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [graph, past, future, selected, selectedEdge, wireDraft, editable, busy]);
  const commitChange = (next: RecordData, msg?: string) => {
    setPast((p) => [...p.slice(-40), structuredClone(graph)]);
    setFuture([]);
    setGraph(next);
    setDirty(true);
    if (msg) setMessage(msg);
  };

  const undo = () => {
    if (past.length === 0 || busy) return;
    const previous = past[past.length - 1];
    const newPast = past.slice(0, -1);
    setFuture((f) => [structuredClone(graph), ...f.slice(0, 40)]);
    setPast(newPast);
    setGraph(previous);
    setSelected("");
    setSelectedEdge(null);
    setDirty(true);
    setMessage("Đã hoàn tác (Undo)");
  };

  const redo = () => {
    if (future.length === 0 || busy) return;
    const next = future[0];
    const newFuture = future.slice(1);
    setPast((p) => [...p.slice(-40), structuredClone(graph)]);
    setFuture(newFuture);
    setGraph(next);
    setSelected("");
    setSelectedEdge(null);
    setDirty(true);
    setMessage("Đã làm lại (Redo)");
  };

  const change = (next: RecordData) => commitChange(next);
  const save = async () => {
    if (!version) throw new Error("Chưa tải cấu hình Process");
    if (!dirty && version.configuration_token.startsWith("saved:")) return version;
    const configuration = await request<RecordData>(path + "/configuration", "PUT", {
      definition: graph, expected_token: version.configuration_token,
    });
    process.replace(configuration);
    setVersion(configuration);
    setDirty(false);
    return configuration;
  };
  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  const selectedNode = graph.tasks.find((t: RecordData) => t.id === selected);
  const resolveModelInfo = (task: RecordData) => {
    if (task.kind === "robot") return null;
    const toolModelId = task.runtime?.tool_model_id;
    const modelId = task.runtime?.model_id;
    const found = availableModels.find(
      (m: RecordData) =>
        (toolModelId && m.id === toolModelId) ||
        (modelId && m.model_identifier === modelId),
    );
    const modelName = found?.name ?? modelId ?? "Model mặc định";
    const effort = task.runtime?.reasoning_effort;
    const effortMap: Record<string, string> = {
      low: "Low",
      medium: "Mid",
      high: "High",
      xhigh: "Extra High",
      max: "Max",
    };
    const levelLabel =
      effort && effort !== "default"
        ? effortMap[effort] || effort
        : "Mặc định";
    const adapter = task.runtime?.adapter ?? found?.tool_id ?? "codex";
    return {
      modelName,
      levelLabel,
      adapter,
      effortRaw: effort || "default",
    };
  };
  const startPos = graph.layout?.["__start__"] ?? { x: 30, y: 118 };
  const buildPathD = (x1: number, y1: number, x2: number, y2: number) => {
    if (Math.abs(y1 - y2) < 2) {
      return `M ${x1} ${y1} L ${x2} ${y2}`;
    }
    const dx = Math.max(24, Math.min(90, Math.abs(x2 - x1) * 0.45));
    return `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
  };
  const position = (task: RecordData, i: number) =>
    graph.layout?.[task.id] ?? {
      x: 180 + (i % 2) * 280,
      y: 80 + Math.floor(i / 2) * 180,
    };
  // START connects strictly to the designated first step (or the first root task if not set).
  // No magical auto-spawning ghost wires!
  const effectiveStartTaskId =
    graph.start_task_id && graph.tasks.some((t: RecordData) => t.id === graph.start_task_id)
      ? graph.start_task_id
      : graph.tasks.find(
          (t: RecordData) => !graph.dependencies.some((d: RecordData) => d.target_task_id === t.id),
        )?.id || (graph.tasks[0]?.id ?? null);
  const startTargetTask = graph.tasks.find((t: RecordData) => t.id === effectiveStartTaskId);

  const handlePointerDown = (
    e: React.PointerEvent<HTMLElement>,
    id: string,
    currentPos: { x: number; y: number },
  ) => {
    if (e.button !== 0) return;
    setSelected(id);
    if (!editable || busy) return;
    e.preventDefault();
    e.stopPropagation();

    const target = e.currentTarget as HTMLElement;
    try {
      target.setPointerCapture(e.pointerId);
    } catch (_) {}

    const startClientX = e.clientX;
    const startClientY = e.clientY;
    const initialX = currentPos.x;
    const initialY = currentPos.y;
    let nextX = initialX;
    let nextY = initialY;
    let isMoved = false;
    let rafId: number | null = null;
    let latestPos = { x: initialX, y: initialY };

    const onPointerMove = (evt: PointerEvent) => {
      const dx = evt.clientX - startClientX;
      const dy = evt.clientY - startClientY;
      if (!isMoved && (Math.abs(dx) > 3 || Math.abs(dy) > 3)) {
        isMoved = true;
        setDraggingId(id);
      }
      if (isMoved) {
        // Snap to 10px grid for neat visual alignment
        nextX = Math.max(20, Math.round((initialX + dx) / 10) * 10);
        nextY = Math.max(20, Math.round((initialY + dy) / 10) * 10);
        latestPos = { x: nextX, y: nextY };
        if (!rafId) {
          rafId = requestAnimationFrame(() => {
            rafId = null;
            setGraph((prev) => ({
              ...prev,
              layout: { ...prev.layout, [id]: latestPos },
            }));
          });
        }
      }
    };

    const onPointerUp = (evt: PointerEvent) => {
      try {
        target.releasePointerCapture(evt.pointerId);
      } catch (_) {}
      if (rafId) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      document.body.style.cursor = "";
      setDraggingId(null);
      if (isMoved) {
        setPast((p) => [...p.slice(-40), structuredClone(graph)]);
        setFuture([]);
        setGraph((prev) => ({
          ...prev,
          layout: { ...prev.layout, [id]: latestPos },
        }));
        setDirty(true);
        setMessage("");
      }
    };

    document.body.style.cursor = "grabbing";
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  };

  const connectTasks = (sourceId: string, targetId: string) => {
    if (sourceId === "__start__") {
      const tName = graph.tasks.find((t: RecordData) => t.id === targetId)?.name || "Bước đích";
      commitChange({ ...graph, start_task_id: targetId }, `Đã nối Start → ${tName}`);
      return;
    }
    if (sourceId === targetId) {
      setError("Không thể nối bước với chính nó.");
      return;
    }
    const alreadyExists = graph.dependencies.some(
      (d: RecordData) =>
        d.source_task_id === sourceId && d.target_task_id === targetId,
    );
    if (alreadyExists) {
      setMessage("Liên kết giữa 2 bước này đã tồn tại.");
      return;
    }
    const isDirectCycle = graph.dependencies.some(
      (d: RecordData) =>
        d.source_task_id === targetId && d.target_task_id === sourceId,
    );
    if (isDirectCycle) {
      setError("Không thể tạo vòng lặp phụ thuộc (chu trình).");
      return;
    }

    const sName =
      graph.tasks.find((t: RecordData) => t.id === sourceId)?.name || "Bước";
    const tName =
      graph.tasks.find((t: RecordData) => t.id === targetId)?.name || "Bước tiếp theo";

    commitChange({
      ...graph,
      dependencies: [
        ...graph.dependencies,
        { source_task_id: sourceId, target_task_id: targetId },
      ],
    }, `Đã nối: ${sName} → ${tName}`);
  };

  const startConnecting = (
    e: React.PointerEvent<HTMLElement>,
    taskId: string,
    taskName: string,
    portPos: { x: number; y: number },
  ) => {
    if (e.button !== 0 || !editable || busy) return;
    e.preventDefault();
    e.stopPropagation();

    const target = e.currentTarget as HTMLElement;
    try {
      target.setPointerCapture(e.pointerId);
    } catch (_) {}

    const surfaceRect = surface.current?.getBoundingClientRect();
    if (!surfaceRect) return;

    const initialX = Math.round(e.clientX - surfaceRect.left);
    const initialY = Math.round(e.clientY - surfaceRect.top);

    setWireDraft({
      sourceTaskId: taskId,
      sourceTaskName: taskName,
      startX: portPos.x,
      startY: portPos.y,
      currentX: initialX,
      currentY: initialY,
    });

    let movedDistance = 0;
    const startClientX = e.clientX;
    const startClientY = e.clientY;

    const onPointerMove = (evt: PointerEvent) => {
      movedDistance += Math.abs(evt.clientX - startClientX) + Math.abs(evt.clientY - startClientY);
    };

    const onPointerUp = (evt: PointerEvent) => {
      try {
        target.releasePointerCapture(evt.pointerId);
      } catch (_) {}
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);

      if (movedDistance > 8) {
        const elemBelow = document.elementFromPoint(evt.clientX, evt.clientY);
        const nodeElem = elemBelow?.closest<HTMLElement>(
          ".graph-node[data-task-id]",
        );
        const targetTaskId = nodeElem?.dataset.taskId;

        if (targetTaskId && targetTaskId !== taskId) {
          connectTasks(taskId, targetTaskId);
        }
        setWireDraft(null);
        setHoveredTargetId(null);
      } else {
        setMessage(`Đang nối từ: ${taskName}. Bấm vào bước nhận kết quả để nối, hoặc bấm chỗ trống / ESC để hủy.`);
      }
    };

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
  };
  useEffect(() => {
    if (!wireDraft) return;

    const onGlobalMove = (evt: PointerEvent) => {
      if (!surface.current) return;
      const sRect = surface.current.getBoundingClientRect();
      const curX = Math.round(evt.clientX - sRect.left);
      const curY = Math.round(evt.clientY - sRect.top);

      const elemBelow = document.elementFromPoint(evt.clientX, evt.clientY);
      const nodeElem = elemBelow?.closest<HTMLElement>(
        ".graph-node[data-task-id]",
      );
      const targetId = nodeElem?.dataset.taskId || null;

      if (targetId && targetId !== wireDraft.sourceTaskId) {
        setHoveredTargetId(targetId);
      } else {
        setHoveredTargetId(null);
      }

      setWireDraft((prev) =>
        prev ? { ...prev, currentX: curX, currentY: curY } : null,
      );
    };

    window.addEventListener("pointermove", onGlobalMove);
    return () => window.removeEventListener("pointermove", onGlobalMove);
  }, [wireDraft?.sourceTaskId]);

  const availableAgents = agents.data ?? [];
  return (
    <>
      <PageHead title={process.data?.name ?? "Process"}>
        <button className="btn btn-outline" onClick={onBack}>
          ← Project
        </button>
      </PageHead>
      {[
        error,
        process.error,
        agents.error,
        skills.error,
        runners.error,
        robots.error,
      ]
        .filter(Boolean)
        .map((e, i) => (
          <Notice error key={i}>
            {e}
          </Notice>
        ))}
      {message && <Notice>{message}</Notice>}
      {process.loading ? (
        <Notice>Đang tải Process…</Notice>
      ) : (
        version && (
          <>
            <div
              className="editor-toolbar"
              data-unsaved={dirty ? "true" : undefined}
            >
              <div className="toolbar-left-group">
                <span className={`status-pill ${dirty ? "status-unsaved" : "status-saved"}`}>
                  <span className="status-indicator-dot" />
                  {dirty ? "Có thay đổi chưa lưu" : "Cấu hình đã lưu"}
                </span>
                <div className="history-button-group">
                  <button
                    type="button"
                    className="history-btn"
                    disabled={past.length === 0 || busy}
                    onClick={undo}
                    title="Hoàn tác (Ctrl + Z)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M3 7v6h6" />
                      <path d="M21 17a9 9 0 00-9-9 9 9 0 00-6 2.3L3 13" />
                    </svg>
                    <span>Hoàn tác</span>
                  </button>
                  <div className="history-btn-divider" />
                  <button
                    type="button"
                    className="history-btn"
                    disabled={future.length === 0 || busy}
                    onClick={redo}
                    title="Làm lại (Ctrl + Y)"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M21 7v6h-6" />
                      <path d="M3 17a9 9 0 019-9 9 9 0 016 2.3L21 13" />
                    </svg>
                    <span>Làm lại</span>
                  </button>
                </div>
              </div>
              <div className="toolbar-session-group">
                <select
                  aria-label="Chế độ Session AI"
                  className="session-mode-select"
                  value={graph.session_mode ?? "shared_per_tool"}
                  onChange={(e) => {
                    commitChange({
                      ...graph,
                      session_mode: e.target.value,
                    });
                  }}
                >
                  <option value="shared_per_tool">AI(codex, agy) chạy cùng 1 Session</option>
                  <option value="isolated">AI(codex, agy) chạy độc lập Session</option>
                </select>
              </div>
              <div className="row-actions">
                <button className="btn btn-outline" disabled={busy} onClick={() => act(async () => {
                  await save(); setMessage("Đã lưu Process, có thể chạy ngay.");
                })}>Lưu</button>
                <button className="btn btn-primary" disabled={busy} onClick={() => act(async () => {
                  await save(); setRunning(true);
                })}>Chạy</button>
              </div>
            </div>
            <div className="process-builder">
              <aside className="palette panel">
                <h3>Nodes</h3>
                <button
                  disabled={!editable || busy}
                  className="palette-item"
                  draggable={editable && !busy}
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/agent-cf-node", "agent");
                    e.dataTransfer.effectAllowed = "copy";
                  }}
                  onClick={() => {
                    setKind("agent");
                    setPendingDropPos(null);
                    setNode({});
                  }}
                >
                  + Bước AI / Skill
                </button>
                <button
                  disabled={!editable || busy}
                  className="palette-item"
                  draggable={editable && !busy}
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/agent-cf-node", "robot");
                    e.dataTransfer.effectAllowed = "copy";
                  }}
                  onClick={() => {
                    setKind("robot");
                    setPendingDropPos(null);
                    setNode({});
                  }}
                >
                  + Robot
                </button>

                <h4>Dependencies</h4>
                {graph.dependencies.map((e: RecordData, i: number) => (
                  <div className="dependency-row" key={i}>
                    <small>
                      {
                        graph.tasks.find(
                          (t: RecordData) => t.id === e.source_task_id,
                        )?.name
                      }{" "}
                      →{" "}
                      {
                        graph.tasks.find(
                          (t: RecordData) => t.id === e.target_task_id,
                        )?.name
                      }
                    </small>
                    {editable && (
                      <button
                        className="icon-button"
                        aria-label="Xóa dependency"
                        onClick={() =>
                          change({
                            ...graph,
                            dependencies: graph.dependencies.filter(
                              (_: unknown, j: number) => j !== i,
                            ),
                          })
                        }
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </aside>
              <div className="graph-scroll">
                <div
                  ref={surface}
                  className="graph-surface"
                  style={{
                    minWidth: Math.max(
                      900,
                      startPos.x + 240,
                      ...graph.tasks.map(
                        (t: RecordData, i: number) => position(t, i).x + 280,
                      ),
                    ),
                    minHeight: Math.max(
                      650,
                      startPos.y + 200,
                      ...graph.tasks.map(
                        (t: RecordData, i: number) => position(t, i).y + 200,
                      ),
                    ),
                  }}
                  onDragOver={(e) => {
                    if (e.dataTransfer.types.includes("application/agent-cf-node")) {
                      e.preventDefault();
                      e.dataTransfer.dropEffect = "copy";
                    }
                  }}
                  onDrop={(e) => {
                    const droppedKind = e.dataTransfer.getData("application/agent-cf-node");
                    if (droppedKind && surface.current) {
                      e.preventDefault();
                      const rect = surface.current.getBoundingClientRect();
                      const dropX = Math.max(20, Math.round((e.clientX - rect.left) / 10) * 10);
                      const dropY = Math.max(20, Math.round((e.clientY - rect.top) / 10) * 10);
                      setPendingDropPos({ x: dropX, y: dropY });
                      setKind(droppedKind);
                      setNode({});
                    }
                  }}
                  onClick={() => {
                    setSelected("");
                    setSelectedEdge(null);
                    if (wireDraft) {
                      setWireDraft(null);
                      setHoveredTargetId(null);
                    }
                  }}
                >
                  <svg className="graph-edges" aria-hidden="true">
                    <defs>
                      <marker
                        id="arrow-start"
                        viewBox="0 0 10 10"
                        refX="8"
                        refY="5"
                        markerWidth="8"
                        markerHeight="8"
                        orient="auto"
                      >
                        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#10b981" />
                      </marker>
                      <marker
                        id="arrow-dependency"
                        viewBox="0 0 10 10"
                        refX="8"
                        refY="5"
                        markerWidth="8"
                        markerHeight="8"
                        orient="auto"
                      >
                        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#7c3aed" />
                      </marker>
                      <marker
                        id="arrow-selected"
                        viewBox="0 0 10 10"
                        refX="8"
                        refY="5"
                        markerWidth="8"
                        markerHeight="8"
                        orient="auto"
                      >
                        <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#ef4444" />
                      </marker>
                    </defs>
                    {startTargetTask && (() => {
                      const ti = graph.tasks.findIndex((tk: RecordData) => tk.id === startTargetTask.id);
                      const b = position(startTargetTask, ti);
                      const sX = startPos.x + 64;
                      const sY = startPos.y + 32;
                      const eX = b.x - 2;
                      const eY = b.y + 70;
                      return (
                        <path
                          key={`start-edge-${startTargetTask.id}`}
                          className="start-edge"
                          markerEnd="url(#arrow-start)"
                          d={buildPathD(sX, sY, eX, eY)}
                        />
                      );
                    })()}
                    {graph.dependencies.map((edge: RecordData, i: number) => {
                      const si = graph.tasks.findIndex(
                        (t: RecordData) => t.id === edge.source_task_id,
                      );
                      const ti = graph.tasks.findIndex(
                        (t: RecordData) => t.id === edge.target_task_id,
                      );
                      if (si < 0 || ti < 0) return null;
                      const a = position(graph.tasks[si], si),
                        b = position(graph.tasks[ti], ti);
                      const isSelectedEdge =
                        selectedEdge &&
                        selectedEdge.source_task_id === edge.source_task_id &&
                        selectedEdge.target_task_id === edge.target_task_id;
                      const sX = a.x + 230;
                      const sY = a.y + 70;
                      const eX = b.x - 2;
                      const eY = b.y + 70;
                      const edgePathD = buildPathD(sX, sY, eX, eY);
                      return (
                        <g
                          key={i}
                          className="dependency-edge-group"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelected("");
                            setSelectedEdge({
                              source_task_id: edge.source_task_id,
                              target_task_id: edge.target_task_id,
                            });
                            setMessage("Dây nối đang được chọn. Nhấn phím DEL để xóa.");
                          }}
                        >
                          <path
                            d={edgePathD}
                            fill="none"
                            stroke="transparent"
                            strokeWidth={18}
                            style={{ cursor: "pointer" }}
                          />
                          <path
                            className={`dependency-edge ${isSelectedEdge ? "selected-edge" : ""}`}
                            markerEnd={isSelectedEdge ? "url(#arrow-selected)" : "url(#arrow-dependency)"}
                            d={edgePathD}
                          />
                          <title>Bấm để chọn dây này (sau đó nhấn phím DEL để xóa)</title>
                        </g>
                      );
                    })}
                    {wireDraft && (
                      <g className="wire-draft-group">
                        <path
                          className="wire-draft-glow"
                          d={buildPathD(wireDraft.startX, wireDraft.startY, wireDraft.currentX, wireDraft.currentY)}
                        />
                        <path
                          className="wire-draft"
                          markerEnd="url(#arrow-dependency)"
                          d={buildPathD(wireDraft.startX, wireDraft.startY, wireDraft.currentX, wireDraft.currentY)}
                        />
                      </g>
                    )}
                  </svg>
                  <div
                    role="button"
                    tabIndex={0}
                    draggable={false}
                    onDragStart={(e) => e.preventDefault()}
                    className={`graph-node start-node ${selected === "__start__" ? "selected" : ""} ${draggingId === "__start__" ? "is-dragging" : ""}`}
                    style={{ left: startPos.x, top: startPos.y }}
                    onPointerDown={(e) => {
                      if (wireDraft) return;
                      handlePointerDown(e, "__start__", startPos);
                    }}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (wireDraft) {
                        setWireDraft(null);
                        setHoveredTargetId(null);
                        setMessage("Không thể nối vào điểm Start (Start là điểm bắt đầu).");
                        return;
                      }
                      setSelected("__start__");
                      setSelectedEdge(null);
                    }}
                  >
                    <div className="start-circle-inner">
                      <svg
                        className="start-play-icon"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <path d="M8 5v14l11-7z" />
                      </svg>
                      <span className="start-circle-text">START</span>
                    </div>
                    <span
                      className="node-port node-port-out start-port-out"
                      title="Kéo hoặc bấm để nối tới bước bắt đầu quy trình"
                      onPointerDown={(e) =>
                        startConnecting(e, "__start__", "Start", {
                          x: startPos.x + 64,
                          y: startPos.y + 32,
                        })
                      }
                    />
                    <div className="start-node-sublabel">Khởi đầu quy trình</div>
                  </div>
                  {graph.tasks.map((task: RecordData, i: number) => {
                    const pos = position(task, i);
                    return (
                      <div
                        role="button"
                        tabIndex={0}
                        key={task.id}
                        data-task-id={task.id}
                        draggable={false}
                        onDragStart={(e) => e.preventDefault()}
                        className={`graph-node ${selected === task.id ? "selected" : ""} ${draggingId === task.id ? "is-dragging" : ""} ${hoveredTargetId === task.id ? "can-connect-target" : ""}`}
                        style={{ left: pos.x, top: pos.y }}
                        onPointerDown={(e) => {
                          if (wireDraft) return;
                          handlePointerDown(e, task.id, pos);
                        }}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (wireDraft) {
                            connectTasks(wireDraft.sourceTaskId, task.id);
                            setWireDraft(null);
                            setHoveredTargetId(null);
                            return;
                          }
                          setSelected(task.id);
                          setSelectedEdge(null);
                        }}
                      >
                        <span className="node-port node-port-in" title="Đầu vào nhận dữ liệu" />
                        <div className="node-header">
                          <span className={`node-badge ${task.kind === "robot" ? "node-badge-robot" : "node-badge-ai"}`}>
                            {task.kind === "robot" ? "◇ ROBOT" : "✦ BƯỚC AI"}
                          </span>
                          {task.kind !== "robot" && (
                            <span
                              className="node-adapter-tag"
                              title={`Công cụ: ${task.runtime?.adapter === "antigravity" ? "Antigravity" : "Codex CLI"}`}
                            >
                              {task.runtime?.adapter === "antigravity" ? "AGY" : "CODEX"}
                            </span>
                          )}
                        </div>
                        <div className="node-title" title={task.name}>{task.name}</div>
                        <div className="node-meta">
                          <div className="node-meta-row" title={`Agent: ${availableAgents.find((a) => a.id === task.agent_id)?.name ?? task.agent_snapshot?.name ?? "Agent điều phối"}`}>
                            <span className="node-meta-icon">👤</span>
                            <span className="node-meta-text">
                              {availableAgents.find((a) => a.id === task.agent_id)?.name ??
                                task.agent_snapshot?.name ?? "Agent điều phối"}
                            </span>
                          </div>
                          <div className={`node-meta-row ${task.kind === "robot" ? "node-meta-robot" : "node-meta-skill"}`} title={task.skill_id ? (skills.data?.find((s) => s.id === task.skill_id)?.name ?? "Skill") : (robotVersions.find((v) => v.id === task.robot_version_id)?.name ?? "Robot")}>
                            <span className="node-meta-icon">{task.kind === "robot" ? "⚙" : "⚡"}</span>
                            <span className="node-meta-text">
                              {task.skill_id
                                ? (skills.data?.find((s) => s.id === task.skill_id)
                                    ?.name ?? "Skill")
                                : (robotVersions.find(
                                    (v) => v.id === task.robot_version_id,
                                  )?.name ?? "Robot")}
                            </span>
                          </div>
                          {task.kind !== "robot" && (() => {
                            const mi = resolveModelInfo(task);
                            if (!mi) return null;
                            return (
                              <div
                                className="node-meta-row node-meta-model"
                                title={`Công cụ: ${mi.adapter.toUpperCase()} · Model: ${mi.modelName} · Mức suy luận: ${mi.levelLabel}`}
                              >
                                <span className="node-meta-icon">🤖</span>
                                <span className="node-meta-text">
                                  <span className="node-model-name">{mi.modelName}</span>
                                  <span className={`node-level-pill node-level-${mi.effortRaw}`}>
                                    {mi.levelLabel}
                                  </span>
                                </span>
                              </div>
                            );
                          })()}
                        </div>
                        <span
                          className="node-port node-port-out"
                          title="Kéo dây từ đây sang bước tiếp theo"
                          onPointerDown={(e) =>
                            startConnecting(e, task.id, task.name, {
                              x: pos.x + 230,
                              y: pos.y + 70,
                            })
                          }
                        />
                      </div>
                    );
                  })}
                  {!graph.tasks.length && (
                    <div
                      className="graph-empty"
                      style={{ left: startPos.x + 110, top: startPos.y + 6 }}
                    >
                      <strong>Chưa có bước thực thi nào</strong>
                      <p>Bấm "+ Bước AI / Skill" hoặc "+ Robot" bên trái để thêm bước đầu tiên sau Start.</p>
                    </div>
                  )}
                </div>
              </div>
              <aside className="inspector panel">
                <h3>
                  {selectedEdge
                    ? "🔗 Dây nối liên kết"
                    : selected === "__start__"
                    ? "▶ Start (Khởi đầu quy trình)"
                    : (selectedNode?.name ?? "Cấu hình node")}
                </h3>
                {selectedEdge ? (
                  <>
                    <dl className="detail-grid">
                      <div>
                        <dt>Bước nguồn</dt>
                        <dd>{graph.tasks.find((t: RecordData) => t.id === selectedEdge.source_task_id)?.name || selectedEdge.source_task_id}</dd>
                      </div>
                      <div>
                        <dt>Bước đích</dt>
                        <dd>{graph.tasks.find((t: RecordData) => t.id === selectedEdge.target_task_id)?.name || selectedEdge.target_task_id}</dd>
                      </div>
                      <div>
                        <dt>Thao tác nhanh</dt>
                        <dd>Nhấn phím <code>DEL</code> hoặc <code>Backspace</code> trên bàn phím để xóa dây này.</dd>
                      </div>
                    </dl>
                    {editable && (
                      <div className="row-actions" style={{ marginTop: 12 }}>
                        <button
                          type="button"
                          className="btn btn-danger"
                          onClick={() => {
                            commitChange({
                              ...graph,
                              dependencies: graph.dependencies.filter(
                                (d: RecordData) =>
                                  !(d.source_task_id === selectedEdge.source_task_id && d.target_task_id === selectedEdge.target_task_id),
                              ),
                            }, "Đã xóa dây nối.");
                            setSelectedEdge(null);
                          }}
                        >
                          Xóa dây này
                        </button>
                      </div>
                    )}
                  </>
                ) : selected === "__start__" ? (
                  <>
                    <dl className="detail-grid">
                      <div>
                        <dt>Loại node</dt>
                        <dd>Khởi đầu (Start Trigger)</dd>
                      </div>
                      <div>
                        <dt>Trạng thái</dt>
                        <dd>
                          <span
                            className="badge"
                            style={{
                              background: "#d1fae5",
                              color: "#065f46",
                              fontWeight: 700,
                            }}
                          >
                            Bắt đầu
                          </span>
                        </dd>
                      </div>
                      <div>
                        <dt>Mô tả</dt>
                        <dd>
                          Điểm bắt đầu quy trình. Dữ liệu Input JSON khi tạo lượt chạy (Run) sẽ được truyền tự động từ điểm này đến các bước thực thi đầu tiên.
                        </dd>
                      </div>
                      <div>
                        <dt>Kết nối</dt>
                        <dd>
                          {startTargetTask
                            ? `Khởi đầu vào bước: ${startTargetTask.name}`
                            : "Chưa có bước thực thi nào"}
                        </dd>
                      </div>
                    </dl>
                    <p
                      style={{
                        marginTop: 18,
                        padding: "10px 12px",
                        background: "#f0f7ff",
                        borderRadius: 6,
                        border: "1px solid #bfdbfe",
                        color: "#1e40af",
                        fontSize: 12,
                        lineHeight: 1.5,
                      }}
                    >
                      💡 <strong>Node Start là điểm cố định</strong> của quy trình nên không thể xóa. Bạn có thể kéo thả để sắp xếp vị trí thuận tiện trên canvas.
                    </p>
                  </>
                ) : selectedNode ? (
                  <>
                    <dl className="detail-grid">
                      <div>
                        <dt>Loại</dt>
                        <dd>{selectedNode.kind === "robot" ? "◇ Robot" : "✦ Bước AI"}</dd>
                      </div>
                      <div>
                        <dt>Agent điều phối</dt>
                        <dd>
                          {availableAgents.find((a) => a.id === selectedNode.agent_id)
                            ?.name ?? selectedNode.agent_snapshot?.name ?? "Không có tên Agent điều phối"}
                        </dd>
                      </div>
                      <div>
                        <dt>Công cụ AI / PC</dt>
                        <dd>
                          {selectedNode.kind === "agent"
                            ? (selectedNode.runtime?.adapter === "antigravity" ? "Antigravity" : "Codex CLI")
                            : (runners.data?.find((r) => r.id === selectedNode.runner_id)?.name ?? "—")}
                        </dd>
                      </div>
                      {selectedNode.kind === "agent" ? (() => {
                        const mi = resolveModelInfo(selectedNode);
                        return (
                          <>
                            <div>
                              <dt>Model thực thi</dt>
                              <dd>
                                <strong>{mi?.modelName ?? selectedNode.runtime?.model_id ?? "—"}</strong>
                              </dd>
                            </div>
                            <div>
                              <dt>Mức suy luận (Level)</dt>
                              <dd>
                                <span
                                  className={`node-level-pill node-level-${mi?.effortRaw ?? "default"}`}
                                  style={{ marginLeft: 0, padding: "2px 8px", fontSize: "11px" }}
                                >
                                  {mi?.levelLabel ?? "Mặc định"}
                                </span>
                              </dd>
                            </div>
                          </>
                        );
                      })() : (
                        <div>
                          <dt>Phiên bản Robot</dt>
                          <dd>
                            {robotVersions.find((v) => v.id === selectedNode.robot_version_id)?.name ?? "—"}
                          </dd>
                        </div>
                      )}
                    </dl>
                    <TechnicalDetails values={{ "Node ID": selectedNode.id, "Task key": selectedNode.task_key, "Agent ID": selectedNode.agent_id, "Skill ID": selectedNode.skill_id, "PC ID": selectedNode.runner_id, "Input mapping": selectedNode.input_mapping ?? [] }} />
                    {editable && (
                      <div className="row-actions">
                        <button
                          disabled={busy}
                          className="btn btn-outline"
                          onClick={() => {
                            setKind(selectedNode.kind);
                            setNode(selectedNode);
                          }}
                        >
                          Sửa node
                        </button>

                        <button
                          disabled={busy}
                          className="btn btn-danger"
                          onClick={() => {
                            if (
                              window.confirm(
                                `Xóa node ${selectedNode.name} và các dependency liên quan?`,
                              )
                            ) {
                              change({
                                ...graph,
                                tasks: graph.tasks.filter(
                                  (t: RecordData) => t.id !== selected,
                                ),
                                dependencies: graph.dependencies.filter(
                                  (e: RecordData) =>
                                    e.source_task_id !== selected &&
                                    e.target_task_id !== selected,
                                ),
                              });
                              setSelected("");
                            }
                          }}
                        >
                          Xóa
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <div>
                    <h3 style={{ marginTop: 0, fontSize: 14, fontWeight: 700, color: "var(--violet-900, #1e1b4b)" }}>
                      Cấu hình Process
                    </h3>
                    <div style={{ marginTop: 12 }}>
                      <label style={{ fontSize: 12, fontWeight: 600, color: "#4b5563", display: "block", marginBottom: 6 }}>
                        Phiên chạy AI:
                      </label>
                      <select
                        aria-label="Cấu hình phiên chạy AI"
                        className="session-mode-select"
                        style={{ width: "100%", padding: "7px 10px" }}
                        value={graph.session_mode ?? "shared_per_tool"}
                        onChange={(e) => {
                          commitChange({
                            ...graph,
                            session_mode: e.target.value,
                          });
                        }}
                      >
                        <option value="shared_per_tool">AI(codex, agy) chạy cùng 1 Session</option>
                        <option value="isolated">AI(codex, agy) chạy độc lập Session</option>
                      </select>
                    </div>
                    <p className="muted" style={{ marginTop: 16, fontSize: 12 }}>
                      Bấm vào một node trên sơ đồ để xem hoặc sửa chi tiết.
                    </p>
                  </div>
                )}
              </aside>
            </div>
          </>
        )
      )}
      {node && (
        <Modal
          title={`${node.id ? "Sửa" : "Thêm"} ${kind === "agent" ? "bước AI" : "node Robot"}`}
          onClose={() => setNode(null)}
        >
          <div className="toolbar">
            {kind === "agent" && <button type="button" className="btn btn-outline" onClick={() => setCreatingSkill(true)}>+ Tạo Skill cho Project này</button>}
          </div>
          {[agents, models].filter(r => r.error).map((r, i) => <Notice key={i} error>{r.error}</Notice>)}
          <NodeForm node={node} kind={kind} agents={availableAgents} models={availableModels} skills={skills.data ?? []}
            runners={(runners.data ?? []).filter(r => r.workspace_id === project.workspace_id && r.status !== "disabled")}
            robotVersions={robotVersions}
            onCancel={() => setNode(null)}
            onSave={async (data) => {
              const model = availableModels.find(m => m.id === data.node_model_id);
              const id = node.id ?? crypto.randomUUID();
              const task: RecordData = {
                ...node,
                ...data,
                id,
                task_key: node.task_key || `task_${id.replaceAll("-", "")}`,
                kind,
                ...(kind === "agent"
                  ? {
                      runtime: {
                        adapter: data.adapter,
                        model_id: model?.model_identifier,
                        tool_model_id: model?.id,
                        ...(data.node_reasoning_effort && data.node_reasoning_effort !== "default"
                          ? { reasoning_effort: data.node_reasoning_effort } : {}),
                      },
                    }
                  : {}),
              };
              delete task.adapter;
              delete task.node_model_id;
              delete task.node_reasoning_effort;
              if (kind === "agent") {
                if (!task.runner_id) delete task.runner_id;
                delete task.working_directory;
              }
              const nextLayout = { ...graph.layout };
              if (pendingDropPos && !node.id) {
                nextLayout[id] = pendingDropPos;
                setPendingDropPos(null);
              }
              change({
                ...graph,
                layout: nextLayout,
                tasks: node.id
                  ? graph.tasks.map((t: RecordData) =>
                      t.id === node.id ? task : t,
                    )
                  : [...graph.tasks, task],
              });
              setSelected(task.id);
              setNode(null);
            }}
          />
        </Modal>
      )}
      {creatingSkill && <NewProjectSkill projectId={project.id} onClose={() => setCreatingSkill(false)} onCreated={() => skills.reload()} />}

      {running && <Modal title="Chạy Process" onClose={() => setRunning(false)}>
        <RunForm embedded initialProcessId={processId} onCancel={() => setRunning(false)} onRunCreated={run => {
          window.location.hash = `#/runs/${encodeURIComponent(run.id)}`;
          setRunning(false);
        }} />
      </Modal>}

    </>
  );
}
