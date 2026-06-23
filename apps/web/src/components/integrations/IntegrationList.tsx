import React from 'react';
import {
  Cloud,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Play,
  Settings,
} from 'lucide-react';
import type { Integration, CRMProvider } from '@/hooks/useIntegrations';
import { PROVIDER_NAMES, PROVIDER_STYLES } from './constants';
import { formatLastSync, formatRecordCount } from './utils';
import { Btn } from "@/components/ui/fabric";

interface IntegrationListProps {
  integrations: Integration[] | undefined;
  selectedProvider: CRMProvider | null;
  onSelect: (provider: CRMProvider) => void;
  onSync: (provider: CRMProvider) => void;
  isSyncing: boolean;
  syncingProvider: CRMProvider | null;
}

export function IntegrationList({
  integrations,
  selectedProvider,
  onSelect,
  onSync,
  isSyncing,
  syncingProvider,
}: IntegrationListProps) {
  // Filter to only enabled/active integrations
  const activeIntegrations = integrations?.filter(i => i.enabled) || [];

  if (activeIntegrations.length === 0) {
    return null; // Don't render if no active integrations
  }

  return (
    <div className="bg-background border border-border rounded-xl overflow-hidden mt-6">
      <div className="px-6 py-4 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground">Active Integrations</h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-muted">
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Provider
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Last Sync
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Records
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {activeIntegrations.map((integration) => {
              const provider = integration.provider as CRMProvider;
              const isSelected = selectedProvider === provider;
              const isThisSyncing = isSyncing && syncingProvider === provider;
              const status = integration.status || 'idle';

              return (
                <tr
                  key={integration.id}
                  className={`hover:bg-muted cursor-pointer transition-colors ${
                    isSelected ? 'bg-primary/10' : ''
                  }`}
                  onClick={() => onSelect(provider)}
                >
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div className={`flex-shrink-0 h-8 w-8 rounded-lg flex items-center justify-center ${PROVIDER_STYLES[provider].gridIconBg} ${PROVIDER_STYLES[provider].gridIconText}`}>
                        <Cloud size={16} />
                      </div>
                      <div className="ml-3">
                        <div className="vf-text-body-m font-medium text-foreground">
                          {PROVIDER_NAMES[provider]}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full vf-text-caption font-medium ${
                      status === 'failed'
                        ? 'bg-destructive/10 text-destructive'
                        : status === 'running'
                        ? 'bg-warning/10 text-warning'
                        : 'bg-success/10 text-success'
                    }`}>
                      {status === 'failed' ? (
                        <>
                          <AlertCircle size={10} />
                          Error
                        </>
                      ) : status === 'running' ? (
                        <>
                          <Loader2 size={10} className="animate-spin" />
                          Syncing
                        </>
                      ) : (
                        <>
                          <CheckCircle2 size={10} />
                          Active
                        </>
                      )}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="vf-text-body-m text-foreground">
                      {formatLastSync(integration.last_successful_sync_at)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="vf-text-body-m text-foreground">
                      {formatRecordCount(integration.records_synced)}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Btn
                        variant="ghost"
                        onClick={() => onSelect(provider)}
                        className="px-2 py-1 vf-text-body-s"
                      >
                        <Settings size={14} className="mr-1" />
                        Configure
                      </Btn>
                      <Btn
                        variant={isThisSyncing ? 'ghost' : 'outline'}
                        onClick={() => onSync(provider)}
                        disabled={isThisSyncing}
                        className="px-2 py-1 vf-text-body-s"
                      >
                        {isThisSyncing ? (
                          <>
                            <Loader2 size={14} className="animate-spin mr-1" />
                            Syncing
                          </>
                        ) : (
                          <>
                            <Play size={14} className="mr-1" />
                            Sync
                          </>
                        )}
                      </Btn>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
