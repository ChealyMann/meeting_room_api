import { describe, expect, it } from 'vitest'

import { fileProblem, sizeText } from '../attachments'

const MB = 1024 * 1024

describe('fileProblem', () => {
  it('takes a PDF, Word or Excel file in any case', () => {
    for (const name of ['a.PDF', 'b.doc', 'c.docx', 'd.xls', 'e.XLSX']) expect(fileProblem({ name, size: 1 }, 0)).toBeNull()
  })

  it('says the same as the server for a wrong type, a big file or a 4th file', () => {
    expect(fileProblem({ name: 'a.png', size: 1 }, 0)).toBe('Only PDF, Word or Excel files.')
    expect(fileProblem({ name: 'agenda', size: 1 }, 0)).toBe('Only PDF, Word or Excel files.')
    expect(fileProblem({ name: 'a.pdf', size: 10 * MB + 1 }, 0)).toBe('File too big (max 10 MB).')
    expect(fileProblem({ name: 'a.pdf', size: 10 * MB }, 0)).toBeNull()
    expect(fileProblem({ name: 'a.pdf', size: 1 }, 3)).toBe('Up to 3 files.')
  })

  it('refuses an empty file', () => {
    expect(fileProblem({ name: 'a.pdf', size: 0 }, 0)).toBe('The file is empty.')
  })
})

describe('sizeText', () => {
  it('shows KB under 1 MB and MB with one decimal above', () => {
    expect(sizeText(839680)).toBe('820 KB')
    expect(sizeText(1258291)).toBe('1.2 MB')
    expect(sizeText(300)).toBe('1 KB')
  })
})
