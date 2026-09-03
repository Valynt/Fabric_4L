/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_ENV?: string;
  readonly VITE_API_BASE?: string;
  readonly VITE_API_VERSION_PREFIX?: string;
  readonly VITE_L1_PREFIX?: string;
  readonly VITE_L2_PREFIX?: string;
  readonly VITE_L2_5_PREFIX?: string;
  readonly VITE_L3_PREFIX?: string;
  readonly VITE_L4_PREFIX?: string;
  readonly VITE_L5_PREFIX?: string;
  readonly VITE_L6_PREFIX?: string;
  readonly VITE_LAYER1_ROUTE_PREFIX?: string;
  readonly VITE_LAYER2_ROUTE_PREFIX?: string;
  readonly VITE_LAYER2_5_ROUTE_PREFIX?: string;
  readonly VITE_LAYER3_ROUTE_PREFIX?: string;
  readonly VITE_LAYER4_ROUTE_PREFIX?: string;
  readonly VITE_LAYER5_ROUTE_PREFIX?: string;
  readonly VITE_LAYER6_ROUTE_PREFIX?: string;
  readonly VITE_PROXY_API_GATEWAY_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
