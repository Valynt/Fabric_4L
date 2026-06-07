/**
 * Integrations Page — CRM Connection Management
 * 
 * Features:
 * - Configure Salesforce and HubSpot connections
 * - Test connection status
 * - View sync logs and health
 * - Manage OAuth tokens
 */
import React from "react";
import { useLocation } from "react-router-dom";
import { useNavigation } from "@/hooks/useNavigation";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import ErrorBoundary from "@/components/ErrorBoundary";
import {
  IntegrationGrid,
  IntegrationConfigPanel,
  IntegrationList,
  PROVIDER_NAMES,
} from "@/components/integrations";
import {
  useIntegrations,
  useCreateOrUpdateIntegration,
  useDeleteIntegration,
  useStartSalesforceOAuth,
  useTestIntegration,
  useSyncIntegration,
  type CRMProvider,
  type IntegrationCreateRequest,
} from "@/hooks/useIntegrations";
import {
  AlertCircle,
  RefreshCw,
  ExternalLink,
  Key,
  Shield,
} from "lucide-react";
import { PageShell } from "@/components";
import { ErrorState } from "@/components/states/ErrorState";
import { PageHeader, Btn } from "@/components/ui/fabric";

function Integrations() {
  const location = useLocation();
  const { navigateTo } = useNavigation();
  const { data: integrations, isLoading, error, refetch } = useIntegrations();
  const createOrUpdateMutation = useCreateOrUpdateIntegration();
  const deleteMutation = useDeleteIntegration();
  const startSalesforceOAuthMutation = useStartSalesforceOAuth();
  const testMutation = useTestIntegration();
  const syncMutation = useSyncIntegration();

  // Parse selected provider from URL query params
  const searchParams = new URLSearchParams(location.search);
  const selectedProvider = searchParams.get('provider') as CRMProvider | null;
  const oauthStatus = searchParams.get('oauth_status');
  const oauthError = searchParams.get('error');
  const oauthErrorDescription = searchParams.get('error_description');

  React.useEffect(() => {
    if (oauthStatus === 'connected') {
      toast.success('Salesforce connected successfully');
      refetch();
    }
    if (oauthStatus === 'error') {
      toast.error(oauthErrorDescription || oauthError || 'Salesforce connection failed');
    }
  }, [oauthError, oauthErrorDescription, oauthStatus, refetch]);

  const setSelectedProvider = (provider: CRMProvider | null) => {
    if (provider) {
      navigateTo('integrations', undefined, { query: { provider } });
    } else {
      navigateTo('integrations');
    }
  };

  // Get integration by provider
  const getIntegration = (provider: CRMProvider) => {
    return integrations?.find(i => i.provider === provider);
  };

  // Handle provider selection
  const handleSelectProvider = (provider: CRMProvider) => {
    setSelectedProvider(provider === selectedProvider ? null : provider);
  };

  // Handle update/create integration
  const handleUpdate = (provider: CRMProvider, data: IntegrationCreateRequest) => {
    createOrUpdateMutation.mutate(
      { provider, data },
      {
        onSuccess: () => {
          toast.success(`${PROVIDER_NAMES[provider]} integration saved`);
        },
        onError: (error) => {
          toast.error(`Failed to save integration: ${error.message}`);
        },
      }
    );
  };

  // Handle delete integration
  const handleDelete = (provider: CRMProvider) => {
    deleteMutation.mutate(provider, {
      onSuccess: () => {
        toast.success(`${PROVIDER_NAMES[provider]} integration disconnected`);
        if (selectedProvider === provider) {
          setSelectedProvider(null);
        }
      },
      onError: (error) => {
        toast.error(`Failed to disconnect: ${error.message}`);
      },
    });
  };

  // Handle test connection
  const handleTest = (provider: CRMProvider) => {
    testMutation.mutate(provider, {
      onSuccess: (result) => {
        if (result.success) {
          toast.success(`Connection to ${PROVIDER_NAMES[provider]} successful`);
        } else {
          toast.error(`Connection failed: ${result.message}`);
        }
      },
      onError: (error) => {
        toast.error(`Test failed: ${error.message}`);
      },
    });
  };

  // Handle sync
  const handleSync = (provider: CRMProvider) => {
    syncMutation.mutate(provider, {
      onSuccess: () => {
        toast.success(`Sync started for ${PROVIDER_NAMES[provider]}`);
      },
      onError: (error) => {
        toast.error(`Sync failed: ${error.message}`);
      },
    });
  };

  const handleStartSalesforceOAuth = () => {
    startSalesforceOAuthMutation.mutate(
      {
        return_to: location.pathname + location.search,
      },
      {
        onSuccess: (result) => {
          window.location.assign(result.authorization_url || result.authorize_url); // navigation-guardrail: ignore external Salesforce OAuth target
        },
        onError: (startError) => {
          toast.error(`Failed to start Salesforce OAuth: ${startError.message}`);
        },
      }
    );
  };

  // Loading state
  if (isLoading) {
    return (
      <PageShell>
        <Skeleton className="h-8 w-48 mb-8" />
        <Skeleton className="h-4 w-96 mb-8" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <Skeleton className="h-48 w-full rounded-xl" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
          <div className="lg:col-span-1">
            <Skeleton className="h-96 w-full rounded-xl" />
          </div>
        </div>
      </PageShell>
    );
  }

  // Error state
  if (error) {
    return (
      <PageShell>
        <PageHeader
          title="Integrations"
          subtitle="Connect and manage your CRM data sources"
        />
        <ErrorState
          title="Failed to load integrations"
          description="We couldn't retrieve your integrations. Please try again."
          error={error}
          onRetry={() => refetch()}
        />
      </PageShell>
    );
  }

  const selectedIntegration = selectedProvider ? getIntegration(selectedProvider) : undefined;

  return (
    <PageShell>
        {/* Header */}
        <PageHeader
          title="Integrations"
          subtitle="Connect and manage your CRM data sources"
        />

        {/* Info Banner */}
        <div className="mt-6 p-4 bg-primary/10 border border-primary/20 rounded-xl">
          <div className="flex items-start gap-3">
            <Shield size={18} className="text-primary mt-0.5" />
            <div>
              <p className="vf-text-body-m font-medium text-foreground">Secure Integration</p>
              <p className="vf-text-body-s text-primary mt-1">
                Your CRM credentials are encrypted at rest and only used for syncing account data.
                OAuth tokens are refreshed automatically when possible.
              </p>
            </div>
          </div>
        </div>

        {/* Main Content: Grid + Panel */}
        <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Grid + List */}
          <div className="lg:col-span-2 space-y-6">
            <IntegrationGrid
              integrations={integrations}
              selectedProvider={selectedProvider}
              onSelect={handleSelectProvider}
            />
            <IntegrationList
              integrations={integrations}
              selectedProvider={selectedProvider}
              onSelect={handleSelectProvider}
              onSync={handleSync}
              isSyncing={syncMutation.isPending}
              syncingProvider={syncMutation.variables || null}
            />
          </div>

          {/* Right Column: Config Panel */}
          <div className="lg:col-span-1">
            <IntegrationConfigPanel
              provider={selectedProvider}
              integration={selectedIntegration}
              onUpdate={(data: IntegrationCreateRequest) => selectedProvider && handleUpdate(selectedProvider, data)}
              onDelete={() => selectedProvider && handleDelete(selectedProvider)}
              onTest={() => selectedProvider && handleTest(selectedProvider)}
              onSync={() => selectedProvider && handleSync(selectedProvider)}
              onStartOAuth={handleStartSalesforceOAuth}
              isUpdating={createOrUpdateMutation.isPending}
              isTesting={testMutation.isPending}
              isSyncing={syncMutation.isPending && syncMutation.variables === selectedProvider}
              isStartingOAuth={startSalesforceOAuthMutation.isPending}
            />
          </div>
        </div>

        {/* Documentation */}
        <div className="mt-12 p-6 bg-card border border-border rounded-xl">
          <h3 className="vf-text-body-l font-semibold text-foreground mb-4">Getting Started</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <a
              href="https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/intro_understanding_authentication.htm"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-4 bg-muted rounded-lg border border-border hover:border-primary/30 hover:bg-primary/5 transition-colors"
            >
              <div className="w-10 h-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
                <Key size={18} />
              </div>
              <div>
                <p className="vf-text-body-m font-medium text-foreground">Salesforce Setup Guide</p>
                <p className="vf-text-caption text-muted-foreground mt-1">
                  Learn how to create a connected app and generate OAuth tokens.
                </p>
                <span className="inline-flex items-center gap-1 vf-text-caption text-primary mt-2">
                  View Documentation
                  <ExternalLink size={10} />
                </span>
              </div>
            </a>

            <a
              href="https://developers.hubspot.com/docs/api/private-apps"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-4 bg-muted rounded-lg border border-border hover:border-warning/30 hover:bg-warning/5 transition-colors"
            >
              <div className="w-10 h-10 rounded-lg bg-warning/10 text-warning flex items-center justify-center shrink-0">
                <Key size={18} />
              </div>
              <div>
                <p className="vf-text-body-m font-medium text-foreground">HubSpot Setup Guide</p>
                <p className="vf-text-caption text-muted-foreground mt-1">
                  Create a private app and generate an access token for API access.
                </p>
                <span className="inline-flex items-center gap-1 vf-text-caption text-warning mt-2">
                  View Documentation
                  <ExternalLink size={10} />
                </span>
              </div>
            </a>
          </div>
        </div>
      </PageShell>
  );
}

export default function IntegrationsPage() {
  return (
    <ErrorBoundary>
      <Integrations />
    </ErrorBoundary>
  );
}
