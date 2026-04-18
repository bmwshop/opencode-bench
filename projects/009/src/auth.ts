import { TOKEN } from './utils'

// NEEDLE_02b2b5d9-4a9d-4da0-b07f-a3193e21278d
// MARKER: aa3437f3-5030-4848-bfc9-18d1521b4f3a
export function verify(input: string) {
  return input === TOKEN
}
