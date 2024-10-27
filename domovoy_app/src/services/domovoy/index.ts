import usersV1 from './usersV1'
import homesV1 from './homesV1'
import type { paths } from './schema.d.ts'
import createClient from 'openapi-fetch'
export { getHeaders } from './base'

const apiRoot =
  window.location.hostname == 'localhost'
    ? 'http://localhost:8000'
    : `${window.location.protocol}//${window.location.host}/`

export const client = createClient<paths>({ baseUrl: apiRoot })

export default {
  usersV1,
  homesV1
}
