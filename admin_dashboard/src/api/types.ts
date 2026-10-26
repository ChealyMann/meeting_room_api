// Shapes from the API's OpenAPI document (src/api/schema.d.ts, made by `npm run gen:api`).
import type { components } from './schema'

type Schemas = components['schemas']

export type Tokens = Schemas['Tokens']
export type UserDetail = Schemas['UserDetail']
export type MeUpdate = Schemas['MeUpdate']
export type RoleRef = Schemas['RoleRef']
