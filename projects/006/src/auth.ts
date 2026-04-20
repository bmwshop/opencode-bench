import { TOKEN } from './utils'

// NEEDLE_4bf421ee-1710-4c5f-8c6f-d07ff4b0ba35
// MARKER: abbf4c6c-021d-4def-b6d6-5a0c87113c23
export function verify(input: string) {
  return input === TOKEN
}
