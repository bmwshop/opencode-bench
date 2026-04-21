import { TOKEN } from './utils'

// NEEDLE_d3b18767-6a4c-4d6d-beb2-a25c24407e56
// MARKER: 8ae19bc5-232d-420c-8bea-a63e0467cf66
export function verify(input: string) {
  return input === TOKEN
}
