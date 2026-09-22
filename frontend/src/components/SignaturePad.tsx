import { useRef, useState } from 'react';

import { Button } from './Button';

export interface SignaturePadProps {
  value: File | null;
  onChange: (file: File | null) => void;
  /** Accessible label for the drawing surface (e.g. "Recipient's signature"). */
  label: string;
  clearLabel: string;
}

/**
 * SignaturePad — Design Phase 6 Increment 5 (delivery proof, STANDARD
 * band). Pointer-events canvas draw + Clear, exported as a `File` via
 * `canvas.toBlob()` for the same `FormData` upload path `PhotoCapture` uses.
 */
export function SignaturePad({ value, onChange, label, clearLabel }: SignaturePadProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const drawing = useRef(false);
  const [hasStroke, setHasStroke] = useState(false);

  function ctx(): CanvasRenderingContext2D | null {
    return canvasRef.current?.getContext('2d') ?? null;
  }

  function point(e: React.PointerEvent<HTMLCanvasElement>): { x: number; y: number } {
    const rect = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  }

  function start(e: React.PointerEvent<HTMLCanvasElement>): void {
    const c = ctx();
    if (!c) return;
    drawing.current = true;
    const { x, y } = point(e);
    c.beginPath();
    c.moveTo(x, y);
  }

  function move(e: React.PointerEvent<HTMLCanvasElement>): void {
    if (!drawing.current) return;
    const c = ctx();
    if (!c) return;
    const { x, y } = point(e);
    c.lineTo(x, y);
    c.strokeStyle = '#1F2937';
    c.lineWidth = 2;
    c.lineCap = 'round';
    c.stroke();
    setHasStroke(true);
  }

  function end(): void {
    if (!drawing.current) return;
    drawing.current = false;
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (blob) onChange(new File([blob], 'signature.png', { type: 'image/png' }));
    }, 'image/png');
  }

  function clear(): void {
    const canvas = canvasRef.current;
    const c = ctx();
    if (canvas && c) c.clearRect(0, 0, canvas.width, canvas.height);
    setHasStroke(false);
    onChange(null);
  }

  return (
    <div className="space-y-2">
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={label}
        width={320}
        height={140}
        className="w-full touch-none rounded-md border border-line-strong bg-surface-card"
        onPointerDown={start}
        onPointerMove={move}
        onPointerUp={end}
        onPointerLeave={end}
      />
      {(hasStroke || value) && (
        <Button variant="secondary" size="compact" onClick={clear}>
          {clearLabel}
        </Button>
      )}
    </div>
  );
}
