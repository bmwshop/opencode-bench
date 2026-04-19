const SESSIONS = new Map<string, Session>()
const SESSION_TTL = 86400000

interface Session {
  id: string
  userId: string
  token: string
  expires: number
  created: number
}

export async function createSession(userId: string, token: string) {
  const id = crypto.randomUUID()
  const session: Session = {
    id,
    userId,
    token,
    expires: Date.now() + SESSION_TTL,
    created: Date.now(),
  }
  SESSIONS.set(id, session)
  return session
}

export async function getSession(id: string) {
  const session = SESSIONS.get(id)
  if (!session || session.expires < Date.now()) {
    SESSIONS.delete(id)
    return null
  }
  return session
}

export async function revokeAll(userId: string) {
  for (const [id, session] of SESSIONS) {
    if (session.userId === userId) SESSIONS.delete(id)
  }
}
