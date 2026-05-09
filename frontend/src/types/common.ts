export interface PaginationParams {
  /** 1-based page number. Omit only when endpoint is intentionally unpaginated. */
  page?: number;
  /** Defaults to 20. Frontend must not request more than 100. */
  page_size?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total_count: number;
  total_pages: number;
}

export function normalizePaginationParams(params: PaginationParams = {}): Required<PaginationParams> {
  return {
    page: params.page ?? 1,
    page_size: Math.min(params.page_size ?? 20, 100),
  };
}
