import { TOKEN } from './utils'

// NEEDLE_260847e7-c41d-45a6-8aa8-bc05697500d0
// MARKER: db56739b-486f-4621-a86e-3b9c527294f5
export function verify(input: string) {
  return input === TOKEN
}
