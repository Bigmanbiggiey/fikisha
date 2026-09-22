import { useEffect, useRef, useState } from 'react';

import { Button } from './Button';

export interface PhotoCaptureProps {
  value: File | null;
  onChange: (file: File | null) => void;
  /** The camera button's accessible label (e.g. "Take photo of the goods"). */
  label: string;
  retakeLabel: string;
  /** Announced via `role="status"` once a photo is captured. */
  addedLabel: string;
}

/**
 * PhotoCapture — Design Phase 6 Increment 5. Camera-first file input
 * (`capture="environment"`) + thumbnail + retake. `[local-ok]`: capturing a
 * photo never itself talks to the server — the surrounding form's submit
 * is the `[server]` action.
 *
 * Scoped down from the wireframe component inventory's full spec: no
 * client-side compression to WebP (documented simplification, not a
 * silent omission — the backend accepts whatever the browser produces).
 */
export function PhotoCapture({ value, onChange, label, retakeLabel, addedLabel }: PhotoCaptureProps): JSX.Element {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!value) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(value);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [value]);

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        aria-label={label}
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      {value && previewUrl ? (
        <div className="space-y-2">
          <img src={previewUrl} alt="" className="h-40 w-full rounded-md border border-line object-cover" />
          <p role="status" className="text-body-sm text-status-success-fg">
            {addedLabel}
          </p>
          <Button
            variant="secondary"
            size="compact"
            onClick={() => {
              onChange(null);
              if (inputRef.current) inputRef.current.value = '';
            }}
          >
            {retakeLabel}
          </Button>
        </div>
      ) : (
        <Button variant="secondary" fullWidth onClick={() => inputRef.current?.click()}>
          {label}
        </Button>
      )}
    </div>
  );
}
