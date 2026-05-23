import React from 'react';
import { Cloud, CloudOff, CheckCircle2, AlertCircle, Loader2, Plus } from 'lucide-react';
import type { Integration, CRMProvider } from '@/hooks/useIntegrations';
import { PROVIDER_STYLES, PROVIDER_NAMES } from './constants';
import { getStatusText, getStatusTextColor } from './utils';

interface IntegrationGridProps {
  integrations: Integration[] | undefined;
  selectedProvider: CRMProvider | null;
  onSelect: (provider: CRMProvider) => void;
}

export function IntegrationGrid({
  integrations,
  selectedProvider,
  onSelect,
}: IntegrationGridProps) {
  // Get configured providers
  const configuredProviders = integrations?.map(i => i.provider) || [];
  const hasIntegrations = configuredProviders.length > 0;

  // Empty state - show available providers to configure
  if (!hasIntegrations) {
    return (
      <div className="bg-white border border-border rounded-xl p-8">
        <h3 className="text-sm font-semibold text-foreground mb-2">Available Integrations</h3>
        <p className="text-sm text-muted-foreground mb-6">
          Select a provider to configure your first integration
        </p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {(Object.keys(PROVIDER_STYLES) as CRMProvider[]).map((provider) => {
            const style = PROVIDER_STYLES[provider];
            return (
              <button
                key={provider}
                onClick={() => onSelect(provider)}
                className="flex flex-col items-center p-6 bg-muted border border-border rounded-xl hover:border-blue-300 hover:bg-blue-50/30 transition-colors text-center"
              >
                <div className={`w-12 h-12 rounded-xl ${style.iconBg} ${style.iconText} flex items-center justify-center mb-3`}>
                  <Plus size={24} />
                </div>
                <span className="text-sm font-medium text-foreground">{PROVIDER_NAMES[provider]}</span>
                <span className="text-xs text-muted-foreground mt-1">Click to configure</span>
              </button>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border border-border rounded-xl p-6">
      <h3 className="text-sm font-semibold text-foreground mb-4">
        Configured Integrations ({configuredProviders.length})
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        {configuredProviders.map((provider) => {
          const integration = integrations?.find(i => i.provider === provider);
          const style = PROVIDER_STYLES[provider];
          const isSelected = selectedProvider === provider;
          const isConnected = integration?.enabled || false;
          const status = integration?.status || 'idle';

          return (
            <button
              key={provider}
              onClick={() => onSelect(provider)}
              className={`relative flex flex-col items-start p-4 border rounded-xl transition-all text-left ${
                isSelected
                  ? 'border-blue-500 ring-2 ring-blue-500/20 bg-blue-50/30'
                  : 'border-neutral-200 hover:border-neutral-300 bg-white'
              }`}
            >
              {/* Status indicator */}
              <div className="absolute top-3 right-3">
                {isConnected ? (
                  status === 'failed' ? (
                    <AlertCircle size={16} className="text-red-500" />
                  ) : status === 'running' ? (
                    <Loader2 size={16} className="text-amber-500 animate-spin" />
                  ) : (
                    <CheckCircle2 size={16} className="text-emerald-500" />
                  )
                ) : (
                  <CloudOff size={16} className="text-neutral-400" />
                )}
              </div>

              {/* Icon */}
              <div className={`w-10 h-10 rounded-lg ${style.iconBg} ${style.iconText} flex items-center justify-center mb-3`}>
                {style.icon}
              </div>

              {/* Name */}
              <span className="text-[14px] font-semibold text-neutral-800">{PROVIDER_NAMES[provider]}</span>

              {/* Status label */}
              <span className={`text-[11px] mt-1 ${getStatusTextColor(status, isConnected)}`}>
                {getStatusText(status, isConnected)}
              </span>

              {/* Records synced hint */}
              {integration && integration.records_synced > 0 && (
                <span className="text-[10px] text-neutral-400 mt-2">
                  {integration.records_synced.toLocaleString()} records synced
                </span>
              )}
            </button>
          );
        })}

        {/* Add new integration placeholder */}
        {configuredProviders.length < Object.keys(PROVIDER_STYLES).length && (
          <button
            onClick={() => {
              const unconfigured = (Object.keys(PROVIDER_STYLES) as CRMProvider[]).find(
                p => !configuredProviders.includes(p)
              );
              if (unconfigured) onSelect(unconfigured);
            }}
            className="flex flex-col items-center justify-center p-4 border border-dashed border-neutral-300 rounded-xl hover:border-blue-300 hover:bg-blue-50/30 transition-colors min-h-[120px]"
          >
            <Plus size={24} className="text-neutral-400 mb-2" />
            <span className="text-[12px] text-neutral-500">Add integration</span>
          </button>
        )}
      </div>
    </div>
  );
}
