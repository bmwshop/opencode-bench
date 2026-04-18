import { validateToken } from './token'

export function authMiddleware(req: Request, res: Response, next: Function) {
  const header = req.headers.authorization
  if (!header?.startsWith("Bearer ")) {
    return res.status(401).json({ error: "MISSING_TOKEN" })
  }
  const payload = validateToken(header.slice(7))
  if (!payload) {
    return res.status(401).json({ error: "INVALID_TOKEN" })
  }
  req.user = payload
  next()
}

export function requireRole(...roles: string[]) {
  return (req: Request, res: Response, next: Function) => {
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({ error: "FORBIDDEN" })
    }
    next()
  }
}
