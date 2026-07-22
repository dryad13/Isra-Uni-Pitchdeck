type Appearance = "error" | "success" | "info" | "warning";

export default function SectionMessage({
  appearance,
  children,
}: {
  appearance: Appearance;
  children: React.ReactNode;
}) {
  if (!children) return null;
  return <div className={`section-message section-message-${appearance}`}>{children}</div>;
}
