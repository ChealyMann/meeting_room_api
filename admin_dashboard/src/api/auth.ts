// Sign-in and refresh use plain fetch: they make tokens, so they never retry with one.
import { networkError, parseApiError } from './errors'
import type { Tokens } from './types'

async function postForTokens(url: string, body: unknown): Promise<Tokens> {
  let response: Response
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch (cause) {
    throw networkError(cause)
  }
  if (!response.ok) throw await parseApiError(response)
  return (await response.json()) as Tokens
}

/** The password is sent exactly as typed: spaces count. */
export function login(baseUrl: string, email: string, password: string): Promise<Tokens> {
  return postForTokens(`${baseUrl}/api/v1/auth/login`, { email, password })
}

export function refreshTokens(baseUrl: string, refreshToken: string): Promise<Tokens> {
  return postForTokens(`${baseUrl}/api/v1/auth/refresh`, { refresh_token: refreshToken })
}
