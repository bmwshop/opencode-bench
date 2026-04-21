export function login(user: string, pass: string) {
  return fetch("/api/login", {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ user, pass })
  })
}
