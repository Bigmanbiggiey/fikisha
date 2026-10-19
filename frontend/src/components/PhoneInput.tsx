import { forwardRef, useState, type InputHTMLAttributes } from 'react';
import { useTranslation } from 'react-i18next';

import { isValidKenyanPhone } from '@/services/phone';

import { Input } from './Input';

export interface PhoneInputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'onChange'> {
  value: string;
  onChange: (value: string) => void;
  invalid?: boolean;
}

/**
 * A phone number field with the Kenyan rule (assessment 2026-10-20 L-3):
 * once the person leaves the field, a number that isn't `07…`/`01…`/`+254…`
 * with 10 digits gets a plain message. The server checks the same rule; the
 * form should also keep its submit button disabled while it is invalid.
 */
export const PhoneInput = forwardRef<HTMLInputElement, PhoneInputProps>(function PhoneInput(
  { value, onChange, invalid = false, onBlur, ...rest },
  ref,
) {
  const { t } = useTranslation('common');
  const [touched, setTouched] = useState(false);
  const bad = touched && value.trim() !== '' && !isValidKenyanPhone(value);
  return (
    <>
      <Input
        ref={ref}
        {...rest}
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        value={value}
        invalid={invalid || bad}
        onChange={(e) => onChange(e.target.value)}
        onBlur={(e) => {
          setTouched(true);
          onBlur?.(e);
        }}
      />
      {bad && (
        <p role="alert" className="mt-1 text-body-sm text-status-danger-fg">
          {t('phone.invalid')}
        </p>
      )}
    </>
  );
});
