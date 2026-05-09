export type VerificationType = 'approved' | 'edited' | 'rejected';

export interface FieldVerification {
  verification_id: string;
  field_name: string;
  field_value: string | null;
  edited_value: string | null;
  verifier_role: 'doctor' | 'patient';
  verification_type: VerificationType;
  is_final: boolean;
  verified_at: string;
}
