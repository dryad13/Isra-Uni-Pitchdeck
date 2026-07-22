import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { api } from "../lib/api";
import Button from "../components/Button";
import Breadcrumbs from "../components/Breadcrumbs";
import EmptyState from "../components/EmptyState";
import Lozenge from "../components/Lozenge";
import PageLayout from "../components/PageLayout";
import { useBusy } from "../hooks/useBusy";

type PerQuestion = {
  global_q: number;
  sheet_q: number;
  option: string;
  key: string | null;
  status: string;
};

type SheetDetail = {
  id: number;
  batch_id: number;
  roll_no: string | null;
  counts: Record<string, unknown>;
  has_source_image: boolean;
  scored: {
    percentage: number;
    secure_score: number;
    per_question: PerQuestion[];
  } | null;
  verification_items: {
    id: number;
    anomaly_type: string;
    status: string;
    detected_values: string | null;
    resolved_by: string | null;
  }[];
};

function statusAppearance(status: string): "success" | "warning" | "danger" | "info" {
  switch (status) {
    case "correct":
      return "success";
    case "wrong":
      return "danger";
    case "multi":
      return "warning";
    default:
      return "info";
  }
}

export default function SheetDetail() {
  const { sheetId } = useParams<{ sheetId: string }>();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from;
  const backLabel = from === "results" ? "Results" : "Reports";
  const backTo = from === "results" ? "/verify" : "/export";
  const loadBusy = useBusy();
  const [detail, setDetail] = useState<SheetDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sheetId) return;
    loadBusy
      .run(async () => {
        const data = await api<SheetDetail>(`/sheets/${sheetId}`);
        setDetail(data);
      })
      .catch((e) => setError((e as Error).message));
  }, [sheetId]);

  return (
    <PageLayout
      title="Sheet audit"
      subtitle="Per-question read vs key for a single processed sheet."
      error={error}
      loading={loadBusy.busy}
      loadingLabel="Loading sheet…"
      breadcrumbs={
        <Breadcrumbs
          items={[
            { label: backLabel, to: backTo },
            { label: sheetId ? `Sheet #${sheetId}` : "Sheet" },
          ]}
        />
      }
      actions={
        <Link to={backTo}>
          <Button variant="subtle">Back to {backLabel}</Button>
        </Link>
      }
      empty={
        !loadBusy.busy && !detail && !error
          ? { title: "Sheet not found", description: "This sheet may have been deleted." }
          : null
      }
    >
      {detail && !loadBusy.busy && (
        <>
          <div className="panel mb-6">
            <p>
              <strong>Roll:</strong> {detail.roll_no ?? "-"} &middot; <strong>Batch:</strong> #
              {detail.batch_id}
            </p>
            {detail.scored && (
              <p className="muted">
                Score {detail.scored.percentage}% &middot; Secure {detail.scored.secure_score}%
              </p>
            )}
            {detail.verification_items.length > 0 && (
              <div className="row mt-4 gap-2" style={{ flexWrap: "wrap" }}>
                {detail.verification_items.map((v) => (
                  <Lozenge key={v.id} appearance={v.status === "pending" ? "warning" : "info"}>
                    {v.anomaly_type} ({v.status})
                  </Lozenge>
                ))}
              </div>
            )}
            {detail.has_source_image && (
              <img
                className="crop-img mt-5"
                style={{ maxWidth: "100%" }}
                src={`/api/sheets/${detail.id}/source-image`}
                alt="source scan"
              />
            )}
          </div>

          {detail.scored ? (
            <div className="panel">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Global Q</th>
                    <th>Sheet Q</th>
                    <th>Read</th>
                    <th>Key</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.scored.per_question.map((q) => (
                    <tr key={q.global_q}>
                      <td>Q{q.global_q}</td>
                      <td>{q.sheet_q}</td>
                      <td>{q.option || "Blank"}</td>
                      <td>{q.key ?? "-"}</td>
                      <td>
                        <Lozenge appearance={statusAppearance(q.status)}>{q.status}</Lozenge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              title="Sheet not scorable"
              description="This sheet is excluded or pending alignment review."
            />
          )}
        </>
      )}
    </PageLayout>
  );
}
