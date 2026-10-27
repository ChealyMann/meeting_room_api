import { expect, test } from '@playwright/test'

import { pick } from './picker'

// Needs the API running (run.bat), an Admin whose password is already changed, and at least one active position.
const email = process.env.E2E_ADMIN_EMAIL
const password = process.env.E2E_ADMIN_PASSWORD

// eslint-disable-next-line playwright/no-skipped-test -- skipped on purpose when no account is given
test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')

test('add a user, give them Staff, set a temporary password; you cannot make yourself inactive', async ({ page }) => {
  const stamp = Date.now()
  const name = `E2E User ${stamp}`
  const panel = page.getByRole('dialog')

  await page.goto('/sign-in')
  await page.getByLabel('Email').fill(email!)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('.count')).toBeVisible()

  await page.getByRole('link', { name: 'Users' }).click()
  await page.getByRole('button', { name: 'New user' }).first().click()
  await panel.locator('#staff_id').fill(`E2E-${String(stamp).slice(-8)}`)
  await panel.locator('#name_kh').fill(`អ្នកប្រើ ${stamp}`)
  await panel.locator('#name_en').fill(name)
  await panel.locator('#email').fill(`e2e.${stamp}@company.com`)
  await pick(page, 'position_id', { first: true })
  await panel.getByRole('button', { name: 'Generate' }).click()
  await panel.getByRole('button', { name: 'Create user' }).click()
  await expect(page.getByRole('status')).toContainText(`${name} added`)

  // A new user has no roles: their panel opens on the Roles tab.
  await expect(panel.getByRole('tab', { name: 'Roles' })).toHaveAttribute('aria-selected', 'true')
  await panel.locator('#tabpanel-roles label').filter({ hasText: /^\s*Staff/ }).locator('input').check()
  await panel.getByRole('button', { name: 'Save roles' }).click()
  await expect(page.getByRole('status')).toContainText('Roles saved')
  await page.getByPlaceholder('Search name, staff ID or email').fill(name)
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await expect(page.locator('tbody tr .chip')).toHaveText(['Staff'])

  await panel.getByRole('tab', { name: 'Password' }).click()
  await panel.getByRole('button', { name: 'Generate' }).click()
  await panel.getByRole('button', { name: 'Set temporary password' }).click()
  await expect(page.getByRole('alertdialog')).toContainText(`Set a temporary password for ${name}?`)
  await page.getByRole('alertdialog').getByRole('button', { name: 'Set password' }).click()
  await expect(page.getByRole('status')).toContainText('Temporary password set')
  await expect(panel.locator('#reset_password')).toHaveValue('')

  await panel.getByRole('button', { name: 'Close' }).click()
  await page.getByPlaceholder('Search name, staff ID or email').fill(email!)
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await page.locator('tbody tr').first().click()
  await expect(panel.locator('.panel-foot').getByRole('switch', { name: 'Active' })).toHaveAttribute('aria-disabled', 'true')
  await expect(panel).toContainText('You cannot make yourself inactive.')

  await page.getByRole('link', { name: 'Roles' }).click()
  await expect(page.locator('tbody tr')).toHaveCount(6)
})
