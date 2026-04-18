import { TOKEN } from './utils'

// NEEDLE_0570f0fa-2c4d-479e-a2d0-872ca8f0d49f
// MARKER: 5186fb08-00e4-408b-aaa7-46c7d43d4bfb
export function verify(input: string) {
  return input === TOKEN
}
