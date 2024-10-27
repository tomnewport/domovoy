import type { paths } from './schema'
import { apiFetch } from './base'

const v1SessionPath = '/api/users/v1/session'
type V1Session = paths[typeof v1SessionPath]
export type GetSessionResponse = V1Session['get']['responses'][200]['content']['application/json']
export type PostSessionRequest = V1Session['post']['requestBody']['content']['application/json']
export type PostSessionResponse = V1Session['post']['responses'][200]['content']['application/json']

const v1HashcashPath = '/api/users/v1/hashcash'
type V1Hashcash = paths[typeof v1HashcashPath]
export type GetHashcashResponse = V1Hashcash['get']['responses'][200]['content']['application/json']

const v1NewPath = '/api/users/v1/new'
type V1New = paths[typeof v1NewPath]
export type NewUserRequest = V1New['post']['requestBody']['content']['application/json']

const v1EmailCodePath = '/api/users/v1/email_code'
type V1EmailCode = paths[typeof v1EmailCodePath]
export type EmailCodeRequest = V1EmailCode['post']['parameters']['query']

export default {
  async getSession() {
    return apiFetch<GetSessionResponse, void>('GET', v1SessionPath)
  },
  async postSession(factors: PostSessionRequest) {
    return apiFetch<PostSessionResponse, PostSessionRequest>('POST', v1SessionPath, factors)
  },
  async deleteSession() {
    return apiFetch<void, void>('DELETE', v1SessionPath)
  },
  async getHashcash() {
    return apiFetch<GetHashcashResponse, void>('GET', v1HashcashPath)
  },
  async postNew(user: NewUserRequest, hashcash: string) {
    return apiFetch<void, NewUserRequest>('POST', v1NewPath, user, hashcash)
  },
  async postEmailCode(email: string, hashcash: string) {
    return apiFetch<void, void>(
      'POST',
      `${v1EmailCodePath}?${new URLSearchParams({ email })}`,
      undefined,
      hashcash
    )
  }
}
