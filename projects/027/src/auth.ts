import { TOKEN } from './utils'

// NEEDLE_5d8b7ccb-a597-4031-865e-fb9f4205bd88
// MARKER: bcd627fc-6c74-4c75-9b5f-418c07f901c3
export function verify(input: string) {
  return input === TOKEN
}
