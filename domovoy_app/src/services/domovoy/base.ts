export function getHeaders(): Headers {
  const sessionId = window.localStorage.getItem('x-session-key')
  return new Headers({
    'X-Session-Key': sessionId || ''
  })
}

const apiRoot =
  window.location.hostname == 'localhost'
    ? 'http://localhost:8000'
    : `${window.location.protocol}//${window.location.host}`

export async function apiFetch<ResponseData, Request = void>(
  method: 'GET' | 'POST' | 'DELETE' | 'PUT' | 'PATCH',
  endpoint: string,
  data?: Request,
  hashcash?: string
): Promise<{ data: ResponseData; response: Response }> {
  const headers = getHeaders()
  if (hashcash) {
    headers.set('X-Hashcash', hashcash)
  }
  const config: RequestInit = {
    method: method,
    headers
  }
  if (data) {
    config.body = JSON.stringify(data)
    headers.set('Content-Type', 'application/json')
  }
  const response = await fetch(`${apiRoot}${endpoint}`, config)
  let responseData = null
  try {
    responseData = await response.json()
  } catch (err) {}
  return {
    data: responseData as ResponseData,
    response: response
  }
}
