import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DuplicateWarningModal } from '../../components/report/DuplicateWarningModal';
import { UploadDropzone } from '../../components/report/UploadDropzone';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Toast } from '../../components/ui/Toast';
import { useUploadReport } from '../../hooks/useReports';
import { normalizeApiError } from '../../lib/apiError';
import type { ApiError } from '../../lib/apiError';
import type { DuplicateWarning, ExactDuplicateError, Report } from '../../types/report';

type DuplicateState =
  | {
      type: 'exact';
      existingReportId: string;
      existingUploadedAt: string;
      uploadedByRole: 'doctor' | 'patient';
    }
  | {
      type: 'probable';
      existingReportId: string;
      existingUploadedAt: string;
      uploadedByRole: 'doctor' | 'patient';
    };

function exactDuplicateFromError(error: ApiError): DuplicateState | null {
  const raw = error.raw as Partial<ExactDuplicateError> | undefined;
  if (!raw?.existing_report_id || !raw.existing_uploaded_at || !raw.uploaded_by_role) {
    return null;
  }

  return {
    type: 'exact',
    existingReportId: raw.existing_report_id,
    existingUploadedAt: raw.existing_uploaded_at,
    uploadedByRole: raw.uploaded_by_role,
  };
}

function probableDuplicateFromReport(warning: DuplicateWarning): DuplicateState {
  return {
    type: 'probable',
    existingReportId: warning.existing_report_id,
    existingUploadedAt: warning.existing_uploaded_at,
    uploadedByRole: warning.uploaded_by_role,
  };
}

export default function UploadPage() {
  const navigate = useNavigate();
  const upload = useUploadReport();
  const [patientUidInput, setPatientUidInput] = useState('');
  const [confirmedPatientUid, setConfirmedPatientUid] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [duplicate, setDuplicate] = useState<DuplicateState | null>(null);

  const uploadFile = async (file: File, force = false): Promise<Report> => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('patient_uid', confirmedPatientUid);
    const report = await upload.mutateAsync({ formData, force });
    setProgress(100);

    if (report.duplicate_warning) {
      setDuplicate(probableDuplicateFromReport(report.duplicate_warning));
    } else {
      navigate(`/doctor/reports/${report.report_id}`);
    }

    return report;
  };

  const handleForceUpload = () => {
    if (!selectedFile) {
      return;
    }

    setDuplicate(null);
    void uploadFile(selectedFile, true);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Upload Report</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Confirm the patient before uploading a document.</p>
      </div>

      {errorMessage ? (
        <Toast variant="error" title="Upload failed">
          {errorMessage}
        </Toast>
      ) : null}

      <Card>
        <h2 className="mb-4 text-base font-semibold text-clinical-text-primary">Step 1: Confirm Patient UID</h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            value={patientUidInput}
            onChange={(event) => setPatientUidInput(event.target.value)}
            className="rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
            placeholder="Patient UID"
            aria-label="Patient UID"
          />
          <Button onClick={() => setConfirmedPatientUid(patientUidInput.trim())} disabled={!patientUidInput.trim()}>
            Confirm
          </Button>
        </div>
        {confirmedPatientUid ? (
          <p className="mt-3 text-sm text-clinical-auto">Patient UID confirmed: {confirmedPatientUid}</p>
        ) : null}
      </Card>

      <Card>
        <h2 className="mb-4 text-base font-semibold text-clinical-text-primary">Step 2: Upload Document</h2>
        <UploadDropzone
          patientUid={confirmedPatientUid}
          disabled={!confirmedPatientUid}
          onFileSelected={setSelectedFile}
          onProgress={setProgress}
          onUpload={(file) => uploadFile(file)}
          onDuplicate={(error) => {
            setSelectedFile(selectedFile);
            setErrorMessage(null);
            setDuplicate(exactDuplicateFromError(error));
          }}
          onError={(error) => {
            const apiError = normalizeApiError(error);
            setErrorMessage(
              apiError.statusCode === 429
                ? 'Upload rate limit reached - try again later'
                : apiError.message,
            );
          }}
        />
        {progress > 0 ? (
          <div className="mt-4 h-2 rounded-full bg-slate-200">
            <div className="h-2 rounded-full bg-clinical-primary" style={{ width: `${progress}%` }} />
          </div>
        ) : null}
      </Card>

      {duplicate ? (
        <DuplicateWarningModal
          type={duplicate.type}
          existingReportId={duplicate.existingReportId}
          existingUploadedAt={duplicate.existingUploadedAt}
          uploadedByRole={duplicate.uploadedByRole}
          onUseExisting={() => navigate(`/doctor/reports/${duplicate.existingReportId}`)}
          onForceUpload={handleForceUpload}
          onDismiss={duplicate.type === 'probable' ? () => setDuplicate(null) : undefined}
        />
      ) : null}
    </div>
  );
}
