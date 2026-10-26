// Who is signed in. The access token lives only in memory; the refresh token
// lives in sessionStorage, so closing the browser signs out (DSH-A07).
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, apiBaseUrl } from '../api'
import { login, refreshTokens } from '../api/auth'
import { ApiError } from '../api/errors'
import * as me from '../api/me'
import type { Tokens, UserDetail } from '../api/types'
import { useDraftsStore } from './drafts'

export const REFRESH_KEY = 'nbc.admin.refresh'

function readRefreshToken(): string | null {
  return sessionStorage.getItem(REFRESH_KEY)
}

export const useSessionStore = defineStore('session', () => {
  const accessToken = ref<string | null>(null)
  const user = ref<UserDetail | null>(null)
  const ready = ref(false)

  const signedIn = computed(() => accessToken.value !== null && user.value !== null)
  const isAdmin = computed(() => user.value?.roles.some((role) => role.code === 'ADMIN') ?? false)
  const mustChangePassword = computed(() => user.value?.must_change_password ?? false)

  function applyTokens(tokens: Tokens): void {
    accessToken.value = tokens.access_token
    sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token)
  }

  function clear(): void {
    accessToken.value = null
    user.value = null
    sessionStorage.removeItem(REFRESH_KEY)
  }

  async function loadMe(): Promise<void> {
    user.value = await me.getMe(api)
  }

  async function signIn(email: string, password: string): Promise<void> {
    applyTokens(await login(apiBaseUrl, email, password))
    await loadMe()
  }

  /**
   * Get a new access token. False when the API refuses the refresh token;
   * a network error is thrown instead, so a short outage does not sign the user out.
   */
  async function refresh(): Promise<boolean> {
    const refreshToken = readRefreshToken()
    if (!refreshToken) return false
    try {
      applyTokens(await refreshTokens(apiBaseUrl, refreshToken))
      return true
    } catch (error) {
      if (error instanceof ApiError && error.code === 'NETWORK_ERROR') throw error
      return false
    }
  }

  /** On app start: sign in again from the stored refresh token, if any. */
  async function restore(): Promise<void> {
    try {
      if (!accessToken.value && readRefreshToken()) {
        if (await refresh()) await loadMe()
        else clear()
      }
    } catch {
      clear()
    } finally {
      ready.value = true
    }
  }

  async function changePassword(current: string, next: string): Promise<void> {
    applyTokens(await me.changePassword(api, current, next))
    await loadMe()
  }

  async function signOut(): Promise<void> {
    try {
      await me.logout(api, readRefreshToken())
    } catch {
      // Signing out locally still works when the API call fails.
    }
    clear()
    // Unsaved edits belong to this user; expire() keeps them, sign-out does not.
    useDraftsStore().clearAll()
  }

  /** The API refused our tokens: forget them. The router sends the user to sign-in. */
  function expire(): void {
    clear()
  }

  return {
    accessToken,
    user,
    ready,
    signedIn,
    isAdmin,
    mustChangePassword,
    applyTokens,
    loadMe,
    signIn,
    refresh,
    restore,
    changePassword,
    signOut,
    expire,
  }
})
