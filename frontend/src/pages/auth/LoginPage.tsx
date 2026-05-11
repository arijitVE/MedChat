import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import type { z } from 'zod';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { normalizeApiError } from '../../lib/apiError';
import { loginSchema } from '../../validation/authSchemas';
import { useLogin } from '../../hooks/useAuth';

type LoginFormValues = z.infer<typeof loginSchema>;
type LoginFieldErrors = Partial<Record<keyof LoginFormValues, string>>;

function getPostAuthPath(role: string, verificationStatus?: string | null): string {
  if (role === 'doctor' && verificationStatus !== 'approved') {
    return '/doctor/verification-pending';
  }
  return `/${role}`;
}

function getLoginErrorMessage(error: unknown): string {
  const apiError = normalizeApiError(error);

  if (apiError.statusCode === 401) {
    return 'Invalid email or password';
  }

  if (apiError.statusCode === 429) {
    return 'Too many attempts. Please wait 15 minutes.';
  }

  return apiError.message;
}

function getFieldErrors(values: LoginFormValues): LoginFieldErrors {
  const result = loginSchema.safeParse(values);

  if (result.success) {
    return {};
  }

  return result.error.issues.reduce<LoginFieldErrors>((errors, issue) => {
    const field = issue.path[0];
    if (field === 'email' || field === 'password') {
      return { ...errors, [field]: issue.message };
    }
    return errors;
  }, {});
}

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useLogin();
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<LoginFieldErrors>({});
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<LoginFormValues>({
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = async (values: LoginFormValues) => {
    const nextFieldErrors = getFieldErrors(values);
    setFieldErrors(nextFieldErrors);
    setFormError(null);

    if (Object.keys(nextFieldErrors).length > 0) {
      return;
    }

    try {
      const response = await login.mutateAsync(values);
      navigate(getPostAuthPath(response.user.role, response.user.verification_status));
    } catch (error) {
      setFormError(getLoginErrorMessage(error));
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-clinical-bg px-4 py-10">
      <Card className="w-full max-w-md">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-clinical-text-primary">Sign in</h1>
          <p className="mt-1 text-sm text-clinical-text-secondary">
            Access your HDMIS workspace.
          </p>
        </div>

        {formError ? (
          <div
            className="mb-4 rounded-md border border-clinical-critical bg-clinical-critical-bg px-3 py-2 text-sm text-clinical-critical"
            role="alert"
            aria-live="assertive"
          >
            {formError}
          </div>
        ) : null}

        <form className="space-y-4" onSubmit={(event) => void handleSubmit(onSubmit)(event)}>
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-clinical-text-primary">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
              aria-invalid={fieldErrors.email ? true : undefined}
              aria-describedby={fieldErrors.email ? 'email-error' : undefined}
              {...register('email')}
            />
            {fieldErrors.email ? (
              <p id="email-error" className="mt-1 text-sm text-clinical-critical">
                {fieldErrors.email}
              </p>
            ) : null}
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-clinical-text-primary">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
              aria-invalid={fieldErrors.password ? true : undefined}
              aria-describedby={fieldErrors.password ? 'password-error' : undefined}
              {...register('password')}
            />
            {fieldErrors.password ? (
              <p id="password-error" className="mt-1 text-sm text-clinical-critical">
                {fieldErrors.password}
              </p>
            ) : null}
          </div>

          <Button className="w-full" type="submit" loading={isSubmitting || login.isPending}>
            Sign in
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-clinical-text-secondary">
          Need an account?{' '}
          <Link className="font-medium text-clinical-primary hover:underline" to="/signup">
            Create account
          </Link>
        </p>
      </Card>
    </main>
  );
}
