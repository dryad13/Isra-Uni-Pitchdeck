type Variant = "primary" | "default" | "subtle" | "danger" | "link" | "danger-link";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

export default function Button({ variant = "default", className = "", ...rest }: Props) {
  const variantClass =
    variant === "default"
      ? ""
      : variant === "link"
        ? "btn-link"
        : variant === "danger-link"
          ? "btn-danger-link"
          : `btn-${variant}`;
  return <button className={`btn ${variantClass} ${className}`.trim()} {...rest} />;
}
