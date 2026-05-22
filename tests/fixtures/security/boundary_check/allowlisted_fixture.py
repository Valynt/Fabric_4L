def compatibility_only(request):
    return request.headers.get("X-Tenant-ID")
