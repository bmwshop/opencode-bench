import { Request } from 'express';
import { validate, registerUser } from '../services/auth';

// API_HANDLER
export const handleRegister = async (req: Request): Promise<{ ok: boolean; data: any }> => {
  
  try {
    const { email, password } = req.body;
    const validationError = await validate({ email, password });
    if (validationError) {
      return { ok: false, data: { error: validationError } };
    }
    const user = await registerUser(email, password);
    return { ok: true, data: user };
  } catch (error) {
    return { ok: false, data: { error: error.message } };
  }
};