import { useRef, useState } from 'react';
import type { DragEvent, InputHTMLAttributes } from 'react';
import { Upload } from 'lucide-react';
import { Button } from '../ui/Button';
import { normalizeApiError } from '../../lib/apiError';
import { uploadSchema } from '../../validation/uploadSchemas';
import type { ApiError } from '../../lib/apiError';
import type { Report, UploadResponse } from '../../types/report';

type UploadResult = Report | UploadResponse;

interface UploadDropzoneProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'onChange' | 'onError' | 'onProgress'> {
  patientUid: string;
  disabled?: boolean;
  onFileSelected?: (file: File) => void;
  onUpload?: (file: File, options: { force?: boolean; onProgress: (progress: number) => void }) => Promise<UploadResult>;
  onProgress?: (progress: number) => void;
  onDuplicate?: (error: ApiError) => void;
  onSuccess?: (report: UploadResult) => void;
  onError?: (error: ApiError) => void;
  className?: string;
}

export function UploadDropzone({
  patientUid,
  disabled = false,
  onFileSelected,
  onUpload,
  onProgress,
  onDuplicate,
  onSuccess,
  onError,
  className = '',
  ...inputProps
}: UploadDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const processFile = async (file: File) => {
    const parsed = uploadSchema.safeParse({ patient_uid: patientUid, file });
    if (!parsed.success) {
      setValidationError(parsed.error.issues[0]?.message ?? 'Invalid upload');
      return;
    }

    setValidationError(null);
    onFileSelected?.(file);

    if (!onUpload) {
      return;
    }

    try {
      setIsUploading(true);
      const report = await onUpload(file, {
        onProgress: (progress) => {
          onProgress?.(progress);
        },
      });
      onSuccess?.(report);
    } catch (error) {
      const apiError = normalizeApiError(error);
      if (apiError.code === 'DUPLICATE_EXACT' && onDuplicate) {
        onDuplicate?.(apiError);
      } else {
        onError?.(apiError);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files.item(0);
    if (file) {
      void processFile(file);
    }
  };

  return (
    <div
      className={`rounded-lg border border-dashed p-8 text-center transition-colors ${
        isDragging ? 'border-clinical-primary bg-clinical-primary-light' : 'border-clinical-border bg-clinical-surface'
      } ${disabled ? 'opacity-60' : ''} ${className}`}
      onDragOver={(event) => {
        event.preventDefault();
        if (!disabled) {
          setIsDragging(true);
        }
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(event) => {
        if (!disabled) {
          handleDrop(event);
        }
      }}
    >
      <input
        ref={inputRef}
        type="file"
        className="sr-only"
        disabled={disabled || isUploading}
        accept="application/pdf,image/jpeg,image/png,image/tiff"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) {
            void processFile(file);
          }
          event.target.value = '';
        }}
        {...inputProps}
      />
      <Upload className="mx-auto h-8 w-8 text-clinical-primary" aria-hidden="true" />
      <p className="mt-3 text-sm font-medium text-clinical-text-primary">
        Drop a PDF or image report here
      </p>
      <p className="mt-1 text-sm text-clinical-text-secondary">
        PDF, JPEG, PNG, or TIFF up to 50MB
      </p>
      {validationError ? (
        <p className="mt-3 text-sm text-clinical-critical" role="alert" aria-live="assertive">
          {validationError}
        </p>
      ) : null}
      <Button
        className="mt-4"
        variant="secondary"
        loading={isUploading}
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
      >
        Choose file
      </Button>
    </div>
  );
}
