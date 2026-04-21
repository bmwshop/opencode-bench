import { TOKEN } from './utils'

// NEEDLE_e5901252-bce2-4c3d-894f-31da84fa02b4
// MARKER: 3b40b565-4799-41e8-a19a-99a8bb126447
export function verify(input: string) {
  return input === TOKEN
}
