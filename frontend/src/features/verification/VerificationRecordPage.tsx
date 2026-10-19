import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router-dom';

import { ErrorState } from '@/components/ErrorState';
import { PageLoader } from '@/components/PageLoader';
import { localizeError } from '@/services/errorMessage';

import { RecordReview } from './RecordReview';
import { verificationApi } from './verificationApi';

/** One verification record on its own (the applicant page shows them together). */
export function VerificationRecordPage(): JSX.Element {
  const { recordId = '' } = useParams();
  const { t } = useTranslation(['org', 'errors']);

  const record = useQuery({
    queryKey: ['verification-record', recordId],
    queryFn: () => verificationApi.getRecord(recordId),
    retry: false,
  });

  if (record.isLoading) return <PageLoader />;
  if (record.isError || !record.data) {
    return (
      <ErrorState message={localizeError(record.error, t)} error={record.error} onRetry={() => void record.refetch()} />
    );
  }

  return (
    <div className="space-y-5">
      <Link to="/verification" className="text-body-sm text-action-secondary-text">
        &larr; {t('org:common.back')}
      </Link>
      <RecordReview
        record={record.data}
        refresh={[['verification-record', recordId], ['verification-queue'], ['verification-applicants']]}
      />
    </div>
  );
}
