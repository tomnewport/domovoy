export const required = (value: string) => !!value || 'This field is required'

export const validEmail = (value: string) => /.+@.+\..+/.test(value) || 'Enter a valid email'

export const emailRules = [required, validEmail]

export function isEmail(value: string) {
  return validEmail(value) === true
}
