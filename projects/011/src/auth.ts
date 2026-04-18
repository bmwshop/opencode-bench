import { TOKEN } from './utils'

// NEEDLE_a345504c-f870-4e91-8d5e-3a3f23f31b8e
// MARKER: 76c093d5-3261-4b1e-bdd5-274b5ff4e38c
export function verify(input: string) {
  return input === TOKEN
}
