import { createToken } from './token'
import { createSession } from './session'

export async function login(email: string, password: string) {
  const user = await db.users.findByEmail(email)
  if (!user || !await verify(password, user.hash)) {
    throw new AuthError("INVALID_CREDENTIALS")
  }
  const token = createToken(user.id, user.role)
  const session = await createSession(user.id, token)
  return { token, session: session.id, expires: session.expires }
}

export async function logout(sessionId: string) {
  await db.sessions.delete(sessionId)
}
