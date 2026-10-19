import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';

import { Alert } from '@/components/Alert';
import { verificationApi } from '@/features/verification/verificationApi';

import { orgApi } from './orgApi';

/**
 * Tells a business where its verification stands (assessment 2026-10-19,
 * D-1). Renders nothing once the business is verified. The business's own
 * `verification_status` is what the server checks before a job is sent; the
 * details record says why it is not verified yet.
 */
export function BusinessVerificationBanner({
  businessId,
  showLink = true,
}: {
  businessId: string;
  /** link to the business page (off on the business page itself) */
  showLink?: boolean;
}): JSX.Element | null {
  const { t } = useTranslation('org');
  const business = useQuery({
    queryKey: ['business', businessId],
    queryFn: () => orgApi.getBusiness(businessId),
  });
  const status = useQuery({
    queryKey: ['verification-status', 'BUSINESS', businessId],
    queryFn: () => verificationApi.subjectStatus('BUSINESS', businessId),
    retry: false,
  });
  if (!business.data || business.data.verification_status === 'VERIFIED') return null;

  const state = status.data?.eligibility.BUSINESS ?? 'NOT_SUBMITTED';
  const key =
    state === 'INFO_REQUESTED'
      ? 'infoRequested'
      : state === 'REJECTED'
        ? 'rejected'
        : state === 'NOT_SUBMITTED' || state === 'EXPIRED'
          ? 'notSubmitted'
          : 'pending';
  return (
    <Alert tone={key === 'pending' ? 'info' : 'warning'} title={t(`businessVerification.${key}Title`)}>
      <p>{t(`businessVerification.${key}Body`)}</p>
      {showLink && (
        <p className="mt-1">
          <Link to={`/businesses/${businessId}`} className="font-semibold underline">
            {t('businessVerification.open')}
          </Link>
        </p>
      )}
    </Alert>
  );
}
