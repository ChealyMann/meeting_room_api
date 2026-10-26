import { expect, test } from '@playwright/test'

// Needs the API running (run.bat) and an Admin whose password is already changed.
const email = process.env.E2E_ADMIN_EMAIL
const password = process.env.E2E_ADMIN_PASSWORD

// eslint-disable-next-line playwright/no-skipped-test -- skipped on purpose when no account is given
test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run this test.')

test('sign in, edit my profile, stay signed in after reload, sign out', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/sign-in/)

  await page.getByLabel('Email').fill(email!)
  await page.getByLabel('Password', { exact: true }).fill(password!)
  await page.getByRole('button', { name: 'Sign in' }).click()

  const rail = page.getByRole('complementary', { name: 'Main' })
  await expect(rail.getByRole('link', { name: 'Rooms' })).toHaveAttribute('aria-current', 'page')
  await expect(page.getByText(/Phnom Penh \d\d:\d\d/)).toBeVisible()

  await rail.getByRole('link', { name: /My profile/ }).click()
  const phone = page.getByLabel('Phone')
  await expect(phone).toBeEditable()
  const before = await phone.inputValue()
  // A phone that differs from the current one.
  const next = ['012 345 678', '012 345 679'].find((value) => value !== before)!

  await phone.fill(next)
  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('status').getByText('Profile saved')).toBeVisible()

  // A reload keeps the session (refresh token in sessionStorage) and the saved phone.
  await page.reload()
  await expect(page.getByLabel('Phone')).toHaveValue(next)

  // Put the phone back as it was.
  await page.getByLabel('Phone').fill(before)
  await page.getByRole('button', { name: 'Save changes' }).click()
  await expect(page.getByRole('status').getByText('Profile saved')).toBeVisible()

  await rail.getByRole('button', { name: 'Sign out' }).click()
  await expect(page).toHaveURL(/\/sign-in/)
})
