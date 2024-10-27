import type { paths } from './schema'
import { apiFetch } from './base'

const homesPath = '/api/homes/v1/homes'
type Homes = paths[typeof homesPath]
export type GetHomesResponse = Homes['get']['responses'][200]['content']['application/json']
export type PostHomesRequest = Homes['post']['requestBody']['content']['application/json']

export default {
  async getHomes() {
    return apiFetch<GetHomesResponse, void>('GET', homesPath)
  },
  async postHomes(newHome: PostHomesRequest) {
    return apiFetch<void, PostHomesRequest>('GET', homesPath, newHome)
  }
}
