{{/*
Common Job spec for one-off backend tasks. Pass a dict with:
  root      : the chart context ($)
  name      : short name (e.g. "migrate", appended to fullname)
  command   : list of args passed after "python"
  extraEnv  : optional list of env entries
*/}}
{{- define "vandalizer.oneOffJob" -}}
apiVersion: batch/v1
kind: Job
metadata:
  name: {{ include "vandalizer.fullname" .root }}-{{ .name }}
  labels:
    {{- include "vandalizer.labels" .root | nindent 4 }}
    app.kubernetes.io/component: one-off
    vandalizer.io/job: {{ .name }}
spec:
  backoffLimit: 1
  ttlSecondsAfterFinished: 86400
  template:
    metadata:
      labels:
        {{- include "vandalizer.selectorLabels" .root | nindent 8 }}
        app.kubernetes.io/component: one-off
        vandalizer.io/job: {{ .name }}
    spec:
      restartPolicy: Never
      {{- include "vandalizer.imagePullSecrets" .root | nindent 6 }}
      containers:
        - name: {{ .name }}
          image: {{ include "vandalizer.backendImage" .root }}
          imagePullPolicy: {{ .root.Values.image.pullPolicy }}
          command: ["python"]
          args:
            {{- range .command }}
            - {{ . | quote }}
            {{- end }}
          env:
            {{- include "vandalizer.backendEnv" .root | nindent 12 }}
            {{- with .extraEnv }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          envFrom:
            {{- include "vandalizer.backendEnvFrom" .root | nindent 12 }}
          volumeMounts:
            {{- include "vandalizer.uploadsVolumeMount" .root | nindent 12 }}
      volumes:
        {{- include "vandalizer.uploadsVolume" .root | nindent 8 }}
{{- end -}}
