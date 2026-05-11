import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import type { z } from 'zod';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { normalizeApiError } from '../../lib/apiError';
import { useSignup } from '../../hooks/useAuth';
import { signupSchema } from '../../validation/authSchemas';
import { doctorSpecializations, signupSexValues } from '../../types/auth';
import type { DoctorSpecialization, SignupRequest, SignupSex } from '../../types/auth';

type SignupFormValues = z.infer<typeof signupSchema>;
type SignupFieldErrors = Partial<Record<keyof SignupFormValues, string>>;
type SexOption = {
  value: SignupSex;
  label: string;
};

const sexOptions: readonly SexOption[] = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
];

const defaultDoctorSpecialization: DoctorSpecialization = 'General Physician';

const signupFields = [
  'email',
  'password',
  'full_name',
  'role',
  'phone',
  'phone_number',
  'gender',
  'license_number',
  'specialization',
  'date_of_birth',
  'sex',
  'blood_group',
  'allergies',
  'chronic_conditions',
  'address',
  'emergency_contact',
  'claim_patient_uid',
] as const;

function trimToNull(value: string | undefined): string | null {
  const trimmed = value?.trim() ?? '';
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeSignupSex(value: SignupFormValues['sex']): SignupSex | null {
  if (value && signupSexValues.includes(value)) {
    return value;
  }

  return null;
}

function calculateAge(dateOfBirth: string | undefined): number | null {
  const value = trimToNull(dateOfBirth);
  if (!value) {
    return null;
  }

  const dob = new Date(`${value}T00:00:00`);
  if (Number.isNaN(dob.getTime())) {
    return null;
  }

  const today = new Date();
  let age = today.getFullYear() - dob.getFullYear();
  const monthDelta = today.getMonth() - dob.getMonth();
  if (monthDelta < 0 || (monthDelta === 0 && today.getDate() < dob.getDate())) {
    age -= 1;
  }
  return age >= 0 ? age : null;
}

function normalizeSignupPayload(values: SignupFormValues): SignupRequest {
  const phoneValue = trimToNull(values.phone_number) ?? trimToNull(values.phone);
  const basePayload = {
    email: values.email.trim(),
    password: values.password.trim(),
    role: values.role,
    full_name: values.full_name.trim(),
    phone: phoneValue,
    phone_number: phoneValue,
  };

  if (values.role === 'doctor') {
    return {
      ...basePayload,
      license_number: trimToNull(values.license_number),
      specialization: values.specialization,
      date_of_birth: null,
      sex: null,
      claim_patient_uid: null,
    };
  }

  return {
    ...basePayload,
    license_number: null,
    specialization: null,
    age: calculateAge(values.date_of_birth),
    gender: normalizeSignupSex(values.gender),
    date_of_birth: trimToNull(values.date_of_birth),
    sex: normalizeSignupSex(values.gender ?? values.sex),
    blood_group: trimToNull(values.blood_group),
    allergies: trimToNull(values.allergies),
    chronic_conditions: trimToNull(values.chronic_conditions),
    address: trimToNull(values.address),
    emergency_contact: trimToNull(values.emergency_contact),
    claim_patient_uid: trimToNull(values.claim_patient_uid),
  };
}

function getSignupErrorMessage(error: unknown): string {
  const apiError = normalizeApiError(error);

  if (apiError.statusCode === 429) {
    return 'Too many attempts. Please wait 15 minutes.';
  }

  return apiError.message;
}

function getFieldErrors(values: SignupFormValues): SignupFieldErrors {
  const result = signupSchema.safeParse(values);

  if (result.success) {
    return {};
  }

  return result.error.issues.reduce<SignupFieldErrors>((errors, issue) => {
    const field = issue.path[0];
    const matchedField = signupFields.find((candidate) => candidate === field);
    if (matchedField) {
      return { ...errors, [matchedField]: issue.message };
    }
    return errors;
  }, {});
}

export default function SignupPage() {
  const navigate = useNavigate();
  const signup = useSignup();
  const [formError, setFormError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<SignupFieldErrors>({});
  const {
    register,
    handleSubmit,
    watch,
    formState: { isSubmitting },
  } = useForm<SignupFormValues>({
    defaultValues: {
      email: '',
      password: '',
      full_name: '',
      role: 'patient',
      phone: '',
      phone_number: '',
      gender: '',
      license_number: '',
      specialization: defaultDoctorSpecialization,
      date_of_birth: '',
      sex: '',
      blood_group: '',
      allergies: '',
      chronic_conditions: '',
      address: '',
      emergency_contact: '',
      claim_patient_uid: '',
    },
  });

  const selectedRole = watch('role');
  const roleLabel = useMemo(
    () => (selectedRole === 'doctor' ? 'Doctor registration' : 'Patient registration'),
    [selectedRole],
  );

  const onSubmit = async (values: SignupFormValues) => {
    const nextFieldErrors = getFieldErrors(values);
    setFieldErrors(nextFieldErrors);
    setFormError(null);

    if (Object.keys(nextFieldErrors).length > 0) {
      return;
    }

    try {
      const response = await signup.mutateAsync(normalizeSignupPayload(values));
      navigate(`/${response.user.role}`);
    } catch (error) {
      setFormError(getSignupErrorMessage(error));
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-clinical-bg px-4 py-10">
      <Card className="w-full max-w-2xl">
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-clinical-text-primary">Create account</h1>
          <p className="mt-1 text-sm text-clinical-text-secondary">{roleLabel}</p>
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

        <form className="grid gap-4 sm:grid-cols-2" onSubmit={(event) => void handleSubmit(onSubmit)(event)}>
          <div className="sm:col-span-2">
            <label htmlFor="full_name" className="block text-sm font-medium text-clinical-text-primary">
              Full name
            </label>
            <input
              id="full_name"
              type="text"
              autoComplete="name"
              className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
              aria-invalid={fieldErrors.full_name ? true : undefined}
              aria-describedby={fieldErrors.full_name ? 'full-name-error' : undefined}
              {...register('full_name')}
            />
            {fieldErrors.full_name ? (
              <p id="full-name-error" className="mt-1 text-sm text-clinical-critical">
                {fieldErrors.full_name}
              </p>
            ) : null}
          </div>

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
              aria-describedby={fieldErrors.email ? 'signup-email-error' : undefined}
              {...register('email')}
            />
            {fieldErrors.email ? (
              <p id="signup-email-error" className="mt-1 text-sm text-clinical-critical">
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
              autoComplete="new-password"
              className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
              aria-invalid={fieldErrors.password ? true : undefined}
              aria-describedby={fieldErrors.password ? 'signup-password-error' : undefined}
              {...register('password')}
            />
            {fieldErrors.password ? (
              <p id="signup-password-error" className="mt-1 text-sm text-clinical-critical">
                {fieldErrors.password}
              </p>
            ) : null}
          </div>

          <fieldset className="sm:col-span-2">
            <legend className="block text-sm font-medium text-clinical-text-primary">Role</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              <label className="flex cursor-pointer items-center gap-2 rounded-md border border-clinical-border px-3 py-2 text-sm">
                <input type="radio" value="patient" {...register('role')} />
                Patient
              </label>
              <label className="flex cursor-pointer items-center gap-2 rounded-md border border-clinical-border px-3 py-2 text-sm">
                <input type="radio" value="doctor" {...register('role')} />
                Doctor
              </label>
            </div>
          </fieldset>

          <div>
            <label htmlFor="phone_number" className="block text-sm font-medium text-clinical-text-primary">
              Phone number
            </label>
            <input
              id="phone_number"
              type="tel"
              autoComplete="tel"
              className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
              aria-invalid={fieldErrors.phone_number ? true : undefined}
              aria-describedby={fieldErrors.phone_number ? 'phone-number-error' : undefined}
              {...register('phone_number')}
            />
            {fieldErrors.phone_number ? (
              <p id="phone-number-error" className="mt-1 text-sm text-clinical-critical">
                {fieldErrors.phone_number}
              </p>
            ) : null}
          </div>

          {selectedRole === 'doctor' ? (
            <>
              <div>
                <label htmlFor="license_number" className="block text-sm font-medium text-clinical-text-primary">
                  License number
                </label>
                <input
                  id="license_number"
                  type="text"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  aria-invalid={fieldErrors.license_number ? true : undefined}
                  aria-describedby={fieldErrors.license_number ? 'license-error' : undefined}
                  {...register('license_number')}
                />
                {fieldErrors.license_number ? (
                  <p id="license-error" className="mt-1 text-sm text-clinical-critical">
                    {fieldErrors.license_number}
                  </p>
                ) : null}
              </div>

              <div>
                <label htmlFor="specialization" className="block text-sm font-medium text-clinical-text-primary">
                  Specialization
                </label>
                <select
                  id="specialization"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  {...register('specialization')}
                >
                  {doctorSpecializations.map((specialization) => (
                    <option key={specialization} value={specialization}>
                      {specialization}
                    </option>
                  ))}
                </select>
              </div>
            </>
          ) : (
            <>
              <div>
                <label htmlFor="gender" className="block text-sm font-medium text-clinical-text-primary">
                  Gender
                </label>
                <select
                  id="gender"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  aria-invalid={fieldErrors.gender ? true : undefined}
                  aria-describedby={fieldErrors.gender ? 'gender-error' : undefined}
                  {...register('gender')}
                >
                  <option value="">Select</option>
                  {sexOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                {fieldErrors.gender ? (
                  <p id="gender-error" className="mt-1 text-sm text-clinical-critical">
                    {fieldErrors.gender}
                  </p>
                ) : null}
              </div>

              <div>
                <label htmlFor="date_of_birth" className="block text-sm font-medium text-clinical-text-primary">
                  Date of birth
                </label>
                <input
                  id="date_of_birth"
                  type="date"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  aria-invalid={fieldErrors.date_of_birth ? true : undefined}
                  aria-describedby={fieldErrors.date_of_birth ? 'date-of-birth-error' : undefined}
                  {...register('date_of_birth')}
                />
                {fieldErrors.date_of_birth ? (
                  <p id="date-of-birth-error" className="mt-1 text-sm text-clinical-critical">
                    {fieldErrors.date_of_birth}
                  </p>
                ) : null}
              </div>

              <div>
                <label htmlFor="blood_group" className="block text-sm font-medium text-clinical-text-primary">
                  Blood group
                </label>
                <input
                  id="blood_group"
                  type="text"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  {...register('blood_group')}
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="allergies" className="block text-sm font-medium text-clinical-text-primary">
                  Allergies
                </label>
                <input
                  id="allergies"
                  type="text"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  {...register('allergies')}
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="chronic_conditions" className="block text-sm font-medium text-clinical-text-primary">
                  Chronic conditions
                </label>
                <input
                  id="chronic_conditions"
                  type="text"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  {...register('chronic_conditions')}
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="address" className="block text-sm font-medium text-clinical-text-primary">
                  Address
                </label>
                <input
                  id="address"
                  type="text"
                  autoComplete="street-address"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  {...register('address')}
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="emergency_contact" className="block text-sm font-medium text-clinical-text-primary">
                  Emergency contact
                </label>
                <input
                  id="emergency_contact"
                  type="text"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  {...register('emergency_contact')}
                />
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="claim_patient_uid" className="block text-sm font-medium text-clinical-text-primary">
                  Patient UID
                </label>
                <input
                  id="claim_patient_uid"
                  type="text"
                  className="mt-1 block w-full rounded-md border border-clinical-border bg-clinical-surface px-3 py-2 text-sm text-clinical-text-primary outline-none focus:border-clinical-primary focus:ring-2 focus:ring-clinical-primary-light"
                  {...register('claim_patient_uid')}
                />
                <p className="mt-1 text-sm text-clinical-text-secondary">
                  Enter your Patient UID if your doctor has already pre-registered you.
                </p>
              </div>
            </>
          )}

          <div className="sm:col-span-2">
            <Button className="w-full" type="submit" loading={isSubmitting || signup.isPending}>
              Create account
            </Button>
          </div>
        </form>

        <p className="mt-6 text-center text-sm text-clinical-text-secondary">
          Already have an account?{' '}
          <Link className="font-medium text-clinical-primary hover:underline" to="/login">
            Sign in
          </Link>
        </p>
      </Card>
    </main>
  );
}
