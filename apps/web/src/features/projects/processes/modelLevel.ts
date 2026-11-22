export interface ToolModelLike {
  name?: string | null;
  model_identifier?: string | null;
  tool_id?: string | null;
}

export interface TaskLike {
  kind?: string;
  runtime?: {
    adapter?: string | null;
    model_id?: string | null;
    tool_model_id?: string | null;
    reasoning_effort?: string | null;
  } | null;
}

export const EFFORT_SHORT_LABELS: Record<string, string> = {
  low: "Low",
  medium: "Mid",
  high: "High",
  xhigh: "Extra High",
  max: "Max",
};

export const EFFORT_OPTION_LABELS: Record<string, string> = {
  low: "Low (Thấp)",
  medium: "Mid (Vừa)",
  high: "High (Cao)",
  xhigh: "Extra High (Rất cao)",
  max: "Max (Tối đa)",
};

const IDENTIFIER_LEVEL_RE = /(?:^|[-_.])(low|medium|high|xhigh|max)$/i;
const NAME_LEVEL_RE = /\((low|medium|high|xhigh|max)\)\s*$/i;

export function extractEmbeddedModelLevel(model?: ToolModelLike | null): string | null {
  if (!model) return null;
  const identifier = typeof model.model_identifier === "string" ? model.model_identifier.trim() : "";
  const idMatch = identifier.match(IDENTIFIER_LEVEL_RE);
  if (idMatch) return idMatch[1].toLowerCase();
  const name = typeof model.name === "string" ? model.name.trim() : "";
  const nameMatch = name.match(NAME_LEVEL_RE);
  return nameMatch ? nameMatch[1].toLowerCase() : null;
}

export function shouldShowReasoningEffort(adapter: string, model?: ToolModelLike | null): boolean {
  if (adapter === "codex") return true;
  return Boolean(model) && extractEmbeddedModelLevel(model) === null;
}

export function resolveTaskModelInfo(
  task: TaskLike,
  availableModels: Array<ToolModelLike & { id?: string }>,
) {
  if (task.kind === "robot") return null;
  const toolModelId = task.runtime?.tool_model_id;
  const modelId = task.runtime?.model_id;
  const found = availableModels.find(
    (m) =>
      (toolModelId && m.id === toolModelId) ||
      (modelId && m.model_identifier === modelId),
  );
  const modelName = found?.name ?? modelId ?? "Model mặc định";
  const adapter = task.runtime?.adapter ?? found?.tool_id ?? "codex";
  const effort = task.runtime?.reasoning_effort;
  const embeddedLevel = extractEmbeddedModelLevel(
    found ?? (modelId ? { model_identifier: modelId } : null),
  );
  const hasExplicitOverride = Boolean(effort && effort !== "default");

  if (hasExplicitOverride && effort) {
    const label = EFFORT_SHORT_LABELS[effort] || effort;
    return {
      modelName,
      levelLabel: label,
      inspectorLevelLabel: label,
      adapter,
      effortRaw: effort,
      showCardPill: true,
    };
  }
  if (embeddedLevel) {
    const label = EFFORT_SHORT_LABELS[embeddedLevel] || embeddedLevel;
    return {
      modelName,
      levelLabel: label,
      inspectorLevelLabel: `${label} (theo model)`,
      adapter,
      effortRaw: embeddedLevel,
      showCardPill: false,
    };
  }
  return {
    modelName,
    levelLabel: "Mặc định",
    inspectorLevelLabel: "Mặc định",
    adapter,
    effortRaw: "default",
    showCardPill: true,
  };
}
