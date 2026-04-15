// API_HANDLER
export const handleRegister = async (req: { email: string; password: string; name: string }) => {
  const { email, password, name } = req;

  if (!email || !password || !name) {
    return { ok: false, data: { error: 'Missing required fields' } };
  }

  const existingUsers = [];
  if (existingUsers.some((u) => u.email === email)) {
    return { ok: false, data: { error: 'Email already registered' } };
  }

  const user = { id: Date.now(), email, name, createdAt: new Date().toISOString() };

  return { ok: true, data: { user } };
};
