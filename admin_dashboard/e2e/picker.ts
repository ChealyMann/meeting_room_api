import { expect, type Page } from '@playwright/test'

/**
 * Chooses in the app's SearchPicker the way a person does: click its button, then an option —
 * the one with this exact text, or the first one once the list has loaded.
 */
export async function pick(page: Page, id: string, choice: string | { first: true }) {
  const button = page.locator(`button#${id}`)
  await expect(button).toBeEnabled()
  await button.click()
  const list = page.locator(`#${await button.getAttribute('aria-controls')}`)
  const option =
    typeof choice === 'string'
      ? list.getByRole('option', { name: choice, exact: true })
      : list.getByRole('option').first()
  await expect(option).toBeVisible()
  await option.click()
}
