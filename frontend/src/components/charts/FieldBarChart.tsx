import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card } from '../ui/Card';
import { Skeleton } from '../ui/Skeleton';

interface FieldBarChartProps {
  fields: string[];
  values: number[];
  title?: string;
  isLoading?: boolean;
  className?: string;
}

interface FieldBarPoint {
  field: string;
  value: number;
}

export function FieldBarChart({
  fields,
  values,
  title = 'Field values',
  isLoading = false,
  className = '',
}: FieldBarChartProps) {
  if (isLoading) {
    return <Skeleton variant="chart" className={className} />;
  }

  const data: FieldBarPoint[] = fields.map((field, index) => ({
    field,
    value: values[index] ?? 0,
  }));
  const fieldLabel = fields.length > 0 ? ` for ${fields.join(', ')}` : '';

  return (
    <Card className={className} role="img" aria-label={`${title} bar chart${fieldLabel}`}>
      <h3 className="mb-4 text-sm font-semibold text-clinical-text-primary">{title}</h3>
      <div className="h-48 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
            <CartesianGrid stroke="#E2E8F0" strokeDasharray="3 3" />
            <XAxis
              dataKey="field"
              tick={{ fontSize: 12, fill: '#475569' }}
              tickLine={false}
              axisLine={{ stroke: '#E2E8F0' }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: '#475569' }}
              tickLine={false}
              axisLine={{ stroke: '#E2E8F0' }}
            />
            <Tooltip />
            <Bar dataKey="value" fill="#1D4ED8" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
