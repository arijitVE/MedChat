import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card } from '../ui/Card';
import { Skeleton } from '../ui/Skeleton';
import type { ChartMeta, TrendPoint, TrendResult } from '../../types/intelligence';

interface TrendLineChartProps {
  data: TrendPoint[];
  meta: ChartMeta;
  insight?: string;
  trendDirection?: TrendResult['trend_direction'];
  isLoading?: boolean;
  className?: string;
}

interface TrendChartPoint {
  date: string;
  value: number | null;
  displayValue: string;
}

function toChartData(data: TrendPoint[]): TrendChartPoint[] {
  return data.map((point) => ({
    date: point.date,
    value: point.numeric_value,
    displayValue: point.value,
  }));
}

function directionLabel(direction?: TrendResult['trend_direction']): string {
  if (!direction) {
    return 'trend unavailable';
  }

  return direction.replace('_', ' ');
}

export function TrendLineChart({
  data,
  meta,
  insight,
  trendDirection,
  isLoading = false,
  className = '',
}: TrendLineChartProps) {
  if (isLoading) {
    return <Skeleton variant="chart" className={className} />;
  }

  const chartData = toChartData(data);
  const referenceLow = meta.ref_low;
  const referenceHigh = meta.ref_high;
  const hasReferenceRange = referenceLow !== null && referenceHigh !== null;

  return (
    <Card
      className={className}
      role="img"
      aria-label={`Trend chart for ${meta.label} - ${directionLabel(trendDirection)}`}
    >
      <div className="mb-4">
        <h3 className="text-sm font-semibold text-clinical-text-primary">{meta.label}</h3>
        {insight ? <p className="mt-1 text-sm text-clinical-text-secondary">{insight}</p> : null}
      </div>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 12, fill: '#475569' }}
              tickLine={false}
              axisLine={{ stroke: '#E2E8F0' }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#475569' }}
              tickLine={false}
              axisLine={{ stroke: '#E2E8F0' }}
              unit={meta.unit ? ` ${meta.unit}` : undefined}
            />
            {hasReferenceRange ? (
              <ReferenceArea
                y1={referenceLow}
                y2={referenceHigh}
                fill="#DCFCE7"
                fillOpacity={0.45}
              />
            ) : null}
            <Tooltip
              formatter={(_value, _name, item) => [
                item.payload.displayValue,
                meta.unit ? `${meta.label} (${meta.unit})` : meta.label,
              ]}
              labelClassName="text-clinical-text-primary"
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#1D4ED8"
              strokeWidth={2}
              dot={{ r: 3, strokeWidth: 2 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
