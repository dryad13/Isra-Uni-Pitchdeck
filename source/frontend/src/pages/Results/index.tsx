import { useState } from "react";
import BatchReview from "./BatchReview";
import SheetsTable from "./SheetsTable";
import PageLayout from "../../components/PageLayout";
import Tabs from "../../components/Tabs";

type Tab = "review" | "sheets";

export default function Results() {
  const [tab, setTab] = useState<Tab>("review");

  return (
    <PageLayout
      title="Results"
      subtitle="Review flagged sheets by roll or browse all processed sheets for a session."
    >
      <Tabs
        variant="toolbar"
        ariaLabel="Results views"
        items={[
          { id: "review", label: "Batch review" },
          { id: "sheets", label: "All sheets" },
        ]}
        activeId={tab}
        onChange={(id) => setTab(id as Tab)}
      />

      {tab === "review" ? (
        <BatchReview embedded />
      ) : (
        <SheetsTable onReview={() => setTab("review")} />
      )}
    </PageLayout>
  );
}
