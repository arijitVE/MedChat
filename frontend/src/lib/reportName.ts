import { sanitizeFilename } from './sanitize';
import type { Report } from '../types/report';

function token(value: string | null | undefined, fallback: string): string {
  const cleaned = (value || fallback).trim().replace(/[^A-Za-z0-9-]+/g, '_').replace(/^_+|_+$/g, '');
  return cleaned || fallback;
}

function documentTypeToken(report: Report): string {
  const rawType = report.inferred_document_type !== 'unknown'
    ? report.inferred_document_type
    : report.upload_document_type;
  const words = token(rawType, 'Medical').split('_').filter(Boolean);
  const titleWords = words.map((word) => `${word.slice(0, 1).toUpperCase()}${word.slice(1).toLowerCase()}`);
  if (!titleWords.some((word) => word.toLowerCase() === 'report')) {
    titleWords.push('Report');
  }
  return titleWords.join('_');
}

export function getReportDisplayName(report: Report): string {
  if (report.display_report_name) {
    return report.display_report_name;
  }

  if (report.patient_name || report.patient_uid) {
    return `${token(report.patient_name, 'Patient')}_${documentTypeToken(report)}_${token(report.patient_uid ?? report.patient_id, 'PatientID')}`;
  }

  return sanitizeFilename(report.file_name);
}
