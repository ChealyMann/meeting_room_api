import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import AttachmentList from '../AttachmentList.vue'

const FILES = [
  { id: 1, name: 'agenda.pdf', size: 839680, url: '/api/v1/bookings/7/attachments/1' },
  { id: 2, name: 'budget.xlsx', size: 1258291, url: '/api/v1/bookings/7/attachments/2' },
]

function pick(wrapper: ReturnType<typeof mount>, file: File) {
  const input = wrapper.get('input[type="file"]')
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  return input.trigger('change')
}

describe('AttachmentList', () => {
  it('shows each file as a chip, with its size on hover', () => {
    const w = mount(AttachmentList, { props: { files: FILES } })
    expect(w.findAll('.att-chip').length).toBe(2)
    expect(w.findAll('.att-name').map((n) => n.text())).toEqual(['agenda.pdf', 'budget.xlsx'])
    expect(w.findAll('.att-name').map((n) => n.attributes('title'))).toEqual(['agenda.pdf · 820 KB', 'budget.xlsx · 1.2 MB'])
  })

  it('says what is allowed under the chips when editable', () => {
    const w = mount(AttachmentList, { props: { files: FILES, editable: true } })
    expect(w.get('.att-note').text()).toBe('PDF, Word or Excel · up to 3 · 10 MB each')
  })

  it('shows nothing when there is no file and it is read only', () => {
    const w = mount(AttachmentList, { props: { files: [] } })
    expect(w.find('.att').exists()).toBe(false)
  })

  it('opens a file on click', async () => {
    const w = mount(AttachmentList, { props: { files: FILES } })
    await w.findAll('.att-name')[1]!.trigger('click')
    expect(w.emitted('open')).toEqual([[1]])
  })

  it('has no Add file or Remove when read only', () => {
    const w = mount(AttachmentList, { props: { files: FILES } })
    expect(w.text()).not.toContain('Add file')
    expect(w.find('[aria-label="Remove agenda.pdf"]').exists()).toBe(false)
  })

  it('adds and removes when editable', async () => {
    const w = mount(AttachmentList, { props: { files: FILES, editable: true } })
    expect(w.text()).toContain('Add file')
    await w.get('[aria-label="Remove agenda.pdf"]').trigger('click')
    expect(w.emitted('remove')).toEqual([[0]])
    const good = new File(['%PDF-1'], 'notes.pdf')
    await pick(w, good)
    expect(w.emitted('add')).toEqual([[good]])
  })

  it('stops a file that is too big, with the reason', async () => {
    const w = mount(AttachmentList, { props: { files: [], editable: true } })
    const big = new File(['x'], 'big.pdf')
    Object.defineProperty(big, 'size', { value: 11 * 1024 * 1024 })
    await pick(w, big)
    expect(w.emitted('add')).toBeUndefined()
    expect(w.get('[role="alert"]').text()).toBe('File too big (max 10 MB).')
  })

  it('hides Add file once 3 files are there', () => {
    const three = [...FILES, { id: 3, name: 'c.doc', size: 10 }]
    const w = mount(AttachmentList, { props: { files: three, editable: true } })
    expect(w.text()).not.toContain('Add file')
    expect(w.text()).toContain('Up to 3 files.')
  })

  it('turns the buttons off while busy', () => {
    const w = mount(AttachmentList, { props: { files: FILES, editable: true, busy: true } })
    expect(w.get('[aria-label="Remove agenda.pdf"]').attributes('disabled')).toBeDefined()
    expect(w.get('.att-add').attributes('disabled')).toBeDefined()
  })
})
