import { useEffect, useMemo, useState } from 'react';
import { TrendLineChart } from '../../components/charts/TrendLineChart';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { useMyReportFields, useMyReports } from '../../hooks/useReports';
import { useMyTrends } from '../../hooks/useIntelligence';
import { normalizeApiError } from '../../lib/apiError';

export default function TrendsPage() {
  const reports = useMyReports();
  const latestReportId = reports.data?.[0]?.report_id ?? '';
  const fields = useMyReportFields(latestReportId);
  const fieldOptions = useMemo(
    () => (fields.data ?? []).filter((field) => field.numeric_value !== null).map((field) => field.field_name),
    [fields.data],
  );
  const [selectedField, setSelectedField] = useState('');

  useEffect(() => {
    if (!selectedField && fieldOptions[0]) {
      setSelectedField(fieldOptions[0]);
    }
  }, [fieldOptions, selectedField]);

  const trend = useMyTrends(selectedField);

  if (reports.isError) {
    return <RetryPanel onRetry={() => void reports.refetch()} message={normalizeApiError(reports.error).message} />;
  }

  if (fields.isError) {
    return <RetryPanel onRetry={() => void fields.refetch()} message={normalizeApiError(fields.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Trends</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Track changes in lab values over time.</p>
      </div>

      {reports.isLoading || fields.isLoading ? (
        <Skeleton variant="card" rows={2} />
      ) : (
        <Card>
          <label htmlFor="trend-field" className="block text-sm font-medium text-clinical-text-primary">
            Field
          </label>
          <select
            id="trend-field"
            value={selectedField}
            onChange={(event) => setSelectedField(event.target.value)}
            className="mt-1 w-full rounded-md border border-clinical-border px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
          >
            {fieldOptions.map((field) => (
              <option key={field} value={field}>{field}</option>
            ))}
          </select>
        </Card>
      )}

      {trend.isError ? (
        <RetryPanel onRetry={() => void trend.refetch()} message={normalizeApiError(trend.error).message} />
      ) : (
        <TrendLineChart
          data={trend.data?.data_points ?? []}
          meta={trend.data?.chart_json.meta ?? { label: selectedField, unit: '', ref_low: null, ref_high: null }}
          insight={trend.data?.insight}
          trendDirection={trend.data?.trend_direction}
          isLoading={trend.isLoading}
        />
      )}
    </div>
  );
}
