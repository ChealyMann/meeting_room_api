import { expect, test } from '@playwright/test'

import { openGroup } from './rail'

// Needs the API running (run.bat) and an Admin whose password is already changed.
const email = process.env.E2E_ADMIN_EMAIL
const password = process.env.E2E_ADMIN_PASSWORD

// eslint-disable-next-line playwright/no-skipped-test -- skipped on purpose when no account is given
test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')

test('add a catering package, then open the bookings list and a booking', async ({ page }) => {
  const name = `E2E Package ${Date.now()}`
  const panel = page.getByRole('dialog')

  await page.goto('/sign-in')
  await page.getByLabel('Email').fill(email!)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('.count')).toBeVisible()

  await openGroup(page, 'Catalog')
  await page.getByRole('link', { name: 'Catering packages' }).click()
  await page.getByRole('button', { name: 'New package' }).first().click()
  await panel.locator('#name').fill(name)
  await panel.getByRole('button', { name: 'Create package' }).click()
  await expect(page.getByRole('status')).toContainText(`${name} saved`)
  await page.getByPlaceholder('Search name').fill(name)
  await expect(page.locator('tbody tr')).toHaveCount(1)

  await page.getByRole('link', { name: 'Bookings', exact: true }).click()
  await expect(page.locator('.count')).toBeVisible()
  const rows = page.locator('tbody tr')
  // A new system may have no bookings yet; then the list is the whole check.
  if ((await rows.count()) > 0) {
    await rows.first().click()
    await panel.getByRole('tab', { name: /Sessions/ }).click()
    await expect(panel.locator('#tabpanel-sessions li').first()).toBeVisible()
  }
})
