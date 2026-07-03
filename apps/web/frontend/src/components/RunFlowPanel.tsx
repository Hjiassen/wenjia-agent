import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent,
  type CSSProperties,
  type WheelEvent,
} from "react";
import { Button, Tooltip } from "antd";
import {
  AimOutlined,
  DragOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from "@ant-design/icons";
import type { FlowEvent, FlowStage } from "../types";
import { buildPipeline } from "../lib/flowModel";
import { StageCard } from "./StageCard";

export interface RunFlowTurn {
  id: string;
  prompt: string;
  events: FlowEvent[];
  error?: boolean;
  live?: boolean;
}

interface RunFlowPanelProps {
  open: boolean;
  turns: RunFlowTurn[];
  onClose: () => void;
}

type FlowItem =
  | { kind: "turn"; id: string; index: number; prompt: string; live?: boolean; error?: boolean }
  | { kind: "stage"; id: string; stage: FlowStage };

interface FlowRow {
  id: string;
  items: FlowItem[];
}

interface CanvasViewport {
  x: number;
  y: number;
  scale: number;
}

interface DragState {
  pointerId: number;
  startX: number;
  startY: number;
  originX: number;
  originY: number;
}

interface PointerPoint {
  x: number;
  y: number;
}

interface PinchState {
  pointerIds: [number, number];
  startDistance: number;
  startCenterX: number;
  startCenterY: number;
  startViewport: CanvasViewport;
}

const MIN_SCALE = 0.5;
const MAX_SCALE = 1.8;
const SCALE_STEP = 0.14;
const DEFAULT_VIEWPORT: CanvasViewport = { x: 28, y: 34, scale: 1 };

function snippet(text: string): string {
  const compact = text.replace(/\s+/g, " ").trim();
  if (!compact) return "（无提问）";
  return compact.length > 24 ? `${compact.slice(0, 24)}…` : compact;
}

function clampScale(value: number): number {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, value));
}

function zoomLabel(scale: number): string {
  return `${Math.round(scale * 100)}%`;
}

function pointerDistance(first: PointerPoint, second: PointerPoint): number {
  return Math.hypot(first.x - second.x, first.y - second.y);
}

function pointerCenter(first: PointerPoint, second: PointerPoint): PointerPoint {
  return {
    x: (first.x + second.x) / 2,
    y: (first.y + second.y) / 2,
  };
}

// Keep each conversation turn on its own canvas row. A row begins with the turn
// marker and only wraps after all stages in that turn have finished rendering.
function buildRows(turns: RunFlowTurn[]): FlowRow[] {
  return turns.map((turn, index) => {
    const items: FlowItem[] = [
      {
        kind: "turn",
        id: turn.id,
        index: index + 1,
        prompt: turn.prompt,
        live: turn.live,
        error: turn.error,
      },
    ];
    buildPipeline(turn.events).forEach((stage) => {
      items.push({ kind: "stage", id: `${turn.id}-${stage.id}`, stage });
    });
    return { id: turn.id, items };
  });
}

export function RunFlowPanel({ open, turns, onClose }: RunFlowPanelProps) {
  const rows = useMemo(() => buildRows(turns), [turns]);
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<DragState | null>(null);
  const activePointersRef = useRef<Map<number, PointerPoint>>(new Map());
  const pinchRef = useRef<PinchState | null>(null);
  const [viewport, setViewport] = useState<CanvasViewport>(DEFAULT_VIEWPORT);
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    if (!open) return;
    setViewport(DEFAULT_VIEWPORT);
    setIsDragging(false);
    dragRef.current = null;
    pinchRef.current = null;
    activePointersRef.current.clear();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const zoomTo = useCallback((nextScale: number, anchorX?: number, anchorY?: number) => {
    setViewport((prev) => {
      const rect = viewportRef.current?.getBoundingClientRect();
      const targetScale = clampScale(nextScale);
      if (!rect) {
        return { ...prev, scale: targetScale };
      }
      const localX = anchorX ?? rect.width / 2;
      const localY = anchorY ?? rect.height / 2;
      const worldX = (localX - prev.x) / prev.scale;
      const worldY = (localY - prev.y) / prev.scale;
      return {
        x: localX - worldX * targetScale,
        y: localY - worldY * targetScale,
        scale: targetScale,
      };
    });
  }, []);

  const handleWheel = useCallback(
    (event: WheelEvent<HTMLDivElement>) => {
      if (!rows.length) return;
      event.preventDefault();
      const rect = event.currentTarget.getBoundingClientRect();
      const localX = event.clientX - rect.left;
      const localY = event.clientY - rect.top;
      const direction = event.deltaY > 0 ? -1 : 1;
      zoomTo(viewport.scale + direction * SCALE_STEP, localX, localY);
    },
    [rows.length, viewport.scale, zoomTo],
  );

  const startPinch = useCallback((target: HTMLDivElement) => {
    const pointers = Array.from(activePointersRef.current.entries()).slice(0, 2);
    if (pointers.length < 2) return;

    const [[firstId, first], [secondId, second]] = pointers;
    const distance = pointerDistance(first, second);
    if (distance <= 0) return;

    const rect = target.getBoundingClientRect();
    const center = pointerCenter(first, second);
    pinchRef.current = {
      pointerIds: [firstId, secondId],
      startDistance: distance,
      startCenterX: center.x - rect.left,
      startCenterY: center.y - rect.top,
      startViewport: viewport,
    };
    dragRef.current = null;
    setIsDragging(true);
  }, [viewport]);

  const handlePointerDown = useCallback(
    (event: PointerEvent<HTMLDivElement>) => {
      if (event.pointerType === "mouse" && event.button !== 0) return;
      const target = event.target as HTMLElement;
      if (target.closest(".runflow-canvas-controls") || target.closest(".runflow-close")) {
        return;
      }
      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      activePointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });

      if (activePointersRef.current.size >= 2) {
        startPinch(event.currentTarget);
        return;
      }

      dragRef.current = {
        pointerId: event.pointerId,
        startX: event.clientX,
        startY: event.clientY,
        originX: viewport.x,
        originY: viewport.y,
      };
      setIsDragging(true);
    },
    [startPinch, viewport.x, viewport.y],
  );

  const handlePointerMove = useCallback((event: PointerEvent<HTMLDivElement>) => {
    if (activePointersRef.current.has(event.pointerId)) {
      activePointersRef.current.set(event.pointerId, { x: event.clientX, y: event.clientY });
    }

    const pinch = pinchRef.current;
    if (pinch) {
      const first = activePointersRef.current.get(pinch.pointerIds[0]);
      const second = activePointersRef.current.get(pinch.pointerIds[1]);
      if (!first || !second) return;

      event.preventDefault();
      const rect = event.currentTarget.getBoundingClientRect();
      const center = pointerCenter(first, second);
      const distance = pointerDistance(first, second);
      const targetScale = clampScale(
        pinch.startViewport.scale * (distance / pinch.startDistance),
      );
      const worldX = (pinch.startCenterX - pinch.startViewport.x) / pinch.startViewport.scale;
      const worldY = (pinch.startCenterY - pinch.startViewport.y) / pinch.startViewport.scale;
      const localCenterX = center.x - rect.left;
      const localCenterY = center.y - rect.top;
      setViewport({
        x: localCenterX - worldX * targetScale,
        y: localCenterY - worldY * targetScale,
        scale: targetScale,
      });
      return;
    }

    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    setViewport((prev) => ({
      ...prev,
      x: drag.originX + event.clientX - drag.startX,
      y: drag.originY + event.clientY - drag.startY,
    }));
  }, []);

  const stopDrag = useCallback((event: PointerEvent<HTMLDivElement>) => {
    activePointersRef.current.delete(event.pointerId);
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }

    const pinch = pinchRef.current;
    if (pinch?.pointerIds.includes(event.pointerId)) {
      pinchRef.current = null;
      dragRef.current = null;
      setIsDragging(false);
      return;
    }

    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    dragRef.current = null;
    setIsDragging(false);
  }, []);

  const canvasStyle = useMemo(
    () => ({
      transform: `translate3d(${viewport.x}px, ${viewport.y}px, 0) scale(${viewport.scale})`,
    }),
    [viewport],
  );
  const bodyStyle = useMemo(
    () =>
      ({
        "--runflow-grid-x": `${viewport.x}px`,
        "--runflow-grid-y": `${viewport.y}px`,
        "--runflow-grid-main": `${48 * viewport.scale}px`,
        "--runflow-grid-dot": `${16 * viewport.scale}px`,
      }) as CSSProperties,
    [viewport],
  );

  return (
    <div className={`runflow-root ${open ? "is-open" : ""}`.trim()} aria-hidden={!open}>
      <div className="runflow-overlay" onClick={onClose} />
      <div className="runflow-modal" role="dialog" aria-label="运行流" aria-modal="true">
        <header className="runflow-head">
          <div>
            <p className="eyebrow">推演过程</p>
            <h2>运行流 · 共 {turns.length} 轮</h2>
          </div>
          <button type="button" className="runflow-close" onClick={onClose} aria-label="关闭">
            ✕
          </button>
        </header>

        <div
          ref={viewportRef}
          className={`runflow-body ${isDragging ? "is-dragging" : ""}`.trim()}
          style={bodyStyle}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={stopDrag}
          onPointerCancel={stopDrag}
          onWheel={handleWheel}
        >
          {rows.length ? (
            <>
              <div className="runflow-canvas-controls" aria-label="画布缩放控制">
                <Tooltip title="拖动画布 / 双指缩放">
                  <span className="runflow-pan-icon" aria-hidden>
                    <DragOutlined />
                  </span>
                </Tooltip>
                <Tooltip title="缩小">
                  <Button
                    type="text"
                    size="small"
                    icon={<ZoomOutOutlined />}
                    onClick={() => zoomTo(viewport.scale - SCALE_STEP)}
                    aria-label="缩小"
                  />
                </Tooltip>
                <span className="runflow-zoom-value">{zoomLabel(viewport.scale)}</span>
                <Tooltip title="放大">
                  <Button
                    type="text"
                    size="small"
                    icon={<ZoomInOutlined />}
                    onClick={() => zoomTo(viewport.scale + SCALE_STEP)}
                    aria-label="放大"
                  />
                </Tooltip>
                <Tooltip title="复位">
                  <Button
                    type="text"
                    size="small"
                    icon={<AimOutlined />}
                    onClick={() => setViewport(DEFAULT_VIEWPORT)}
                    aria-label="复位画布"
                  />
                </Tooltip>
              </div>
              <div className="runflow-canvas" style={canvasStyle}>
                <div className="runflow-flow">
                  {rows.map((row) => (
                    <div className="runflow-row" key={row.id}>
                      {row.items.map((item, index) => (
                        <div className="runflow-node" key={item.id}>
                          {index > 0 ? (
                            <span className="runflow-connector" aria-hidden>
                              →
                            </span>
                          ) : null}
                          {item.kind === "turn" ? (
                            <div
                              className={`runflow-turn-chip ${item.live ? "is-live" : ""} ${
                                item.error ? "is-error" : ""
                              }`.trim()}
                            >
                              <span className="runflow-turn-index">
                                第 {item.index} 轮
                                {item.live ? <span className="runflow-live-dot" aria-hidden /> : null}
                              </span>
                              <span className="runflow-turn-prompt">{snippet(item.prompt)}</span>
                            </div>
                          ) : (
                            <StageCard stage={item.stage} />
                          )}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <p className="runflow-empty">还没有推演记录，发起一次提问后这里会出现完整运行流。</p>
          )}
        </div>
      </div>
    </div>
  );
}
