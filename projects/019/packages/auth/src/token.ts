import { sign, verify as jwtVerify } from 'jsonwebtoken'

const SECRET = process.env.JWT_SECRET || "dev-secret-do-not-use"
const EXPIRY = 3600

export function createToken(userId: string, role: string) {
  return sign({ sub: userId, role }, SECRET, { expiresIn: EXPIRY })
}

export function validateToken(token: string) {
  try {
    return jwtVerify(token, SECRET) as { sub: string; role: string }
  } catch {
    return null
  }
}

export function refreshToken(token: string) {
  const payload = validateToken(token)
  if (!payload) return null
  return createToken(payload.sub, payload.role)
}
