{{/*
Common helpers for the Vandalizer chart.
*/}}

{{- define "vandalizer.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "vandalizer.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{- define "vandalizer.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Common labels applied to every object. */}}
{{- define "vandalizer.labels" -}}
helm.sh/chart: {{ include "vandalizer.chart" . }}
app.kubernetes.io/name: {{ include "vandalizer.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/* Selector labels — must be stable across upgrades. */}}
{{- define "vandalizer.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vandalizer.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/* Component-specific names (api, frontend, mongo, redis, chromadb, celery-<queue>, celery-beat). */}}
{{- define "vandalizer.componentName" -}}
{{- printf "%s-%s" (include "vandalizer.fullname" .root) .component | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Image references — registry must be set via an environment values file. */}}
{{- define "vandalizer.backendImage" -}}
{{- $registry := required "image.registry is required — pass -f values-<env>.yaml" .Values.image.registry -}}
{{- $tag := .Values.image.backend.tag | default .Chart.AppVersion -}}
{{- printf "%s/%s:%s" $registry .Values.image.backend.repository $tag -}}
{{- end -}}

{{- define "vandalizer.frontendImage" -}}
{{- $registry := required "image.registry is required — pass -f values-<env>.yaml" .Values.image.registry -}}
{{- $tag := .Values.image.frontend.tag | default .Chart.AppVersion -}}
{{- printf "%s/%s:%s" $registry .Values.image.frontend.repository $tag -}}
{{- end -}}

{{/* Shared env: points pods at in-cluster services plus ConfigMap + Secret envFrom. */}}
{{- define "vandalizer.backendEnv" -}}
- name: REDIS_HOST
  value: {{ include "vandalizer.fullname" . }}-redis
- name: MONGO_HOST
  value: mongodb://{{ include "vandalizer.fullname" . }}-mongo:{{ .Values.mongo.service.port }}/
- name: CHROMADB_HOST
  value: {{ include "vandalizer.fullname" . }}-chromadb:{{ .Values.chromadb.service.port }}
{{- end -}}

{{- define "vandalizer.backendEnvFrom" -}}
- configMapRef:
    name: {{ include "vandalizer.fullname" . }}-backend-env
- secretRef:
    name: {{ .Values.secrets.backendEnvSecret }}
{{- end -}}

{{/* Shared uploads volume mount for api + celery. */}}
{{- define "vandalizer.uploadsVolume" -}}
- name: uploads
  persistentVolumeClaim:
    claimName: {{ include "vandalizer.fullname" . }}-uploads
{{- end -}}

{{- define "vandalizer.uploadsVolumeMount" -}}
- name: uploads
  mountPath: /app/static/uploads
{{- end -}}

{{- define "vandalizer.imagePullSecrets" -}}
{{- with .Values.image.pullSecrets }}
imagePullSecrets:
{{- range . }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end -}}
