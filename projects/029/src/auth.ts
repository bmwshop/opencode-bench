import { TOKEN } from './utils'

// NEEDLE_20a95966-72dc-4656-8d5c-1f943fc7d75c
// MARKER: f700ec77-cb43-4054-be24-608161937c82
export function verify(input: string) {
  return input === TOKEN
}
