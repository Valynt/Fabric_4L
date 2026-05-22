def bad_patterns(request, payload, api_key):
    tenant = request.headers.get("X-Tenant-ID")
    maybe = request.query_params.get("tenant_id")
    data_tenant = payload.get("tenant_id")
    key_tenant = api_key.tenant_id
    fallback = getattr(api_key, "tenant_id", None)
    return tenant, maybe, data_tenant, key_tenant, fallback
