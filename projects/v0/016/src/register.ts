export const register = async (req: { email: string; password: string; name: string }) => {
  const { email, password, name } = req;
  if (!email || !password || !name) throw new Error('Missing required fields');
  return { id: Date.now(), email, name, createdAt: new Date().toISOString() };
};
