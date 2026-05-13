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
    <main className="min-h-screen bg-clinical-bg px-4 py-8 sm:px-8 lg:px-12">
      <div className="mx-auto grid min-h-[calc(100vh-4rem)] w-full max-w-7xl items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(420px,520px)]">
        <section className="max-w-2xl">
          <div className="inline-flex w-fit self-start rounded-full border border-clinical-primary-light bg-clinical-surface px-4 py-2 text-sm font-semibold text-clinical-primary shadow-sm">
            HDIMS
          </div>
          <h1 className="mt-8 max-w-2xl text-4xl font-semibold leading-tight text-clinical-text-primary sm:text-5xl">
            Healthcare Data &amp; Insights Management System
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-8 text-clinical-text-secondary">
            Secure dashboards for reports, vital signs, analytics, and role-based healthcare operations.
          </p>
        </section>

        <Card className="w-full p-7 shadow-xl shadow-slate-200/80 sm:p-9">
          <div className="mb-8">
            <p className="text-sm font-semibold text-clinical-primary">Welcome back</p>
            <h2 className="mt-3 text-3xl font-semibold text-clinical-text-primary">Sign in to your dashboard</h2>
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

          <form className="space-y-5" onSubmit={(event) => void handleSubmit(onSubmit)(event)}>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-clinical-text-primary">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="name@example.com"
                className="mt-2 block min-h-12 w-full rounded-lg border border-clinical-border bg-clinical-surface px-4 py-3 text-sm text-clinical-text-primary outline-none placeholder:text-clinical-text-muted focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
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
                placeholder="Enter password"
                className="mt-2 block min-h-12 w-full rounded-lg border border-clinical-border bg-clinical-surface px-4 py-3 text-sm text-clinical-text-primary outline-none placeholder:text-clinical-text-muted focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
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

            <Button className="min-h-12 w-full rounded-lg bg-clinical-primary-dark" type="submit" loading={isSubmitting || login.isPending}>
              Sign in
            </Button>
          </form>

          <p className="mt-7 text-center text-sm text-clinical-text-secondary">
            No account yet?{' '}
            <Link className="font-semibold text-clinical-primary hover:underline" to="/signup">
              Create one
            </Link>
          </p>
        </Card>
      </div>
    </main>
  );
}
