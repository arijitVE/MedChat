import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { AbnormalityPanel } from '../../components/charts/AbnormalityPanel';
import { TrendLineChart } from '../../components/charts/TrendLineChart';
import { RetryPanel } from '../../components/feedback/RetryPanel';
import { Card } from '../../components/ui/Card';
import { Skeleton } from '../../components/ui/Skeleton';
import { useAnalytics, useTrend } from '../../hooks/useIntelligence';
import { normalizeApiError } from '../../lib/apiError';

export default function AnalyticsPage() {
  const { patientId = '' } = useParams();
  const analytics = useAnalytics(patientId);
  const fieldOptions = useMemo(
    () => [...(analytics.data?.abnormal_fields ?? []), ...(analytics.data?.normal_fields ?? [])],
    [analytics.data],
  );
  const [selectedField, setSelectedField] = useState('');

  useEffect(() => {
    if (!selectedField && fieldOptions[0]) {
      setSelectedField(fieldOptions[0].name);
    }
  }, [fieldOptions, selectedField]);

  const trend = useTrend(patientId, selectedField);

  if (analytics.isError) {
    return <RetryPanel onRetry={() => void analytics.refetch()} message={normalizeApiError(analytics.error).message} />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold text-clinical-text-primary">Analytics</h1>
        <p className="mt-1 text-sm text-clinical-text-secondary">Patient trend and abnormality review.</p>
      </div>

      {analytics.isLoading ? (
        <Skeleton variant="card" rows={2} />
      ) : (
        <>
          <Card>
            <label className="block text-sm font-medium text-clinical-text-primary" htmlFor="field-selector">
              Field
            </label>
            <select
              id="field-selector"
              className="mt-1 w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
              value={selectedField}
              onChange={(event) => setSelectedField(event.target.value)}
            >
              {fieldOptions.map((field) => (
                <option key={field.field_id} value={field.name}>
                  {field.name}
                </option>
              ))}
            </select>
          </Card>

          <AbnormalityPanel
            abnormalFields={analytics.data?.abnormal_fields ?? []}
            normalFields={analytics.data?.normal_fields ?? []}
          />

          <Card>
            <h2 className="mb-2 text-base font-semibold text-clinical-text-primary">AI Insight</h2>
            <p className="text-sm text-clinical-text-secondary">
              {analytics.data?.ai_insight ?? 'No insight available.'}
            </p>
          </Card>

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
        </>
      )}
    </div>
  );
}
