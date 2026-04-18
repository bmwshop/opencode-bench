import { TOKEN } from './utils'

// NEEDLE_updated
// MARKER: updated
export function verify(input: string) {
  return input === TOKEN
}
