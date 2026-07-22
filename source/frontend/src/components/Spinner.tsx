type Props = {
  size?: "sm" | "md";
  label?: string;
};

export default function Spinner({ size = "sm", label }: Props) {
  return (
    <span className={`spinner spinner-${size}`} role="status" aria-label={label ?? "Loading"}>
      <span className="spinner-ring" />
      {label && <span className="spinner-label">{label}</span>}
    </span>
  );
}
