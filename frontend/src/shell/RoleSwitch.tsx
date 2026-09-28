import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';

import { OptionRows } from '@/components/OptionRow';

import { useActiveRole } from './activeRole';
import { roleHomePath, type NavRole } from './navConfig';
import { useWorkspaces } from './useWorkspaces';

/**
 * "Working as" (Design Phase 6 plan Q3: a simple role-switch control; IA
 * §18: make the active context obvious, switch it deliberately). Renders
 * only for someone with more than one role. Switching lands on that role's
 * first screen, so nothing is done in the wrong context by accident.
 */
export function RoleSwitch({ className }: { className?: string }): JSX.Element | null {
  const { t } = useTranslation('common');
  const navigate = useNavigate();
  const { roles, role, setRole } = useActiveRole();
  const { workspaces } = useWorkspaces();

  if (!role || roles.length < 2) return null;

  // Name the actual businesses / groups behind each role, e.g. "Mama Njeri
  // Hardware" under Business, so the choice is unambiguous.
  const describe = (r: NavRole): string => {
    if (r === 'OPERATIONS_OFFICER' || r === 'PLATFORM_ADMIN') return t('role.staffDescription');
    return workspaces
      .filter((w) => w.kind === r)
      .map((w) => w.label)
      .join(', ');
  };

  return (
    <OptionRows<NavRole>
      className={className}
      legend={t('roleSwitch.title')}
      value={role}
      onChange={(next) => {
        setRole(next);
        navigate(roleHomePath(next));
      }}
      options={roles.map((r) => ({ value: r, label: t(`role.${r}`), description: describe(r) }))}
    />
  );
}
