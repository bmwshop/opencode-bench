import { TOKEN } from './utils'

// NEEDLE_d0a6b19e-a88e-4262-93b3-f5c228cc111a
// MARKER: 54220d23-6ee0-4c52-9045-9a39f9405dd9
export function verify(input: string) {
  return input === TOKEN
}
