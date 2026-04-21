import { TOKEN } from './utils'

// NEEDLE_3eafa60d-2bfd-48fc-9917-4e6f9be2594d
// MARKER: 3e74e5a4-4b54-4197-b742-23552197723d
export function verify(input: string) {
  return input === TOKEN
}
