import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import Breadcrumbs from "../components/Breadcrumbs";
import Button from "../components/Button";
import EmptyState from "../components/EmptyState";
import Field from "../components/Field";
import SectionMessage from "../components/SectionMessage";
import Spinner from "../components/Spinner";
import { useToast } from "../components/Toast";
import { useBusy } from "../hooks/useBusy";
import { SHEET_TYPES, type SheetTypeValue } from "./OperatorDashboard/types";

type LayoutSummary = {
  id: number;
  template_family: string;
  name: string;
  max_questions: number;
  created_at: string | null;
};

type FieldBlock = {
  fieldType: string;
  origin: [number, number];
  bubblesGap: number;
  labelsGap: number;
  fieldLabels: string[];
};

type Template = {
  pageDimensions: [number, number];
  bubbleDimensions: [number, number];
  emptyValue?: string;
  preProcessors?: unknown[];
  fieldBlocks: Record<string, FieldBlock>;
};

type Bubble = {
  block: string;
  field_label: string;
  field_value: string;
  x: number;
  y: number;
  w: number;
  h: number;
};

type Overlay = {
  page_dimensions: [number, number];
  bubble_dimensions: [number, number];
  blocks: { name: string; labels: number; bubbles_per_label: number }[];
  bubbles: Bubble[];
};

type WarpResult = {
  aligned: boolean;
  image: string | null;
  width: number | null;
  height: number | null;
};

const DISPLAY_WIDTH = 460;

function sheetLabel(value: SheetTypeValue) {
  return SHEET_TYPES.find((s) => s.value === value)?.label ?? value;
}

function defaultLayoutName(sheetType: SheetTypeValue) {
  return `Isra ${sheetType}`;
}

export default function LayoutCalibrator() {
  const toast = useToast();
  const { busy: initBusy, run: runInit } = useBusy();
  const { busy: previewBusy, run: runPreview } = useBusy();
  const { busy: saveBusy, run: runSave } = useBusy();

  const [layouts, setLayouts] = useState<LayoutSummary[]>([]);
  const [sheetType, setSheetType] = useState<SheetTypeValue>("150Q");
  const [layoutId, setLayoutId] = useState<number | null>(null);
  const [name, setName] = useState(defaultLayoutName("150Q"));
  const [template, setTemplate] = useState<Template | null>(null);
  const [overlay, setOverlay] = useState<Overlay | null>(null);
  const [warp, setWarp] = useState<WarpResult | null>(null);
  const [error, setError] = useState("");
  const refreshTimer = useRef<number | null>(null);
  const warpCache = useRef<{ family: string; result: WarpResult | null } | null>(null);

  const reloadLayouts = useCallback(async () => {
    const data = await api<{ layouts: LayoutSummary[] }>("/templates");
    setLayouts(data.layouts);
  }, []);

  const loadWarp = useCallback(
    async (fam: string, tpl: Template, force = false) => {
      if (!force && warpCache.current?.family === fam && warpCache.current.result?.aligned) {
        setWarp(warpCache.current.result);
        return;
      }
      try {
        const wp = await runPreview(() =>
          api<WarpResult>("/templates/warp", {
            method: "POST",
            body: JSON.stringify({ template_family: fam, template: tpl }),
          }).catch(() => null),
        );
        warpCache.current = { family: fam, result: wp };
        setWarp(wp);
      } catch {
        warpCache.current = { family: fam, result: null };
        setWarp(null);
      }
    },
    [runPreview],
  );

  const refreshOverlay = useCallback(
    async (tpl: Template, fam: string) => {
      setError("");
      try {
        const ov = await runPreview(() =>
          api<Overlay>("/templates/overlay", {
            method: "POST",
            body: JSON.stringify({ template_family: fam, template: tpl }),
          }),
        );
        setOverlay(ov);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [runPreview],
  );

  const refreshPreview = useCallback(
    async (tpl: Template, fam: string, forceWarp = false) => {
      await Promise.all([loadWarp(fam, tpl, forceWarp), refreshOverlay(tpl, fam)]);
    },
    [loadWarp, refreshOverlay],
  );

  const scheduleOverlayRefresh = useCallback(
    (tpl: Template, fam: string) => {
      if (refreshTimer.current) window.clearTimeout(refreshTimer.current);
      refreshTimer.current = window.setTimeout(() => refreshOverlay(tpl, fam), 400);
    },
    [refreshOverlay],
  );

  const loadBuiltInTemplate = useCallback(
    async (fam: SheetTypeValue, quiet = false) => {
      setError("");
      warpCache.current = null;
      try {
        const data = await api<{ template: Template }>(`/templates/families/${fam}/default`);
        setTemplate(data.template);
        setLayoutId(null);
        setName(defaultLayoutName(fam));
        if (!quiet) toast.success(`Loaded ${sheetLabel(fam)} layout.`);
        await refreshPreview(data.template, fam);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [refreshPreview, toast],
  );

  useEffect(() => {
    runInit(async () => {
      await reloadLayouts();
      await loadBuiltInTemplate("150Q", true);
    }).catch((e) => setError((e as Error).message));
    // Mount-only bootstrap; stable callbacks are listed explicitly.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadLayout = async (id: number) => {
    setError("");
    try {
      const data = await api<LayoutSummary & { template: Template }>(`/templates/${id}`);
      setTemplate(data.template);
      setLayoutId(data.id);
      setSheetType(data.template_family as SheetTypeValue);
      setName(data.name);
      toast.info("Loaded saved layout.");
      await refreshPreview(data.template, data.template_family);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const updateBlock = (
    blockName: string,
    field: keyof FieldBlock,
    idx: number | null,
    value: number,
  ) => {
    if (!template) return;
    const next: Template = structuredClone(template);
    const block = next.fieldBlocks[blockName];
    if (idx === null) {
      (block[field] as number) = value;
    } else {
      (block[field] as [number, number])[idx] = value;
    }
    setTemplate(next);
    scheduleOverlayRefresh(next, sheetType);
  };

  const updateBubbleDim = (idx: number, value: number) => {
    if (!template) return;
    const next: Template = structuredClone(template);
    next.bubbleDimensions[idx] = value;
    setTemplate(next);
    scheduleOverlayRefresh(next, sheetType);
  };

  const save = async () => {
    if (!template) return;
    const saveName = name.trim() || defaultLayoutName(sheetType);
    setError("");
    try {
      await runSave(async () => {
        if (layoutId === null) {
          const created = await api<LayoutSummary>("/templates", {
            method: "POST",
            body: JSON.stringify({
              name: saveName,
              template_family: sheetType,
              template,
            }),
          });
          setLayoutId(created.id);
          setName(created.name);
          toast.success("Custom layout saved.");
        } else {
          await api(`/templates/${layoutId}`, {
            method: "PUT",
            body: JSON.stringify({ name: saveName, template }),
          });
          toast.success("Layout updated.");
        }
        await reloadLayouts();
      });
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const savedLayouts = useMemo(
    () =>
      layouts.filter(
        (l) => l.template_family === sheetType && l.name !== defaultLayoutName(sheetType),
      ),
    [layouts, sheetType],
  );

  const scale = useMemo(() => {
    const pageW = overlay?.page_dimensions[0] ?? template?.pageDimensions[0] ?? 1;
    return DISPLAY_WIDTH / pageW;
  }, [overlay, template]);

  const pageH = overlay?.page_dimensions[1] ?? template?.pageDimensions[1] ?? 1;
  const editingCustom = layoutId !== null;

  return (
    <section>
      <Breadcrumbs
        items={[
          { label: "Tools", to: "/advanced" },
          { label: "Layout Calibrator" },
        ]}
      />
      <h1 className="page-title">Layout Calibrator</h1>
      <p className="page-subtitle">
        Align bubble overlays on the warped answer sheet. Pick 150 or 60 questions, nudge
        coordinates until every circle sits on a printed bubble, then save only if you need a
        custom layout for an exam session.
      </p>

      <SectionMessage appearance="error">{error}</SectionMessage>

      <div className="panel">
        <div className="field-row calib-toolbar">
          <Field label="Answer sheet" htmlFor="calib-sheet-type">
            <select
              id="calib-sheet-type"
              value={sheetType}
              onChange={(e) => {
                const next = e.target.value as SheetTypeValue;
                setSheetType(next);
                setLayoutId(null);
                warpCache.current = null;
                void loadBuiltInTemplate(next);
              }}
            >
              {SHEET_TYPES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </Field>
          <Button onClick={() => loadBuiltInTemplate(sheetType)} disabled={previewBusy}>
            Reset to default
          </Button>
          {savedLayouts.length > 0 && (
            <Field label="Custom layout" htmlFor="calib-layout">
              <select
                id="calib-layout"
                value={layoutId ?? ""}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v) void loadLayout(Number(v));
                  else void loadBuiltInTemplate(sheetType, true);
                }}
              >
                <option value="">Built-in default</option>
                {savedLayouts.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.name}
                  </option>
                ))}
              </select>
            </Field>
          )}
        </div>
      </div>

      {initBusy && <Spinner label="Loading…" />}

      {!initBusy && !template && (
        <EmptyState
          title="No template loaded"
          description="Choose an answer sheet type above."
        />
      )}

      {template && (
        <div className="panel">
          <div className="calib-grid">
            <div className="calib-preview">
              <div className="calib-canvas" style={{ width: DISPLAY_WIDTH, height: pageH * scale }}>
                {warp?.aligned && warp.image ? (
                  <img src={warp.image} alt="warped sheet" style={{ width: DISPLAY_WIDTH }} />
                ) : (
                  <div className="calib-noimg">
                    {previewBusy
                      ? "Rendering…"
                      : "No warped preview (alignment failed or engine offline)."}
                  </div>
                )}
                {overlay?.bubbles.map((b, i) => (
                  <div
                    key={i}
                    className={b.block.startsWith("Roll") ? "bubble bubble-roll" : "bubble bubble-mcq"}
                    style={{
                      left: b.x * scale,
                      top: b.y * scale,
                      width: b.w * scale,
                      height: b.h * scale,
                    }}
                    title={`${b.field_label}=${b.field_value}`}
                  />
                ))}
              </div>
          <Button
            onClick={() => {
              if (template) void refreshPreview(template, sheetType, true);
            }}
            disabled={previewBusy}
          >
                {previewBusy ? "Refreshing…" : "Refresh preview"}
              </Button>
            </div>

            <div className="calib-controls">
              {editingCustom && (
                <Field label="Layout name" htmlFor="calib-name">
                  <input id="calib-name" value={name} onChange={(e) => setName(e.target.value)} />
                </Field>
              )}

              <fieldset>
                <legend>Bubble size (px)</legend>
                <div className="calib-row-group">
                  <NumberRow
                    label="W"
                    value={template.bubbleDimensions[0]}
                    onChange={(v) => updateBubbleDim(0, v)}
                  />
                  <NumberRow
                    label="H"
                    value={template.bubbleDimensions[1]}
                    onChange={(v) => updateBubbleDim(1, v)}
                  />
                </div>
              </fieldset>

              {Object.entries(template.fieldBlocks).map(([blockName, block]) => (
                <fieldset key={blockName}>
                  <legend>
                    {blockName.replace(/_/g, " ")}
                    <span className="muted"> ({block.fieldLabels.join(", ")})</span>
                  </legend>
                  <div className="calib-row-group">
                    <NumberRow
                      label="X"
                      value={block.origin[0]}
                      onChange={(v) => updateBlock(blockName, "origin", 0, v)}
                    />
                    <NumberRow
                      label="Y"
                      value={block.origin[1]}
                      onChange={(v) => updateBlock(blockName, "origin", 1, v)}
                    />
                    <NumberRow
                      label="Bubble gap"
                      value={block.bubblesGap}
                      onChange={(v) => updateBlock(blockName, "bubblesGap", null, v)}
                    />
                    <NumberRow
                      label="Row gap"
                      value={block.labelsGap}
                      onChange={(v) => updateBlock(blockName, "labelsGap", null, v)}
                    />
                  </div>
                </fieldset>
              ))}

              <div className="calib-actions">
                <Button variant="primary" onClick={save} disabled={saveBusy}>
                  {saveBusy
                    ? "Saving…"
                    : editingCustom
                      ? "Update custom layout"
                      : "Save as custom layout"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function NumberRow({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <Field label={label} htmlFor={`num-${label}`}>
      <input
        id={`num-${label}`}
        type="number"
        step="0.5"
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </Field>
  );
}
