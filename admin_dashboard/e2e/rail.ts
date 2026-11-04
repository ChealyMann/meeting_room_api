import type { Page } from '@playwright/test'

/** Setup groups in the sidebar fold: open one (if it is closed) before clicking its links. */
export async function openGroup(page: Page, name: 'Places' | 'Catalog' | 'Organisation' | 'People'): Promise<void> {
  const fold = page.locator('aside button.fold', { hasText: name })
  if ((await fold.getAttribute('aria-expanded')) === 'false') await fold.click()
}
