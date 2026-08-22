{{/*
Common helper templates for the Fabric_4L chart.
*/}}

{{/* Expand the name of the chart. */}}
{{- define "fabric.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Create a default fully qualified app name. */}}
{{- define "fabric.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* Create chart name and version. */}}
{{- define "fabric.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Common labels */}}
{{- define "fabric.labels" -}}
helm.sh/chart: {{ include "fabric.chart" . }}
{{ include "fabric.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Selector labels */}}
{{- define "fabric.selectorLabels" -}}
app.kubernetes.io/name: {{ include "fabric.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Service account name */}}
{{- define "fabric.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "fabric.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/* Environment from global or default */}}
{{- define "fabric.environment" -}}
{{- default "dev" .Values.global.environment }}
{{- end }}

{{/* Application image reference for a service or chart default. Digests take precedence over tags. */}}
{{- define "fabric.image" -}}
{{- $root := index . 0 -}}
{{- $svc := index . 1 -}}
{{- $svcImage := default (dict) (default (dict) $svc).image -}}
{{- $imageRepository := default $root.Values.image.repository $svcImage.repository -}}
{{- if not $imageRepository -}}
{{- fail "image.repository is required" -}}
{{- end -}}
{{- $imageTag := default (default "" $root.Values.image.tag) $svcImage.tag | toString -}}
{{- $imageDigest := default (default "" $root.Values.image.digest) $svcImage.digest | toString -}}
{{- if and (eq $imageDigest "") (or (eq $imageTag "") (eq $imageTag "latest")) -}}
{{- fail "image.tag must be explicitly set to a non-latest value or image.digest must be set" -}}
{{- end -}}
{{- if and (ne $imageDigest "") (not (mustRegexMatch "^sha256:[a-f0-9]{64}$" $imageDigest)) -}}
{{- fail "image.digest must be a valid sha256 digest in the form sha256:<64 hex chars>" -}}
{{- end -}}
{{- if ne $imageDigest "" -}}
{{- printf "%s@%s" $imageRepository $imageDigest -}}
{{- else -}}
{{- printf "%s:%s" $imageRepository $imageTag -}}
{{- end -}}
{{- end }}
