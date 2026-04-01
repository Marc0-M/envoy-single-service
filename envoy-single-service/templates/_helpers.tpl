
{{- define "svc.microservice" -}}
{{ required "microservice is required. Example: --set microservice=audit-services" .Values.microservice }}
{{- end }}

{{- define "svc.group" -}}
{{ required "group is required. Example: --set group=portal-services" .Values.group }}
{{- end }}

{{- define "svc.env" -}}
{{ required "env is required. Example: --set env=devc" .Values.env }}
{{- end }}

{{- define "svc.gatewayName" -}}
{{ required "gateway.name is required. Example: --set gateway.name=https-gw" .Values.gateway.name }}
{{- end }}

{{- define "svc.backendSecret" -}}
{{ required "backend.caSecretName is required. Example: --set backend.caSecretName=portal-backend-ca" .Values.backend.caSecretName }}
{{- end }}

{{- define "envoy-single-service.fullname" -}}
{{- printf "%s-%s-%s" .Values.group .Values.microservice .Values.env | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "envoy-single-service.backendNamespace" -}}
{{- printf "%s-%s" .Values.group .Values.env -}}
{{- end -}}

{{- define "envoy-single-service.gatewayNamespace" -}}
{{- printf "common-gw-%s" .Values.env -}}
{{- end -}}

{{- define "envoy-single-service.serviceName" -}}
{{- default (printf "service-%s" .Values.microservice) .Values.svc -}}
{{- end -}}

{{- define "envoy-single-service.pathPrefix" -}}
{{- default (printf "/%s" .Values.microservice) .Values.pathPrefix -}}
{{- end -}}

{{- define "envoy-single-service.httpRouteName" -}}
{{- printf "%s-route" (include "envoy-single-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "envoy-single-service.referenceGrantName" -}}
{{- printf "%s-refgrant" (include "envoy-single-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "envoy-single-service.backendTLSPolicyName" -}}
{{- printf "%s-btlsp" (include "envoy-single-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "envoy-single-service.backendTrafficPolicyName" -}}
{{- printf "%s-btp" (include "envoy-single-service.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "envoy-single-service.labels" -}}
app.kubernetes.io/name: {{ include "envoy-single-service.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}
