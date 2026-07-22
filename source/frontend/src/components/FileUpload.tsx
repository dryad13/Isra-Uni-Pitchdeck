import { useRef, useState } from "react";
import Button from "./Button";
import Spinner from "./Spinner";

type Props = {
  id: string;
  accept?: string;
  disabled?: boolean;
  busy?: boolean;
  onFile: (files: FileList | null) => void;
  hint?: string;
};

export default function FileUpload({
  id,
  accept,
  disabled,
  busy,
  onFile,
  hint,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileName, setFileName] = useState("");

  const pick = () => inputRef.current?.click();

  const handleFiles = (files: FileList | null) => {
    if (!files?.length) return;
    setFileName(files[0].name);
    onFile(files);
  };

  const clear = () => {
    setFileName("");
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div
      className={`file-upload${dragOver ? " file-upload-drag" : ""}${disabled ? " file-upload-disabled" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        id={id}
        type="file"
        accept={accept}
        disabled={disabled || busy}
        className="file-upload-input"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <div className="file-upload-body">
        {busy ? (
          <Spinner label="Uploading…" />
        ) : fileName ? (
          <>
            <span className="file-upload-name">{fileName}</span>
            <Button variant="subtle" type="button" onClick={clear} disabled={disabled}>
              Clear
            </Button>
          </>
        ) : (
          <>
            <span className="muted">{hint ?? "Drag a file here or choose one"}</span>
            <Button variant="default" type="button" onClick={pick} disabled={disabled}>
              Choose file
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
