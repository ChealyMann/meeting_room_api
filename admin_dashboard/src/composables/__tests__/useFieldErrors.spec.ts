import { describe, expect, it } from 'vitest'

import { ApiError } from '../../api/errors'
import { useFieldErrors } from '../useFieldErrors'

describe('useFieldErrors', () => {
  it('copies field errors and the message from an ApiError', () => {
    const { errors, formMessage, apply } = useFieldErrors()

    apply(new ApiError(422, 'VALIDATION_ERROR', 'Invalid request.', { phone: 'Too long (max 20).' }))

    expect(errors.value.phone).toBe('Too long (max 20).')
    expect(formMessage.value).toBe('Invalid request.')
  })

  it('replaces old errors on the next apply', () => {
    const { errors, apply } = useFieldErrors()
    apply(new ApiError(422, 'VALIDATION_ERROR', 'Invalid request.', { phone: 'x' }))

    apply(new ApiError(422, 'VALIDATION_ERROR', 'Invalid request.', { avatar_url: 'y' }))

    expect(errors.value).toEqual({ avatar_url: 'y' })
  })

  it('gives a plain message for anything that is not an ApiError', () => {
    const { errors, formMessage, apply } = useFieldErrors()

    apply(new Error('boom'))

    expect(errors.value).toEqual({})
    expect(formMessage.value).toBe('Something went wrong.')
  })

  it('clear empties both', () => {
    const { errors, formMessage, apply, clear } = useFieldErrors()
    apply(new ApiError(422, 'VALIDATION_ERROR', 'Invalid request.', { phone: 'x' }))

    clear()

    expect(errors.value).toEqual({})
    expect(formMessage.value).toBe('')
  })
})
