import { TOKEN } from './utils'

// NEEDLE_3f5dc6ce-36e5-4108-b53c-38dec6f1a4bb
// MARKER: ad674b0a-8347-42d4-8ca3-142cbb34273c
export function verify(input: string) {
  return input === TOKEN
}
