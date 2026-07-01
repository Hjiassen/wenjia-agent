import type { CSSProperties, ReactNode } from "react";
import { Tag, Typography } from "antd";
import {
  CheckCircleFilled,
  CheckOutlined,
  ClockCircleOutlined,
  CloseCircleFilled,
  CloseOutlined,
  LoadingOutlined,
  SwapOutlined,
} from "@ant-design/icons";
import type { FlowStage, StageStatus } from "../types";
import { COLORS } from "../theme";

const STATUS_META: Record<StageStatus, { text: string; icon: ReactNode }> = {
  pending: { text: "等待", icon: <ClockCircleOutlined /> },
  active: { text: "进行中", icon: <LoadingOutlined /> },
  success: { text: "完成", icon: <CheckCircleFilled /> },
  failed: { text: "失败", icon: <CloseCircleFilled /> },
};

const TOOL_ICON: Record<StageStatus, ReactNode> = {
  pending: <ClockCircleOutlined />,
  active: <LoadingOutlined />,
  success: <CheckOutlined />,
  failed: <CloseOutlined />,
};

const NEUTRAL = "#6b7280";

function accent(status: StageStatus): string {
  if (status === "success") return COLORS.teal;
  if (status === "active") return COLORS.gold;
  if (status === "failed") return COLORS.rose;
  return NEUTRAL;
}

// Solid brand-colored pill for the stage status (crisp, never a washed grey tint).
function statusStyle(status: StageStatus): CSSProperties {
  if (status === "pending") {
    return { color: NEUTRAL, background: "transparent", borderColor: "#d9d9d9" };
  }
  const c = accent(status);
  return { color: "#fff", background: c, borderColor: c };
}

// Lighter outlined pill for tools so a card with several tools stays calm.
function toolStyle(status: StageStatus): CSSProperties {
  const c = accent(status);
  return { color: c, background: "transparent", borderColor: c };
}

function durationText(value?: number): string {
  return typeof value === "number" ? ` · ${value.toFixed(2)}s` : "";
}

function stageStatusMeta(stage: FlowStage): { text: string; icon: ReactNode } {
  if (stage.kind === "interrupted") {
    return { text: "中止", icon: <CloseCircleFilled /> };
  }
  return STATUS_META[stage.status];
}

function isCheckpoint(stage: FlowStage): boolean {
  return (
    (stage.kind === "start" || stage.kind === "verify" || stage.kind === "done") &&
    !stage.viaHandoff &&
    stage.thinkingSteps.length === 0 &&
    stage.tools.length === 0
  );
}

export function StageCard({ stage }: { stage: FlowStage }) {
  const meta = stageStatusMeta(stage);
  const hasDetails = Boolean(stage.viaHandoff || stage.thinkingSteps.length || stage.tools.length);

  if (isCheckpoint(stage)) {
    return (
      <div className={`stage-marker kind-${stage.kind} status-${stage.status}`}>
        <span className={`stage-marker-icon status-${stage.status}`}>{meta.icon}</span>
        <span className="stage-marker-label">{stage.label}</span>
        {stage.status === "success" ? null : (
          <span className="stage-marker-status">{meta.text}</span>
        )}
      </div>
    );
  }

  return (
    <article
      className={`stage-card kind-${stage.kind} status-${stage.status} ${
        hasDetails ? "has-details" : "is-compact"
      }`}
    >
      <header className="stage-card-head">
        <span className="stage-title">
          <span className={`stage-icon status-${stage.status}`}>{meta.icon}</span>
          <span className="stage-title-text">{stage.label}</span>
        </span>
        <Tag style={statusStyle(stage.status)} className="stage-status-tag">
          {meta.text}
        </Tag>
      </header>

      {hasDetails ? (
        <div className="stage-card-body">
          {stage.viaHandoff ? (
            <Typography.Text type="secondary" className="stage-handoff">
              <SwapOutlined /> 由{stage.viaHandoff}移交
            </Typography.Text>
          ) : null}

          {stage.thinkingSteps.map((step, index) => (
            <Typography.Paragraph key={index} type="secondary" className="stage-thinking">
              {step}
            </Typography.Paragraph>
          ))}

          {stage.tools.length ? (
            <div className="stage-tools">
              {stage.tools.map((tool) => (
                <Tag
                  key={tool.id}
                  icon={TOOL_ICON[tool.status]}
                  style={toolStyle(tool.status)}
                  className="tool-tag"
                >
                  {tool.label}
                  {durationText(tool.duration)}
                </Tag>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}
