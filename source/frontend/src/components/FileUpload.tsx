import { useRef, useState } from "react";
import Button from "./Button";
import Spinner from "./Spinner";

type Props = {
  id: string;
  accept?: string;
  disabled?: boolean;
  busy?: boolean;
  onFile: (files: FileList | File[] | null) => void;
  hint?: string;
  allowFolder?: boolean;
};

export default function FileUpload({
  id,
  accept,
  disabled,
  busy,
  onFile,
  hint,
  allowFolder = true,
}: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [summaryText, setSummaryText] = useState("");

  const pickFiles = () => fileInputRef.current?.click();
  const pickFolder = () => folderInputRef.current?.click();

  const handleFiles = (filesInput: FileList | File[] | null) => {
    if (!filesInput) return;
    const fileArray = Array.from(filesInput);
    if (fileArray.length === 0) return;

    if (fileArray.length === 1) {
      setSummaryText(fileArray[0].name);
    } else {
      setSummaryText(`${fileArray.length} scan files selected`);
    }
    onFile(filesInput);
  };

  const clear = () => {
    setSummaryText("");
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (folderInputRef.current) folderInputRef.current.value = "";
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
        ref={fileInputRef}
        id={id}
        type="file"
        multiple
        accept={accept}
        disabled={disabled || busy}
        className="file-upload-input"
        onChange={(e) => handleFiles(e.target.files)}
      />
      {allowFolder && (
        <input
          ref={folderInputRef}
          id={`${id}-folder`}
          type="file"
          // @ts-expect-error webkitdirectory is supported in HTML5 directory selection
          webkitdirectory=""
          directory=""
          multiple
          disabled={disabled || busy}
          className="file-upload-input"
          onChange={(e) => handleFiles(e.target.files)}
        />
      )}
      <div className="file-upload-body">
        {busy ? (
          <Spinner label="Uploading scans…" />
        ) : summaryText ? (
          <>
            <span className="file-upload-name">{summaryText}</span>
            <Button variant="subtle" type="button" onClick={clear} disabled={disabled}>
              Clear
            </Button>
          </>
        ) : (
          <>
            <span className="muted">{hint ?? "Drop scan files or a folder here"}</span>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
              <Button variant="default" type="button" onClick={pickFiles} disabled={disabled}>
                Choose file(s)
              </Button>
              {allowFolder && (
                <Button variant="default" type="button" onClick={pickFolder} disabled={disabled}>
                  Choose folder 📁
                </Button>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

