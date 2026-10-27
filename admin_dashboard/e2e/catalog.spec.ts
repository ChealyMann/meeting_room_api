import { expect, test } from '@playwright/test'

// Needs the API running (run.bat) and an Admin whose password is already changed.
const email = process.env.E2E_ADMIN_EMAIL
const password = process.env.E2E_ADMIN_PASSWORD

// eslint-disable-next-line playwright/no-skipped-test -- skipped on purpose when no account is given
test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')

test('add a room type and an item with an icon, then turn the item off', async ({ page }) => {
  const stamp = Date.now()
  const roomType = `E2E Room type ${stamp}`
  const item = `E2E Item ${stamp}`
  const panel = page.getByRole('dialog')

  await page.goto('/sign-in')
  await page.getByLabel('Email').fill(email!)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('.count')).toBeVisible()

  await page.getByRole('link', { name: 'Room types' }).click()
  await page.getByRole('button', { name: 'New room type' }).first().click()
  await panel.locator('#name_kh').fill(`ប្រភេទ ${stamp}`)
  await panel.locator('#name_en').fill(roomType)
  await panel.getByRole('button', { name: 'Create room type' }).click()
  await expect(page.getByRole('status')).toContainText(`${roomType} saved`)
  await page.getByPlaceholder('Search Khmer or English name').fill(roomType)
  await expect(page.locator('tbody tr')).toHaveCount(1)

  await page.getByRole('link', { name: 'Equipment' }).click()
  await page.getByRole('button', { name: 'New item' }).first().click()
  await panel.locator('#name').fill(item)
  await panel.getByRole('radio', { name: 'Projector' }).click()
  await panel.getByRole('button', { name: 'Create item' }).click()
  await expect(page.getByRole('status')).toContainText(`${item} saved`)
  await page.getByPlaceholder('Search name').fill(item)
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await expect(page.locator('tbody tr .col-icon svg')).toBeVisible()

  await page.locator('tbody tr').first().click()
  await panel.locator('.panel-foot').getByRole('switch', { name: 'Active' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('No rooms have it.')
  await page.getByRole('alertdialog').getByRole('button', { name: 'Make inactive' }).click()
  await page.getByRole('group', { name: 'Status' }).getByRole('button', { name: 'All' }).click()
  await expect(page.locator('tbody tr').first()).toContainText('Inactive')
})
