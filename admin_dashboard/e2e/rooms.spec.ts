import { expect, test } from '@playwright/test'

import { pick } from './picker'

// Needs the API running (run.bat), an Admin whose password is already changed, and at least
// one active office with a building, a floor, a room type and an equipment item.
const email = process.env.E2E_ADMIN_EMAIL
const password = process.env.E2E_ADMIN_PASSWORD

// eslint-disable-next-line playwright/no-skipped-test -- skipped on purpose when no account is given
test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')

test('create a room in steps, find it, turn it off', async ({ page }) => {
  const stamp = Date.now()
  const nameEn = `E2E Room ${stamp}`

  await page.goto('/sign-in')
  await page.getByLabel('Email').fill(email!)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('.count')).toBeVisible()

  await page.getByRole('button', { name: 'New room' }).first().click()
  const panel = page.getByRole('dialog')
  await panel.locator('#name_kh').fill(`បន្ទប់ ${stamp}`)
  await panel.locator('#name_en').fill(nameEn)
  await pick(page, 'location_id', { first: true })
  await pick(page, 'building_id', { first: true })
  await pick(page, 'floor_id', { first: true })
  await pick(page, 'category_id', { first: true })
  await panel.locator('#capacity').fill('8')
  await page.getByRole('button', { name: 'Create room' }).click()

  await expect(panel).toContainText('Step 2 of 3 · Photos')
  await panel.locator('#room-photos').setInputFiles('public/nbc-logo.png')
  await expect(panel.locator('li.photo').first()).toContainText('Cover')
  await panel.getByRole('button', { name: 'Next: equipment' }).click()

  await expect(panel).toContainText('Step 3 of 3 · Equipment')
  await panel.locator('#tabpanel-equipment input[type="checkbox"]').first().check()
  await panel.getByRole('button', { name: 'Save equipment' }).click()
  await expect(page.getByRole('status')).toContainText('Equipment saved')
  await panel.getByRole('button', { name: 'Done' }).click()

  await page.getByPlaceholder('Search name or description').fill(nameEn)
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await page.locator('tbody tr').first().click()
  await page.getByRole('dialog').getByRole('button', { name: 'Turn off' }).click()
  await page.getByRole('alertdialog').getByRole('button', { name: 'Turn off' }).click()
  await expect(page.getByRole('dialog')).toContainText('Inactive')
})
