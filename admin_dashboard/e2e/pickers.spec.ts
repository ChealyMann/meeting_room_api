import { expect, test, type Page } from '@playwright/test'

import { pick } from './picker'

// The app's dropdowns (SearchPicker) in a real browser, without the real API.
const ME = {
  id: 1,
  name_en: 'Sok Dara',
  email: 'dara@company.com',
  roles: [{ code: 'ADMIN', name_en: 'Admin', name_kh: 'អ្នកគ្រប់គ្រង' }],
  must_change_password: false,
  avatar_url: null,
  updated_at: '2026-10-01T00:00:00Z',
}
const st = { is_active: true, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:00Z' }
const PP = { code: 'PP', name_en: 'Phnom Penh', name_kh: 'ភ្នំពេញ' }
const OFFICES = ['Head Office', 'Battambang Branch', 'Kampot Branch', 'Siem Reap Branch', 'Takeo Branch', 'Kandal Branch'].map(
  (name_en, i) => ({ id: i + 1, name_en, name_kh: 'ការិយាល័យ', province: PP, description: null, address: null, map_query: null, ...st }),
)
const ROOMS = Array.from({ length: 20 }, (_, i) => ({
  id: 12 + i,
  name_en: `Room ${i + 1}`,
  name_kh: `បន្ទប់ ${i + 1}`,
  short_desc: null,
  capacity: 10,
  size_sqm: null,
  start_time: '08:00',
  end_time: '17:00',
  category: { id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ' },
  floor: { id: 7, floor_label: '3rd floor' },
  building: { id: 5, name_en: 'Building A', name_kh: 'អគារ A', short_name: null },
  location: { id: 1, name_en: 'Head Office', name_kh: 'ការិយាល័យកណ្តាល' },
  province: PP,
  owner: null,
  cover_photo: null,
  is_active: true,
  is_bookable: true,
  is_private: false,
}))

async function signedIn(page: Page, path: string, posts: string[] = []) {
  await page.addInitScript(() => sessionStorage.setItem('nbc.admin.refresh', 'R0'))
  await page.route('**/api/v1/**', (route) => {
    const url = new URL(route.request().url())
    if (route.request().method() === 'POST' && url.pathname === '/api/v1/rooms') {
      posts.push(route.request().postData() ?? '')
      return route.fulfill({ status: 201, json: { ...ROOMS[0], description: null, photos: [], equipment: [] } })
    }
    const lists: Record<string, unknown[]> = {
      '/api/v1/locations': OFFICES,
      '/api/v1/buildings': [{ id: 5, location_id: 1, name_en: 'Building A', name_kh: 'អគារ A', short_name: null, sort_order: 0, ...st }],
      '/api/v1/floors': [{ id: 7, building_id: 5, floor_label: '3rd floor', sort_order: 0, ...st }],
      '/api/v1/categories': [{ id: 1, name_en: 'Meeting room', name_kh: 'បន្ទប់ប្រជុំ', sort_order: 0, ...st }],
    }
    if (url.pathname === '/api/v1/auth/refresh') {
      return route.fulfill({ json: { access_token: 'A1', refresh_token: 'R1', token_type: 'bearer' } })
    }
    if (url.pathname === '/api/v1/me') return route.fulfill({ json: ME })
    if (url.pathname === '/api/v1/rooms') return route.fulfill({ json: { items: ROOMS, page: 1, size: 20, total: 57 } })
    const items = lists[url.pathname] ?? []
    return route.fulfill({ json: { items, page: 1, size: 100, total: items.length } })
  })
  await page.setViewportSize({ width: 1366, height: 800 })
  await page.goto(path)
}

test('the room form is filled with pickers inside the side panel', async ({ page }) => {
  const posts: string[] = []
  await signedIn(page, '/?room=new', posts)
  const panel = page.getByRole('dialog')

  await panel.locator('#name_kh').fill('បន្ទប់ថ្មី')
  await panel.locator('#name_en').fill('New Room')
  await pick(page, 'location_id', 'Head Office')
  await pick(page, 'building_id', { first: true })
  await pick(page, 'floor_id', { first: true })
  await pick(page, 'category_id', 'Meeting room')
  await panel.locator('#capacity').fill('8')

  // The owner list near the panel's foot opens fully inside the window.
  await page.locator('button#room_owner_id').click()
  const list = page.locator(`#${await page.locator('button#room_owner_id').getAttribute('aria-controls')}`)
  const box = (await list.boundingBox())!
  expect(box.y).toBeGreaterThanOrEqual(0)
  expect(box.y + box.height).toBeLessThanOrEqual(800)
  await page.keyboard.press('Escape')

  await panel.getByRole('button', { name: 'Create room' }).click()
  await expect.poll(() => posts.length).toBe(1)
  expect(JSON.parse(posts[0]!)).toMatchObject({ floor_id: 7, category_id: 1, capacity: 8 })
})

test('the rows-per-page picker at the bottom opens upward', async ({ page }) => {
  await signedIn(page, '/')
  await expect(page.locator('tbody tr')).toHaveCount(20)

  const button = page.locator('button#rows-per-page')
  await button.click()
  const list = page.locator(`#${await button.getAttribute('aria-controls')}`)
  const listBox = (await list.boundingBox())!
  const buttonBox = (await button.boundingBox())!
  expect(listBox.y + listBox.height).toBeLessThanOrEqual(buttonBox.y)

  await list.getByRole('option', { name: '50', exact: true }).click()
  await expect(page).toHaveURL(/size=50/)
})
