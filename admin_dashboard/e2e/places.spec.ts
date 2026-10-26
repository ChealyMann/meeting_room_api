import { expect, test } from '@playwright/test'

// Needs the API running (run.bat) and an Admin whose password is already changed.
const email = process.env.E2E_ADMIN_EMAIL
const password = process.env.E2E_ADMIN_PASSWORD

// eslint-disable-next-line playwright/no-skipped-test -- skipped on purpose when no account is given
test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')

test('add an office, a building and a floor, then turn the office off and on', async ({ page }) => {
  const stamp = Date.now()
  const office = `E2E Office ${stamp}`
  const building = `E2E Building ${stamp}`
  const floor = `E2E Floor ${stamp}`
  const panel = page.getByRole('dialog')

  await page.goto('/sign-in')
  await page.getByLabel('Email').fill(email!)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('.count')).toBeVisible()

  await page.getByRole('link', { name: 'Offices' }).click()
  await page.getByRole('button', { name: 'New office' }).first().click()
  await panel.locator('#name_kh').fill(`ការិយាល័យ ${stamp}`)
  await panel.locator('#name_en').fill(office)
  await expect(panel.locator('#province option')).not.toHaveCount(1)
  await panel.locator('#province').selectOption({ index: 1 })
  await panel.getByRole('button', { name: 'Create office' }).click()
  await expect(page.getByRole('status')).toContainText(`${office} saved`)
  await page.getByPlaceholder('Search name or address').fill(office)
  await expect(page.locator('tbody tr')).toHaveCount(1)

  await page.getByRole('link', { name: 'Buildings' }).click()
  await page.getByRole('button', { name: 'New building' }).first().click()
  await expect(panel.locator('#location_id')).toContainText(office)
  await panel.locator('#location_id').selectOption({ label: office })
  await panel.locator('#name_kh').fill(`អគារ ${stamp}`)
  await panel.locator('#name_en').fill(building)
  await panel.getByRole('button', { name: 'Create building' }).click()
  await expect(page.getByRole('status')).toContainText(`${building} saved`)

  await page.getByRole('link', { name: 'Floors' }).click()
  await page.getByRole('button', { name: 'New floor' }).first().click()
  await expect(panel.locator('#location_id')).toContainText(office)
  await panel.locator('#location_id').selectOption({ label: office })
  await expect(panel.locator('#building_id')).toContainText(building)
  await panel.locator('#building_id').selectOption({ label: building })
  await panel.locator('#floor_label').fill(floor)
  await panel.getByRole('button', { name: 'Create floor' }).click()
  await expect(page.getByRole('status')).toContainText(`${floor} saved`)

  await page.getByRole('link', { name: 'Offices' }).click()
  await page.getByRole('group', { name: 'Status' }).getByRole('button', { name: 'All' }).click()
  await page.getByPlaceholder('Search name or address').fill(office)
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await page.locator('tbody tr').first().click()
  await panel.getByRole('button', { name: 'Turn off' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('No rooms are affected.')
  await page.getByRole('alertdialog').getByRole('button', { name: 'Turn off' }).click()
  await expect(page.locator('tbody tr').first()).toContainText('Inactive')

  await page.locator('tbody tr').first().click()
  await panel.getByRole('button', { name: 'Turn on' }).click()
  await expect(page.locator('tbody tr').first()).toContainText('Active')
})
