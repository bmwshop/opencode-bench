export function login(user: string, pass: string) {
  return fetch("/api/login", { body: JSON.stringify({ user, pass }) })
}
