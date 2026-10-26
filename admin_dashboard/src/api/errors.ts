/** One error type for everything the API (or the network) can go wrong with. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: Record<string, string>
  readonly retryAfterSeconds: number | null

  constructor(
    status: number,
    code: string,
    message: string,
    fields: Record<string, string> = {},
    retryAfterSeconds: number | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
    this.retryAfterSeconds = retryAfterSeconds
  }
}

interface ErrorBody {
  error?: { code?: unknown; message?: unknown; fields?: unknown }
}

function retryAfter(response: Response): number | null {
  const value = Number(response.headers.get('Retry-After'))
  return Number.isFinite(value) && value > 0 ? value : null
}

/** Read the API's `{"error": {code, message, fields}}` body; anything else gets a plain message. */
export async function parseApiError(response: Response): Promise<ApiError> {
  const fallback = new ApiError(
    response.status,
    `HTTP_${response.status}`,
    `Something went wrong (${response.status}).`,
    {},
    retryAfter(response),
  )
  let body: ErrorBody
  try {
    body = (await response.json()) as ErrorBody
  } catch {
    return fallback
  }
  const error = body?.error
  if (!error || typeof error.code !== 'string' || typeof error.message !== 'string') {
    return fallback
  }
  const fields =
    error.fields && typeof error.fields === 'object' ? (error.fields as Record<string, string>) : {}
  return new ApiError(response.status, error.code, error.message, fields, retryAfter(response))
}

/** `fetch` itself failed: the server is down or unreachable. */
export function networkError(cause: unknown): ApiError {
  const error = new ApiError(0, 'NETWORK_ERROR', "Can't reach the server. Check the API is running.")
  ;(error as Error & { cause?: unknown }).cause = cause
  return error
}
