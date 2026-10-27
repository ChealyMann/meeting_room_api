import { expect, test } from '@playwright/test'

import { pick } from './picker'

// Needs the API running (run.bat), an Admin whose password is already changed, and at least one active office.
const email = process.env.E2E_ADMIN_EMAIL
const password = process.env.E2E_ADMIN_PASSWORD

// eslint-disable-next-line playwright/no-skipped-test -- skipped on purpose when no account is given
test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')

test('add a department, a division and a position, then make the position inactive', async ({ page }) => {
  const stamp = Date.now()
  const department = `E2E Department ${stamp}`
  const division = `E2E Division ${stamp}`
  const position = `E2E Position ${stamp}`
  const panel = page.getByRole('dialog')

  await page.goto('/sign-in')
  await page.getByLabel('Email').fill(email!)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page.locator('.count')).toBeVisible()

  await page.getByRole('link', { name: 'Departments' }).click()
  await page.getByRole('button', { name: 'New department' }).first().click()
  await pick(page, 'location_id', { first: true })
  await panel.locator('#name_kh').fill(`នាយកដ្ឋាន ${stamp}`)
  await panel.locator('#name_en').fill(department)
  await panel.getByRole('button', { name: 'Create department' }).click()
  await expect(page.getByRole('status')).toContainText(`${department} saved`)

  await page.getByRole('link', { name: 'Divisions' }).click()
  await page.getByRole('button', { name: 'New division' }).first().click()
  await pick(page, 'department_id', department)
  await panel.locator('#name_kh').fill(`ការិយាល័យ ${stamp}`)
  await panel.locator('#name_en').fill(division)
  await panel.getByRole('button', { name: 'Create division' }).click()
  await expect(page.getByRole('status')).toContainText(`${division} saved`)
  await page.getByPlaceholder('Search name or short name').fill(division)
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await expect(page.locator('tbody tr').first()).toContainText(department)

  await page.getByRole('link', { name: 'Positions' }).click()
  await page.getByRole('button', { name: 'New position' }).first().click()
  await panel.locator('#name_kh').fill(`តួនាទី ${stamp}`)
  await panel.locator('#name_en').fill(position)
  await panel.getByRole('button', { name: 'Create position' }).click()
  await expect(page.getByRole('status')).toContainText(`${position} saved`)
  await page.getByPlaceholder('Search Khmer or English name').fill(position)
  await expect(page.locator('tbody tr')).toHaveCount(1)

  await page.locator('tbody tr').first().click()
  await panel.locator('.panel-foot').getByRole('switch', { name: 'Active' }).click()
  await expect(page.getByRole('alertdialog')).toContainText('No users have it.')
  await page.getByRole('alertdialog').getByRole('button', { name: 'Make inactive' }).click()
  await page.getByRole('group', { name: 'Status' }).getByRole('button', { name: 'All' }).click()
  await expect(page.locator('tbody tr').first()).toContainText('Inactive')
})
