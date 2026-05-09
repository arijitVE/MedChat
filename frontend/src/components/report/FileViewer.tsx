import { useEffect, useMemo, useRef, useState } from 'react';
import type { MouseEvent as ReactMouseEvent, WheelEvent } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Document, Page, pdfjs } from 'react-pdf';
import {
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  RotateCw,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { reportsApi } from '../../api/reports';
import { normalizeApiError } from '../../lib/apiError';
import { queryKeys, staleTime } from '../../lib/queryKeys';
import { Button } from '../ui/Button';
import { Skeleton } from '../ui/Skeleton';
import { RetryPanel } from '../feedback/RetryPanel';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

interface FileViewerProps {
  reportId: string;
  role: 'doctor' | 'patient';
  mimeType: string;
  className?: string;
}

const zoomOptions = [0.5, 0.75, 1, 1.25, 1.5] as const;

function isPdf(mimeType: string): boolean {
  return mimeType === 'application/pdf';
}

function isImage(mimeType: string): boolean {
  return mimeType.startsWith('image/');
}

export function FileViewer({ reportId, role, mimeType, className = '' }: FileViewerProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [zoom, setZoom] = useState<(typeof zoomOptions)[number]>(1);
  const [rotation, setRotation] = useState(0);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const dragStartRef = useRef({ pointerX: 0, pointerY: 0, x: 0, y: 0 });

  const rawFileQuery = useQuery({
    queryKey: [...queryKeys.reports.rawFile(reportId), role] as const,
    queryFn: async ({ signal }) => {
      try {
        const response = role === 'doctor'
          ? await reportsApi.getRawFile(reportId, { signal })
          : await reportsApi.getMyReportRawFile(reportId, { signal });
        return response.data;
      } catch (error) {
        throw normalizeApiError(error);
      }
    },
    enabled: Boolean(reportId),
    staleTime: staleTime.reportDetail,
  });

  useEffect(() => {
    if (!rawFileQuery.data) {
      setBlobUrl(null);
      return undefined;
    }

    const nextBlobUrl = URL.createObjectURL(rawFileQuery.data);
    setBlobUrl(nextBlobUrl);
    return () => URL.revokeObjectURL(nextBlobUrl);
  }, [rawFileQuery.data]);

  useEffect(() => {
    setPageNumber(1);
    setNumPages(0);
    setZoom(1);
    setRotation(0);
    setPosition({ x: 0, y: 0 });
  }, [reportId]);

  const isLoading = rawFileQuery.isLoading || rawFileQuery.isFetching || !blobUrl;
  const isPdfFile = isPdf(mimeType);
  const isImageFile = isImage(mimeType);
  const imageTransform = useMemo(
    () => `translate(${position.x}px, ${position.y}px) scale(${zoom}) rotate(${rotation}deg)`,
    [position, rotation, zoom],
  );

  const updateZoom = (nextZoom: number) => {
    const clamped = Math.min(Math.max(nextZoom, 0.5), 1.5);
    const nearest = zoomOptions.reduce((closest, option) =>
      Math.abs(option - clamped) < Math.abs(closest - clamped) ? option : closest,
    );
    setZoom(nearest);
  };

  const startDrag = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (!isImageFile) {
      return;
    }

    setIsDragging(true);
    dragStartRef.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      x: position.x,
      y: position.y,
    };
  };

  const moveDrag = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (!isDragging) {
      return;
    }

    const start = dragStartRef.current;
    setPosition({
      x: start.x + event.clientX - start.pointerX,
      y: start.y + event.clientY - start.pointerY,
    });
  };

  const handleWheel = (event: WheelEvent<HTMLDivElement>) => {
    if (!isImageFile) {
      return;
    }

    event.preventDefault();
    updateZoom(zoom + (event.deltaY < 0 ? 0.25 : -0.25));
  };

  if (rawFileQuery.isError) {
    return (
      <RetryPanel
        className={className}
        onRetry={() => void rawFileQuery.refetch()}
        message="Failed to load document"
      />
    );
  }

  if (isLoading) {
    return <Skeleton variant="file" className={className} />;
  }

  if (!blobUrl || (!isPdfFile && !isImageFile)) {
    return (
      <RetryPanel
        className={className}
        onRetry={() => void rawFileQuery.refetch()}
        message="Unsupported document format"
      />
    );
  }

  return (
    <section className={`flex h-full min-h-96 flex-col rounded-lg border border-clinical-border bg-clinical-surface ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-clinical-border px-4 py-3">
        {isPdfFile ? (
          <label className="flex items-center gap-2 text-sm text-clinical-text-secondary">
            Zoom
            <select
              className="rounded-md border border-clinical-border bg-clinical-surface px-2 py-1 text-sm text-clinical-text-primary"
              value={zoom}
              onChange={(event) => setZoom(Number(event.target.value) as (typeof zoomOptions)[number])}
            >
              {zoomOptions.map((option) => (
                <option key={option} value={option}>
                  {Math.round(option * 100)}%
                </option>
              ))}
            </select>
          </label>
        ) : (
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="secondary" className="min-h-8 px-2 py-1" onClick={() => updateZoom(zoom - 0.25)}>
              <ZoomOut className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button variant="secondary" className="min-h-8 px-2 py-1" onClick={() => updateZoom(zoom + 0.25)}>
              <ZoomIn className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button variant="secondary" className="min-h-8 px-2 py-1" onClick={() => setRotation((current) => current - 90)}>
              <RotateCcw className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button variant="secondary" className="min-h-8 px-2 py-1" onClick={() => setRotation((current) => current + 90)}>
              <RotateCw className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              variant="secondary"
              className="min-h-8 px-3 py-1"
              onClick={() => {
                setZoom(1);
                setRotation(0);
                setPosition({ x: 0, y: 0 });
              }}
            >
              Reset
            </Button>
          </div>
        )}
      </div>

      <div
        className={`flex-1 overflow-auto bg-slate-100 p-4 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
        aria-label={isPdfFile ? `Document viewer, page ${pageNumber} of ${numPages || 1}` : 'Uploaded image document'}
        onMouseDown={startDrag}
        onMouseMove={moveDrag}
        onMouseUp={() => setIsDragging(false)}
        onMouseLeave={() => setIsDragging(false)}
        onWheel={handleWheel}
      >
        {isPdfFile ? (
          <Document
            file={blobUrl}
            loading={<Skeleton variant="file" />}
            error={<RetryPanel onRetry={() => void rawFileQuery.refetch()} message="Failed to load PDF" />}
            onLoadSuccess={({ numPages: nextNumPages }: { numPages: number }) => {
              setNumPages(nextNumPages);
              setPageNumber(1);
            }}
          >
            <Page
              pageNumber={pageNumber}
              scale={zoom}
              loading={<Skeleton variant="file" />}
              renderTextLayer={false}
              renderAnnotationLayer={false}
            />
          </Document>
        ) : (
          <div className="flex min-h-full items-center justify-center overflow-hidden">
            <img
              src={blobUrl}
              alt="Uploaded medical document"
              className="max-h-full max-w-full select-none object-contain transition-transform"
              draggable={false}
              style={{ transform: imageTransform }}
            />
          </div>
        )}
      </div>

      {isPdfFile ? (
        <div className="flex items-center justify-center gap-3 border-t border-clinical-border px-4 py-3">
          <Button
            variant="secondary"
            className="min-h-8 px-2 py-1"
            disabled={pageNumber <= 1}
            onClick={() => setPageNumber((current) => Math.max(current - 1, 1))}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          </Button>
          <span className="text-sm text-clinical-text-secondary">
            Page {pageNumber} of {numPages || 1}
          </span>
          <Button
            variant="secondary"
            className="min-h-8 px-2 py-1"
            disabled={pageNumber >= numPages}
            onClick={() => setPageNumber((current) => Math.min(current + 1, numPages))}
          >
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
      ) : null}
    </section>
  );
}
