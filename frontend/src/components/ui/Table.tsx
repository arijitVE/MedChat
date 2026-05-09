import type {
  HTMLAttributes,
  TableHTMLAttributes,
  TdHTMLAttributes,
  ThHTMLAttributes,
} from 'react';

export function Table({
  className = '',
  ...props
}: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-x-auto rounded-lg border border-clinical-border bg-clinical-surface">
      <table className={`w-full text-left text-sm ${className}`} {...props} />
    </div>
  );
}

export function TableHeader({
  className = '',
  ...props
}: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={`bg-slate-50 text-clinical-text-secondary ${className}`} {...props} />;
}

export function TableBody({
  className = '',
  ...props
}: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={`divide-y divide-clinical-border ${className}`} {...props} />;
}

export function TableRow({ className = '', ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={`hover:bg-slate-50 ${className}`} {...props} />;
}

export function TableHead({ className = '', scope = 'col', ...props }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope={scope}
      className={`px-4 py-3 text-xs font-semibold uppercase tracking-normal ${className}`}
      {...props}
    />
  );
}

export function TableCell({ className = '', ...props }: TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={`px-4 py-3 text-clinical-text-primary ${className}`} {...props} />;
}
