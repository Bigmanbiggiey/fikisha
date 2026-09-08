/**
 * RFC 9457 `application/problem+json` — the backend's single error shape
 * (see backend `fikisha/common/exceptions.py`). The client localizes `code`;
 * `detail` is a human-readable fallback only.
 */

export interface FieldError {
  field: string | null;
  code: string;
  detail: string;
}

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  code: string;
  detail: string;
  request_id?: string;
  errors?: FieldError[];
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | undefined;
  readonly fieldErrors: FieldError[];
  readonly problem: ProblemDetail | undefined;

  constructor(problem: ProblemDetail | undefined, status: number, fallbackMessage: string) {
    super(problem?.detail ?? fallbackMessage);
    this.name = 'ApiError';
    this.status = status;
    this.code = problem?.code ?? (status === 0 ? 'network_error' : 'error');
    this.requestId = problem?.request_id;
    this.fieldErrors = problem?.errors ?? [];
    this.problem = problem;
  }

  /** True when the caller should attempt a token refresh + retry. */
  get isUnauthenticated(): boolean {
    return this.status === 401;
  }
}

export function isProblemDetail(value: unknown): value is ProblemDetail {
  return (
    typeof value === 'object' &&
    value !== null &&
    'code' in value &&
    'status' in value &&
    typeof (value as ProblemDetail).code === 'string'
  );
}
