import { useRef, useState } from 'react';

interface SignaturePadProps {
  onCapture: (signatureSvg: string) => void;
}

/**
 * Finger/stylus signature capture on an HTML canvas. The stroked bitmap is
 * exported as a PNG data URI wrapped in an SVG `<image>` element, which is
 * what the backend stores as `signature_svg` alongside the consent submission.
 */
export function SignaturePad({ onCapture }: SignaturePadProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const isDrawingRef = useRef(false);
  const lastPointRef = useRef<{ x: number; y: number } | null>(null);
  const [hasStroke, setHasStroke] = useState(false);

  function getContext(): CanvasRenderingContext2D | null {
    return canvasRef.current?.getContext('2d') ?? null;
  }

  function pointFromEvent(event: React.PointerEvent<HTMLCanvasElement>): { x: number; y: number } {
    const rect = canvasRef.current!.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  function handlePointerDown(event: React.PointerEvent<HTMLCanvasElement>) {
    isDrawingRef.current = true;
    lastPointRef.current = pointFromEvent(event);
  }

  function handlePointerMove(event: React.PointerEvent<HTMLCanvasElement>) {
    if (!isDrawingRef.current) return;
    const context = getContext();
    const point = pointFromEvent(event);
    if (!context || !lastPointRef.current) return;
    context.strokeStyle = '#0f172a';
    context.lineWidth = 2.5;
    context.lineCap = 'round';
    context.beginPath();
    context.moveTo(lastPointRef.current.x, lastPointRef.current.y);
    context.lineTo(point.x, point.y);
    context.stroke();
    lastPointRef.current = point;
    setHasStroke(true);
  }

  function handlePointerUp() {
    isDrawingRef.current = false;
    lastPointRef.current = null;
  }

  function clear() {
    const canvas = canvasRef.current;
    const context = getContext();
    if (canvas && context) {
      context.clearRect(0, 0, canvas.width, canvas.height);
    }
    setHasStroke(false);
  }

  function confirm() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const pngDataUrl = canvas.toDataURL('image/png');
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${canvas.width}" height="${canvas.height}"><image href="${pngDataUrl}" width="${canvas.width}" height="${canvas.height}" /></svg>`;
    onCapture(svg);
  }

  return (
    <div className="flex flex-col gap-3">
      <canvas
        ref={canvasRef}
        width={340}
        height={180}
        className="touch-none rounded-lg border-2 border-dashed border-slate-300 bg-white"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      />
      <div className="flex gap-3">
        <button
          type="button"
          onClick={clear}
          className="flex-1 rounded-lg border border-slate-300 py-3 text-sm font-medium"
        >
          Borrar
        </button>
        <button
          type="button"
          onClick={confirm}
          disabled={!hasStroke}
          className="flex-1 rounded-lg bg-slate-900 py-3 text-sm font-semibold text-white disabled:opacity-40"
        >
          Confirmar firma
        </button>
      </div>
    </div>
  );
}
