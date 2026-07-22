type Props = {
  options: string[];
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  labels?: Record<string, string>;
};

export default function OptionToggleGroup({
  options,
  value,
  onChange,
  disabled = false,
  labels = {},
}: Props) {
  return (
    <div className="option-toggle-group" role="group" aria-label="Answer options">
      {options.map((opt) => {
        const label = labels[opt] ?? opt;
        const pressed = value === opt;
        return (
          <button
            key={opt}
            type="button"
            className="option-toggle"
            aria-pressed={pressed}
            disabled={disabled}
            onClick={() => onChange(opt)}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
