import {
  AlertTriangle,
  Activity,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  CircleAlert,
} from 'lucide-react';
import {
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ReactNode } from 'react';
import { Card } from '../ui/Card';
import { EmptyState } from '../ui/EmptyState';
import { Skeleton } from '../ui/Skeleton';
import type { AnalyticsResult, PatientFieldTrend } from '../../types/intelligence';

interface PatientAnalyticsDashboardProps {
  analytics?: AnalyticsResult;
  isLoading?: boolean;
}

interface ChartPoint {
  date: string;
  value: number | null;
  referenceMin: number | null;
  referenceMax: number | null;
  status: string;
  displayValue: string;
  reportName: string;
}

function formatNumber(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '-';
  }
  return Number(value).toFixed(digits).replace(/\.0$/, '');
}

function statusLabel(status: string) {
  if (status === 'low') {
    return 'Low';
  }
  if (status === 'high') {
    return 'High';
  }
  if (status === 'normal') {
    return 'Normal';
  }
  return 'Unknown';
}

function trendLabel(direction: string) {
  return direction.replace('_', ' ');
}

function trendIcon(direction: string) {
  if (direction === 'increasing') {
    return <ArrowUpRight className="h-4 w-4 text-clinical-warning" aria-hidden="true" />;
  }
  if (direction === 'decreasing') {
    return <ArrowDownRight className="h-4 w-4 text-clinical-primary" aria-hidden="true" />;
  }
  if (direction === 'stable') {
    return <ArrowRight className="h-4 w-4 text-clinical-auto" aria-hidden="true" />;
  }
  return <CircleAlert className="h-4 w-4 text-clinical-text-muted" aria-hidden="true" />;
}

function toChartData(trend: PatientFieldTrend): ChartPoint[] {
  return trend.values.map((point) => ({
    date: point.report_date,
    value: point.value,
    referenceMin: point.reference_min,
    referenceMax: point.reference_max,
    status: point.status,
    displayValue: point.display_value,
    reportName: point.report_name,
  }));
}

function hasConstantReferenceRange(trend: PatientFieldTrend) {
  const first = trend.values.find((point) => point.reference_min !== null || point.reference_max !== null);
  if (!first || first.reference_min === null || first.reference_max === null) {
    return false;
  }
  return trend.values.every(
    (point) => point.reference_min === first.reference_min && point.reference_max === first.reference_max,
  );
}

function rangePosition(trend: PatientFieldTrend) {
  const latest = trend.values[trend.values.length - 1];
  if (!latest || latest.value === null || latest.reference_min === null || latest.reference_max === null) {
    return 50;
  }
  const spread = latest.reference_max - latest.reference_min;
  const paddedMin = latest.reference_min - spread;
  const paddedMax = latest.reference_max + spread;
  if (paddedMax === paddedMin) {
    return 50;
  }
  return Math.min(100, Math.max(0, ((latest.value - paddedMin) / (paddedMax - paddedMin)) * 100));
}

function SummaryCard({
  label,
  value,
  tone = 'neutral',
}: {
  label: string;
  value: number;
  tone?: 'neutral' | 'critical' | 'success' | 'warning';
}) {
  const toneClass = {
    neutral: 'bg-slate-50 text-clinical-text-primary',
    critical: 'bg-clinical-critical-bg text-clinical-critical',
    success: 'bg-clinical-auto-bg text-clinical-auto',
    warning: 'bg-clinical-hitl-bg text-clinical-hitl',
  }[tone];

  return (
    <Card className="p-4">
      <p className="text-xs font-semibold uppercase text-clinical-text-secondary">{label}</p>
      <p className={`mt-3 inline-flex rounded-md px-2 py-1 text-2xl font-semibold ${toneClass}`}>{value}</p>
    </Card>
  );
}

function StatusBadge({ status }: { status: string }) {
  const classes =
    status === 'normal'
      ? 'bg-clinical-auto-bg text-clinical-auto'
      : status === 'low' || status === 'high'
        ? 'bg-clinical-critical-bg text-clinical-critical'
        : 'bg-slate-100 text-clinical-text-secondary';

  return (
    <span className={`rounded-full px-2 py-1 text-xs font-semibold ${classes}`}>
      {statusLabel(status)}
    </span>
  );
}

function SingleValueRangeCard({ trend }: { trend: PatientFieldTrend }) {
  const point = trend.values[0];
  const hasRange = point?.reference_min !== null && point?.reference_max !== null;

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-clinical-text-primary">{trend.field_name}</h3>
          <p className="mt-1 text-sm text-clinical-text-secondary">
            Latest: {trend.latest_display_value} {trend.unit ?? ''}
          </p>
        </div>
        <StatusBadge status={trend.latest_status} />
      </div>

      {hasRange ? (
        <div className="mt-4">
          <div className="relative h-3 rounded-full bg-slate-200">
            <div className="absolute left-1/3 h-3 w-1/3 rounded-full bg-clinical-auto-bg" />
            <span
              className="absolute top-1/2 h-5 w-5 -translate-y-1/2 rounded-full border-2 border-white bg-clinical-primary shadow"
              style={{ left: `calc(${rangePosition(trend)}% - 10px)` }}
              aria-hidden="true"
            />
          </div>
          <div className="mt-2 flex justify-between text-xs text-clinical-text-secondary">
            <span>Low</span>
            <span>
              Reference {formatNumber(point.reference_min)} - {formatNumber(point.reference_max)}
            </span>
            <span>High</span>
          </div>
        </div>
      ) : (
        <p className="mt-4 rounded-md bg-slate-50 px-3 py-2 text-sm text-clinical-text-secondary">
          Insufficient historical data available for trend analysis.
        </p>
      )}
    </Card>
  );
}

function TrendChart({ trend }: { trend: PatientFieldTrend }) {
  const chartData = toChartData(trend);
  const hasReferenceArea = hasConstantReferenceRange(trend);
  const referenceMin = hasReferenceArea ? chartData[0]?.referenceMin : null;
  const referenceMax = hasReferenceArea ? chartData[0]?.referenceMax : null;

  return (
    <Card className="p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            {trendIcon(trend.trend_direction)}
            <h3 className="text-sm font-semibold text-clinical-text-primary">{trend.field_name}</h3>
          </div>
          <p className="mt-1 text-xs text-clinical-text-secondary">
            {trendLabel(trend.trend_direction)} · {trend.sample_size} values
            {trend.percent_change !== null ? ` · ${formatNumber(trend.percent_change)}% change` : ''}
          </p>
        </div>
        <StatusBadge status={trend.latest_status} />
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#475569' }} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#475569' }} tickLine={false} width={44} />
            {hasReferenceArea && referenceMin !== null && referenceMax !== null ? (
              <ReferenceArea y1={referenceMin} y2={referenceMax} fill="#DCFCE7" fillOpacity={0.45} />
            ) : null}
            <Tooltip
              formatter={(_value, _name, item) => [
                `${item.payload.displayValue}${trend.unit ? ` ${trend.unit}` : ''}`,
                trend.field_name,
              ]}
              labelFormatter={(label, payload) => {
                const point = payload[0]?.payload as ChartPoint | undefined;
                return point ? `${label} · ${point.reportName}` : label;
              }}
            />
            {!hasReferenceArea ? (
              <>
                <Line type="monotone" dataKey="referenceMin" stroke="#16A34A" strokeDasharray="4 4" dot={false} connectNulls />
                <Line type="monotone" dataKey="referenceMax" stroke="#16A34A" strokeDasharray="4 4" dot={false} connectNulls />
              </>
            ) : null}
            <Line type="monotone" dataKey="value" stroke="#1D4ED8" strokeWidth={2} dot={false} connectNulls={false} />
            <Scatter data={chartData} dataKey="value">
              {chartData.map((point) => (
                <Cell
                  key={`${trend.field_name}-${point.date}-${point.displayValue}`}
                  fill={point.status === 'normal' ? '#1D4ED8' : point.status === 'unknown' ? '#94A3B8' : '#DC2626'}
                />
              ))}
            </Scatter>
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

function CompactTrendList({ title, trends, icon }: { title: string; trends: PatientFieldTrend[]; icon: ReactNode }) {
  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-semibold text-clinical-text-primary">{title}</h3>
      </div>
      {trends.length === 0 ? (
        <p className="text-sm text-clinical-text-secondary">No matching parameters.</p>
      ) : (
        <div className="space-y-2">
          {trends.slice(0, 6).map((trend) => (
            <div key={`${title}-${trend.field_name}`} className="flex items-center justify-between gap-3 rounded-md bg-slate-50 px-3 py-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-clinical-text-primary">{trend.field_name}</p>
                <p className="text-xs text-clinical-text-secondary">
                  {trend.latest_display_value} {trend.unit ?? ''} · {trend.latest_report_date}
                </p>
              </div>
              <StatusBadge status={trend.latest_status} />
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

export function PatientAnalyticsDashboard({ analytics, isLoading = false }: PatientAnalyticsDashboardProps) {
  if (isLoading) {
    return <Skeleton variant="card" rows={6} />;
  }

  const trends = analytics?.trends ?? [];
  const overview = analytics?.overview;
  const trendReady = trends.filter((trend) => trend.sample_size >= 2);
  const singleValue = trends.filter((trend) => trend.sample_size === 1);
  const abnormal = analytics?.critical_changes ?? [];
  const stable = analytics?.stable_parameters ?? [];
  const insufficient = analytics?.insufficient_data ?? [];

  if (trends.length === 0) {
    return (
      <EmptyState title="No structured numeric analytics available" description="Upload or process reports with numeric extracted fields to enable patient-specific analytics." />
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
        <SummaryCard label="Tracked Fields" value={overview?.tracked_fields ?? trends.length} />
        <SummaryCard label="Trend Ready" value={overview?.trend_ready_fields ?? trendReady.length} tone="success" />
        <SummaryCard label="Data Points" value={overview?.total_values ?? 0} />
        <SummaryCard label="Abnormal Latest" value={overview?.abnormal_latest_count ?? abnormal.length} tone="critical" />
        <SummaryCard label="Critical Changes" value={overview?.critical_change_count ?? 0} tone="warning" />
        <SummaryCard label="Insufficient" value={overview?.insufficient_data_count ?? insufficient.length} />
      </div>

      <Card>
        <h2 className="text-base font-semibold text-clinical-text-primary">Latest Clinical Summary</h2>
        <p className="mt-2 text-sm text-clinical-text-secondary">
          These visuals are calculated directly from structured report fields, report timestamps, and extracted reference ranges.
          LLMs are not used to create chart values.
        </p>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <CompactTrendList
          title="Abnormal Findings"
          trends={abnormal}
          icon={<AlertTriangle className="h-4 w-4 text-clinical-critical" aria-hidden="true" />}
        />
        <CompactTrendList
          title="Stable Parameters"
          trends={stable}
          icon={<CheckCircle2 className="h-4 w-4 text-clinical-auto" aria-hidden="true" />}
        />
        <CompactTrendList
          title="Missing / Insufficient Data"
          trends={insufficient}
          icon={<CircleAlert className="h-4 w-4 text-clinical-text-muted" aria-hidden="true" />}
        />
      </div>

      <section className="space-y-4" aria-label="Longitudinal trends">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-clinical-primary" aria-hidden="true" />
          <h2 className="text-base font-semibold text-clinical-text-primary">Longitudinal Trends</h2>
        </div>
        {trendReady.length === 0 ? (
          <EmptyState title="No longitudinal trends yet" description="At least two historical numeric values are needed for a trend chart." />
        ) : (
          <div className="grid gap-4 xl:grid-cols-2">
            {trendReady.map((trend) => (
              <TrendChart key={trend.field_name} trend={trend} />
            ))}
          </div>
        )}
      </section>

      {singleValue.length > 0 ? (
        <section className="space-y-4" aria-label="Single value reference comparisons">
          <h2 className="text-base font-semibold text-clinical-text-primary">Single-Report Reference Checks</h2>
          <div className="grid gap-4 xl:grid-cols-2">
            {singleValue.map((trend) => (
              <SingleValueRangeCard key={trend.field_name} trend={trend} />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
