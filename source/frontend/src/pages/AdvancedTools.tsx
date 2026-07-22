import { Link } from "react-router-dom";
import PageLayout from "../components/PageLayout";
import Button from "../components/Button";
import Lozenge from "../components/Lozenge";

const TOOLS = [
  {
    id: "calibrator",
    title: "Layout Calibrator",
    description: "Tune OMR bubble layout overlays and save custom templates for answer sheet types.",
    to: "/advanced/calibrator",
    icon: "LC",
  },
  {
    id: "accuracy",
    title: "Accuracy Lab",
    description: "Run OMR against fixtures, tune detection thresholds, and save reference answers for QA.",
    to: "/advanced/accuracy",
    icon: "AL",
    badge: "Developer / QA" as const,
  },
];

export default function AdvancedTools() {
  return (
    <PageLayout
      title="Tools"
      subtitle="Advanced utilities for layout tuning and accuracy validation."
    >
      <div className="tools-grid">
        {TOOLS.map((tool) => (
          <article key={tool.id} className="tool-card">
            <div className="tool-card-icon" aria-hidden="true">
              {tool.icon}
            </div>
            <div className="row gap-2">
              <h2>{tool.title}</h2>
              {tool.badge && (
                <Lozenge appearance="info">{tool.badge}</Lozenge>
              )}
            </div>
            <p>{tool.description}</p>
            <div className="tool-card-footer">
              <Link to={tool.to}>
                <Button variant="primary">Open</Button>
              </Link>
            </div>
          </article>
        ))}
      </div>
    </PageLayout>
  );
}
