type Appearance = "default" | "success" | "warning" | "danger" | "info" | "progress";

export default function Lozenge({
  children,
  appearance = "default",
}: {
  children: React.ReactNode;
  appearance?: Appearance;
}) {
  return <span className={`lozenge lozenge-${appearance}`}>{children}</span>;
}
