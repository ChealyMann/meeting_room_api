import { describe, expect, it } from 'vitest'

import { ApiError, networkError, parseApiError } from '../errors'

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  })
}

describe('parseApiError', () => {
  it('reads code, message and field errors from the API error shape', async () => {
    const error = await parseApiError(
      jsonResponse(422, {
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Invalid request.',
          fields: { phone: 'Too long (max 20).' },
        },
      }),
    )

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(422)
    expect(error.code).toBe('VALIDATION_ERROR')
    expect(error.message).toBe('Invalid request.')
    expect(error.fields.phone).toBe('Too long (max 20).')
    expect(error.retryAfterSeconds).toBeNull()
  })

  it('reads Retry-After on a rate limit', async () => {
    const error = await parseApiError(
      jsonResponse(
        429,
        { error: { code: 'RATE_LIMITED', message: 'Too many failed sign-ins.' } },
        { 'Retry-After': '840' },
      ),
    )

    expect(error.code).toBe('RATE_LIMITED')
    expect(error.retryAfterSeconds).toBe(840)
    expect(error.fields).toEqual({})
  })

  it('gives a plain message when the body is not JSON', async () => {
    const error = await parseApiError(
      new Response('<html>Bad gateway</html>', {
        status: 502,
        headers: { 'Content-Type': 'text/html' },
      }),
    )

    expect(error.status).toBe(502)
    expect(error.code).toBe('HTTP_502')
    expect(error.message).toBe('Something went wrong (502).')
    expect(error.fields).toEqual({})
  })
})

describe('networkError', () => {
  it('turns a failed fetch into a NETWORK_ERROR', () => {
    const error = networkError(new TypeError('Failed to fetch'))

    expect(error.status).toBe(0)
    expect(error.code).toBe('NETWORK_ERROR')
    expect(error.message).toBe("Can't reach the server. Check the API is running.")
  })
})
