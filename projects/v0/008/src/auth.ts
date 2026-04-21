import { TOKEN } from './utils'

// NEEDLE_b6ffcaf1-360d-4600-a0cf-2dbc2d32a2ef
// MARKER: b7bd31de-21a2-43bb-aa35-f9dede46c3c8
export function verify(input: string) {
  return input === TOKEN
}
