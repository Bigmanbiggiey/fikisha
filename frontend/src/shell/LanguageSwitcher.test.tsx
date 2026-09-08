import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it } from 'vitest';

import i18n from '@/i18n';
import { renderWithProviders } from '@/test/renderWithProviders';

import { LanguageSwitcher } from './LanguageSwitcher';

describe('LanguageSwitcher', () => {
  afterEach(async () => {
    await i18n.changeLanguage('en');
  });

  it('switches the active language to Swahili', async () => {
    renderWithProviders(<LanguageSwitcher />, { withAuth: false });
    const select = screen.getByRole('combobox', { name: /language|lugha/i });

    expect(i18n.resolvedLanguage).toBe('en');
    await userEvent.selectOptions(select, 'sw');

    await waitFor(() => expect(i18n.resolvedLanguage).toBe('sw'));
    expect(localStorage.getItem('fikisha.lang')).toBe('sw');
  });
});
