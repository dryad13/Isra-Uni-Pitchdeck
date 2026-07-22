import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Breadcrumbs from "../components/Breadcrumbs";
import Button from "../components/Button";
import EmptyState from "../components/EmptyState";
import Field from "../components/Field";
import SectionMessage from "../components/SectionMessage";
import Spinner from "../components/Spinner";
import { useToast } from "../components/Toast";
import { useBusy } from "../hooks/useBusy";
import { api, upload } from "../lib/api";
import { SHEET_TYPES, type SheetTypeValue } from "./OperatorDashboard/types";

type Fixture = {
  id: string;
  label: string;
  template_family: string;
  sheet_question_count: number;
  kind: "filled" | "blank";
  available: boolean;
};

type ThresholdDefaults = {
  fill_threshold: number;
  blank_threshold: number;
  multi_mark_threshold: number;
  comfort_margin: number;
  comfort_ratio: number;
  alignment_review_below: number;
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

type QuestionRow = {
  sheet_q: number;
  detected: string;
  template_detected?: string;
  contour_detected?: string;
  final_detected?: string;
  method?: string | null;
  status: string;
  fills: Record<string, number>;
  contour_fills?: Record<string, number>;
  low_confidence?: boolean;
  hard_multi?: boolean;
  reference: string | null;
  match: boolean | null;
};

type DetectedBubble = {
  block: string;
  cx: number;
  cy: number;
  w: number;
  h: number;
};

type RunResult = {
  fixture_id: string | null;
  aligned: boolean;
  alignment_quality: number;
  roll_no: string | null;
  roll_status: string | null;
  timing_ms: number;
  thresholds_used: ThresholdDefaults;
  dynamic_threshold: number | null;
  grid_refined: boolean;
  grid_confidence?: number | null;
  fallback_used?: boolean;
  contour_agreement_pct?: number | null;
  read_method_summary?: string | null;
  detected_bubbles?: DetectedBubble[];
  questions: QuestionRow[];
  summary: {
    total: number;
    answered: number;
    blank: number;
    multi: number;
    anomalies: number;
    accuracy_pct: number | null;
    roll_match: boolean | null;
    compared?: number;
    matched?: number;
    mismatches?: number;
  };
  warp_preview: string | null;
  overlay: {
    page_dimensions: [number, number];
    bubbles: Bubble[];
  } | null;
};

type LayoutSummary = {
  id: number;
  template_family: string;
  name: string;
};

type FilterMode = "all" | "mismatch" | "low_confidence" | "multi" | "blank";

const MAX_PREVIEW_WIDTH = 460;
const MIN_PREVIEW_WIDTH = 200;
const OPTIONS = ["", "A", "B", "C", "D"] as const;

const THRESHOLD_FIELDS: { key: keyof ThresholdDefaults; label: string; min: number; max: number; step: number }[] = [
  { key: "fill_threshold", label: "Fill threshold", min: 10, max: 120, step: 1 },
  { key: "blank_threshold", label: "Blank separation", min: 5, max: 80, step: 1 },
  { key: "multi_mark_threshold", label: "Multi-mark margin", min: 2, max: 60, step: 1 },
  { key: "comfort_margin", label: "Comfort margin", min: 5, max: 80, step: 1 },
  { key: "comfort_ratio", label: "Comfort ratio", min: 1, max: 3, step: 0.05 },
];

function bubbleClass(q: QuestionRow): string {
  if (q.match === true) return "bubble bubble-match";
  if (q.match === false) return "bubble bubble-mismatch";
  if (q.hard_multi || q.status === "multi") return "bubble bubble-warn";
  if (q.low_confidence) return "bubble bubble-warn";
  if (q.status === "blank") return "bubble bubble-blank";
  return "bubble bubble-mcq";
}

export default function AccuracyLab() {
  const toast = useToast();
  const { busy: initBusy, run: runInit } = useBusy();
  const { busy: runBusy, run: runValidation } = useBusy();
  const { busy: saveBusy, run: runSave } = useBusy();
  const fileRef = useRef<HTMLInputElement>(null);
  const previewWrapRef = useRef<HTMLDivElement>(null);
  const [previewWidth, setPreviewWidth] = useState(MIN_PREVIEW_WIDTH);

  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [thresholdDefaults, setThresholdDefaults] = useState<ThresholdDefaults | null>(null);
  const [thresholds, setThresholds] = useState<ThresholdDefaults | null>(null);
  const [sourceKind, setSourceKind] = useState<"fixture" | "upload">("fixture");
  const [fixtureId, setFixtureId] = useState("sample_scan");
  const [uploadId, setUploadId] = useState<string | null>(null);
  const [uploadName, setUploadName] = useState("");
  const [sheetType, setSheetType] = useState<SheetTypeValue>("150Q");
  const [layoutId, setLayoutId] = useState<number | null>(null);
  const [layouts, setLayouts] = useState<LayoutSummary[]>([]);
  const [sheetQuestionCount, setSheetQuestionCount] = useState(150);
  const [result, setResult] = useState<RunResult | null>(null);
  const [editedAnswers, setEditedAnswers] = useState<Record<string, string>>({});
  const [editedRoll, setEditedRoll] = useState("");
  const [filter, setFilter] = useState<FilterMode>("all");
  const [error, setError] = useState("");

  const loadFixtures = useCallback(async () => {
    const data = await api<{ fixtures: Fixture[]; threshold_defaults: ThresholdDefaults }>(
      "/accuracy/fixtures",
    );
    setFixtures(data.fixtures);
    setThresholdDefaults(data.threshold_defaults);
    setThresholds(data.threshold_defaults);
    const first = data.fixtures.find((f) => f.available);
    if (first) {
      setFixtureId(first.id);
      setSheetType(first.template_family as SheetTypeValue);
      setSheetQuestionCount(first.sheet_question_count);
    }
  }, []);

  useEffect(() => {
    void runInit(async () => {
      try {
        await loadFixtures();
        const layoutData = await api<{ layouts: LayoutSummary[] }>("/templates");
        setLayouts(layoutData.layouts);
      } catch (e) {
        setError((e as Error).message);
      }
    });
  }, [loadFixtures, runInit]);

  useEffect(() => {
    const el = previewWrapRef.current;
    if (!el) return;

    const updateWidth = () => {
      const available = el.clientWidth;
      if (available <= 0) return;
      setPreviewWidth(
        Math.min(MAX_PREVIEW_WIDTH, Math.max(MIN_PREVIEW_WIDTH, Math.floor(available))),
      );
    };

    updateWidth();
    const ro = new ResizeObserver(updateWidth);
    ro.observe(el);
    return () => ro.disconnect();
  }, [result]);

  const pageW = result?.overlay?.page_dimensions[0] ?? 1080;
  const pageH = result?.overlay?.page_dimensions[1] ?? 1593;

  const scale = useMemo(() => previewWidth / pageW, [previewWidth, pageW]);

  const filteredQuestions = useMemo(() => {
    if (!result) return [];
    return result.questions.filter((q) => {
      if (filter === "mismatch") return q.match === false;
      if (filter === "low_confidence") return q.low_confidence;
      if (filter === "multi") return q.status === "multi" || q.hard_multi;
      if (filter === "blank") return q.status === "blank";
      return true;
    });
  }, [result, filter]);

  const syncEditsFromResult = useCallback((res: RunResult) => {
    const answers: Record<string, string> = {};
    for (const q of res.questions) {
      answers[String(q.sheet_q)] = q.reference ?? q.detected ?? "";
    }
    setEditedAnswers(answers);
    setEditedRoll(res.roll_no ?? "");
  }, []);

  const runScan = useCallback(async () => {
    setError("");
    if (!thresholds) return;
    try {
      const body = {
        template_family: sheetType,
        layout_id: layoutId,
        sheet_question_count: sheetQuestionCount,
        include_warp_preview: true,
        threshold_overrides: thresholds,
        ...(sourceKind === "fixture" ? { fixture_id: fixtureId } : { upload_id: uploadId }),
      };
      const res = await runValidation(() =>
        api<RunResult>("/accuracy/run", {
          method: "POST",
          body: JSON.stringify(body),
        }),
      );
      setResult(res);
      syncEditsFromResult(res);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [
    thresholds,
    sheetType,
    layoutId,
    sheetQuestionCount,
    sourceKind,
    fixtureId,
    uploadId,
    runValidation,
    syncEditsFromResult,
  ]);

  const handleFixtureChange = (id: string) => {
    setFixtureId(id);
    const fx = fixtures.find((f) => f.id === id);
    if (fx) {
      setSheetType(fx.template_family as SheetTypeValue);
      setSheetQuestionCount(fx.sheet_question_count);
    }
  };

  const handleUpload = async (file: File) => {
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await upload<{ upload_id: string; filename: string }>(
        "/accuracy/upload",
        form,
      );
      setUploadId(res.upload_id);
      setUploadName(res.filename);
      setSourceKind("upload");
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const saveReference = async () => {
    const id = sourceKind === "fixture" ? fixtureId : uploadId;
    if (!id) {
      toast.error("Select a scan before saving a reference.");
      return;
    }
    try {
      await runSave(() =>
        api(`/accuracy/reference/${id}`, {
          method: "PUT",
          body: JSON.stringify({
            template_family: sheetType,
            roll_no: editedRoll || null,
            answers: editedAnswers,
          }),
        }),
      );
      toast.success("Reference saved.");
      await runScan();
    } catch (e) {
      toast.error((e as Error).message);
    }
  };

  const resetThresholds = () => {
    if (thresholdDefaults) setThresholds({ ...thresholdDefaults });
  };

  const savedLayouts = useMemo(
    () => layouts.filter((l) => l.template_family === sheetType),
    [layouts, sheetType],
  );

  const activeFixture = fixtures.find((f) => f.id === fixtureId);
  const isBlankFixture = activeFixture?.kind === "blank";

  return (
    <section>
      <Breadcrumbs
        items={[
          { label: "Tools", to: "/advanced" },
          { label: "Accuracy Lab" },
        ]}
      />
      <h1 className="page-title">Accuracy Lab</h1>
      <p className="page-subtitle">
        Run the OMR pipeline against live-scanner fixtures, tune thresholds for your Canon
        output, confirm reads as ground truth, and track accuracy on re-runs.
      </p>

      <SectionMessage appearance="error">{error}</SectionMessage>

      {initBusy && <Spinner label="Loading fixtures…" />}

      {!initBusy && (
        <div className="accuracy-lab">
          <div className="accuracy-sidebar panel">
            <h2 className="panel-heading">Scan &amp; settings</h2>

            <Field label="Scan source" htmlFor="acc-source">
              <select
                id="acc-source"
                value={sourceKind === "fixture" ? fixtureId : "__upload__"}
                onChange={(e) => {
                  const v = e.target.value;
                  if (v === "__upload__") {
                    setSourceKind("upload");
                  } else {
                    setSourceKind("fixture");
                    handleFixtureChange(v);
                  }
                }}
              >
                {fixtures.map((f) => (
                  <option key={f.id} value={f.id} disabled={!f.available}>
                    {f.label}
                    {!f.available ? " (missing)" : ""}
                  </option>
                ))}
                {uploadId && (
                  <option value="__upload__">Custom upload — {uploadName}</option>
                )}
                {!uploadId && <option value="__upload__">Custom upload…</option>}
              </select>
            </Field>

            <input
              ref={fileRef}
              type="file"
              accept=".jpg,.jpeg,.png,.tif,.tiff"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) void handleUpload(file);
                e.target.value = "";
              }}
            />
            <Button onClick={() => fileRef.current?.click()}>
              Upload scan
            </Button>

            <Field label="Template family" htmlFor="acc-family">
              <select
                id="acc-family"
                value={sheetType}
                onChange={(e) => {
                  setSheetType(e.target.value as SheetTypeValue);
                  setLayoutId(null);
                }}
              >
                {SHEET_TYPES.map((s) => (
                  <option key={s.value} value={s.value}>
                    {s.label}
                  </option>
                ))}
              </select>
            </Field>

            {savedLayouts.length > 0 && (
              <Field label="Layout" htmlFor="acc-layout">
                <select
                  id="acc-layout"
                  value={layoutId ?? ""}
                  onChange={(e) => setLayoutId(e.target.value ? Number(e.target.value) : null)}
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

            <Field label="Questions on sheet" htmlFor="acc-qcount">
              <input
                id="acc-qcount"
                type="number"
                min={1}
                max={150}
                value={sheetQuestionCount}
                onChange={(e) => setSheetQuestionCount(Number(e.target.value))}
              />
            </Field>

            <fieldset className="accuracy-thresholds">
              <legend>Threshold tuning</legend>
              {thresholds &&
                THRESHOLD_FIELDS.map(({ key, label, min, max, step }) => (
                  <Field key={key} label={`${label} (${thresholds[key]})`} htmlFor={`thr-${key}`}>
                    <input
                      id={`thr-${key}`}
                      type="range"
                      min={min}
                      max={max}
                      step={step}
                      value={thresholds[key]}
                      onChange={(e) =>
                        setThresholds((prev) =>
                          prev ? { ...prev, [key]: Number(e.target.value) } : prev,
                        )
                      }
                    />
                  </Field>
                ))}
              <div className="calib-actions">
                <Button onClick={resetThresholds}>
                  Reset thresholds
                </Button>
                <Button
                  variant="primary"
                  onClick={() => void runScan()}
                  disabled={runBusy || (sourceKind === "upload" && !uploadId)}
                >
                  {runBusy ? "Running…" : "Run validation"}
                </Button>
              </div>
            </fieldset>
          </div>

          <div className="accuracy-center panel">
            <h2 className="panel-heading">Warp preview</h2>
            {!result && (
              <EmptyState
                title="No run yet"
                description="Pick a fixture and run validation to see alignment and bubble overlay."
              />
            )}
            {result && (
              <>
                <div className="accuracy-badges">
                  <span className={result.aligned ? "badge badge-ok" : "badge badge-bad"}>
                    {result.aligned ? "Aligned" : "Alignment failed"}
                  </span>
                  <span className="badge">Quality {result.alignment_quality.toFixed(2)}</span>
                  {result.dynamic_threshold != null && (
                    <span className="badge">Dyn threshold {result.dynamic_threshold}</span>
                  )}
                  {result.grid_refined && <span className="badge">Grid refined</span>}
                  <span className="badge">{result.timing_ms} ms</span>
                </div>
                <div className="accuracy-preview-wrap" ref={previewWrapRef}>
                  <div
                    className="calib-canvas accuracy-canvas"
                    style={{ width: previewWidth, height: pageH * scale }}
                  >
                    {result.warp_preview ? (
                      <img src={result.warp_preview} alt="warped scan" />
                    ) : (
                      <div className="calib-noimg">No warp preview</div>
                    )}
                    {result.overlay?.bubbles.map((b, i) => {
                      const sheetQ = Number(/\d+/.exec(b.field_label)?.[0] ?? 0);
                      const q = result.questions.find((row) => row.sheet_q === sheetQ);
                      const cls = q ? bubbleClass(q) : "bubble bubble-mcq";
                      return (
                        <div
                          key={i}
                          className={cls}
                          style={{
                            left: b.x * scale,
                            top: b.y * scale,
                            width: b.w * scale,
                            height: b.h * scale,
                          }}
                          title={`Q${sheetQ} ${b.field_value}`}
                        />
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </div>

          <div className="accuracy-results panel">
            <h2 className="panel-heading">Results &amp; reference</h2>
            {!result && (
              <EmptyState
                title="Awaiting run"
                description="Summary metrics and per-question edits appear here after validation."
              />
            )}
            {result && (
              <>
                <div className="accuracy-summary">
                  {result.read_method_summary && (
                    <div className="accuracy-stat">
                      <span className="accuracy-stat-value">{result.read_method_summary}</span>
                      <span className="accuracy-stat-label">Read mode</span>
                    </div>
                  )}
                  {result.grid_confidence != null && (
                    <div className="accuracy-stat">
                      <span className="accuracy-stat-value">
                        {Math.round(result.grid_confidence * 100)}%
                      </span>
                      <span className="accuracy-stat-label">Grid confidence</span>
                    </div>
                  )}
                  {!isBlankFixture && result.summary.accuracy_pct != null && (
                    <div className="accuracy-stat">
                      <span className="accuracy-stat-value">{result.summary.accuracy_pct}%</span>
                      <span className="accuracy-stat-label">Accuracy</span>
                    </div>
                  )}
                  <div className="accuracy-stat">
                    <span className="accuracy-stat-value">{result.summary.answered}</span>
                    <span className="accuracy-stat-label">Answered</span>
                  </div>
                  <div className="accuracy-stat">
                    <span className="accuracy-stat-value">{result.summary.blank}</span>
                    <span className="accuracy-stat-label">Blank</span>
                  </div>
                  <div className="accuracy-stat">
                    <span className="accuracy-stat-value">{result.summary.multi}</span>
                    <span className="accuracy-stat-label">Multi</span>
                  </div>
                  <div className="accuracy-stat">
                    <span className="accuracy-stat-value">{result.summary.anomalies}</span>
                    <span className="accuracy-stat-label">Anomalies</span>
                  </div>
                </div>

                <Field label="Roll number (reference)" htmlFor="acc-roll">
                  <input
                    id="acc-roll"
                    value={editedRoll}
                    onChange={(e) => setEditedRoll(e.target.value)}
                    placeholder={result.roll_no ?? "Roll"}
                  />
                </Field>
                {result.summary.roll_match != null && (
                  <p className={result.summary.roll_match ? "calib-status" : "calib-error"}>
                    Roll {result.summary.roll_match ? "matches" : "mismatch vs reference"} (
                    detected {result.roll_no ?? "—"})
                  </p>
                )}

                <div className="accuracy-filter">
                  {(
                    [
                      ["all", "All"],
                      ["mismatch", "Mismatches"],
                      ["low_confidence", "Low confidence"],
                      ["multi", "Multi"],
                      ["blank", "Blank"],
                    ] as const
                  ).map(([mode, label]) => (
                    <button
                      key={mode}
                      type="button"
                      className={filter === mode ? "filter-chip active" : "filter-chip"}
                      onClick={() => setFilter(mode)}
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className="table-wrap accuracy-table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Q</th>
                        <th>Contour</th>
                        <th>Template</th>
                        <th>Final</th>
                        <th>Method</th>
                        <th>Fills</th>
                        <th>Reference</th>
                        <th>Match</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredQuestions.map((q) => (
                        <tr
                          key={q.sheet_q}
                          className={
                            q.match === false
                              ? "row-mismatch"
                              : q.low_confidence || q.hard_multi
                                ? "row-warn"
                                : undefined
                          }
                        >
                          <td>{q.sheet_q}</td>
                          <td>{q.contour_detected || "—"}</td>
                          <td>{q.template_detected || "—"}</td>
                          <td>
                            {q.final_detected || q.detected || "—"}
                            {q.low_confidence && <span className="muted"> low</span>}
                            {q.hard_multi && <span className="muted"> multi</span>}
                          </td>
                          <td>{q.method || "—"}</td>
                          <td className="fill-bars">
                            {(["A", "B", "C", "D"] as const).map((opt) => {
                              const val = q.fills[opt] ?? 0;
                              const max = Math.max(...Object.values(q.fills), 1);
                              return (
                                <span key={opt} className="fill-bar" title={`${opt}: ${val}`}>
                                  <span
                                    className="fill-bar-inner"
                                    style={{ width: `${(val / max) * 100}%` }}
                                  />
                                  <span className="fill-bar-label">{opt}</span>
                                </span>
                              );
                            })}
                          </td>
                          <td>
                            <select
                              value={editedAnswers[String(q.sheet_q)] ?? ""}
                              onChange={(e) =>
                                setEditedAnswers((prev) => ({
                                  ...prev,
                                  [String(q.sheet_q)]: e.target.value,
                                }))
                              }
                            >
                              {OPTIONS.map((opt) => (
                                <option key={opt || "blank"} value={opt}>
                                  {opt || "blank"}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            {q.match == null ? "—" : q.match ? "✓" : "✗"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {!isBlankFixture && (
                  <div className="calib-actions">
                    <Button variant="primary" onClick={() => void saveReference()} disabled={saveBusy}>
                      {saveBusy ? "Saving…" : "Save as reference"}
                    </Button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
