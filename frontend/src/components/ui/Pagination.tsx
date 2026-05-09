import type { HTMLAttributes } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './Button';

interface PaginationProps extends HTMLAttributes<HTMLElement> {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({
  page,
  totalPages,
  onPageChange,
  className = '',
  ...props
}: PaginationProps) {
  const canGoPrevious = page > 1;
  const canGoNext = page < totalPages;

  return (
    <nav
      className={`flex items-center justify-between gap-3 ${className}`}
      aria-label="Pagination"
      {...props}
    >
      <Button
        variant="secondary"
        onClick={() => onPageChange(page - 1)}
        disabled={!canGoPrevious}
        leftIcon={<ChevronLeft className="h-4 w-4" aria-hidden="true" />}
      >
        Previous
      </Button>
      <span className="text-sm text-clinical-text-secondary" aria-live="polite">
        Page {page} of {Math.max(totalPages, 1)}
      </span>
      <Button
        variant="secondary"
        onClick={() => onPageChange(page + 1)}
        disabled={!canGoNext}
        rightIcon={<ChevronRight className="h-4 w-4" aria-hidden="true" />}
      >
        Next
      </Button>
    </nav>
  );
}
