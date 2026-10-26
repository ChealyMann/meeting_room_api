import { expect, test, type Page } from '@playwright/test'

// Runs without the real API: every /api/v1 call gets a fake answer.
const ME = {
  id: 1,
  staff_id: 'EMP-00002',
  title: null,
  name_en: 'Sok Dara',
  name_kh: 'សុខ ដារា',
  email: 'dara@company.com',
  secondary_email: null,
  phone: null,
  avatar_url: null,
  signature_url: null,
  email_notifications: true,
  division: null,
  department: null,
  position: { id: 9, name_en: 'IT Lead', name_kh: 'ប្រធានព័ត៌មានវិទ្យា' },
  province: null,
  roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }],
  owned_room_ids: [],
  is_active: true,
  must_change_password: false,
  last_login_at: null,
  created_at: '2026-10-01T00:00:00Z',
  updated_at: '2026-10-01T00:00:00Z',
}

async function signedIn(page: Page) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (path === '/api/v1/auth/logout') return route.fulfill({ status: 204 })
    return route.fulfill({ json: ME })
  })
  await page.goto('/')
}

for (const [name, width] of [
  ['full rail', 1280],
  ['collapsed rail (tablet)', 900],
] as const) {
  test(`${name}: the user can sign out`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 })
    await signedIn(page)

    const signOut = page.getByRole('button', { name: 'Sign out' })
    await expect(signOut).toBeVisible()
    await signOut.click()
    await expect(page).toHaveURL(/\/sign-in/)
  })
}

test('phone: the user can sign out from the menu', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 })
  await signedIn(page)

  await page.getByRole('button', { name: 'Menu' }).click()
  await page.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/sign-in/)
})
