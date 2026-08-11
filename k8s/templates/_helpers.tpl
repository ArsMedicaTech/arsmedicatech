{{- define "surrealdb.sharedEnv" -}}
- name: COGNITO_DOMAIN
  value: "{{ .Values.auth.cognito.cognitoDomain }}"
- name: USER_POOL_ID
  value: "{{ .Values.auth.cognito.userPoolId }}"
- name: USER_POOL_CLIENT_ID
  value: "{{ .Values.auth.cognito.userPoolClientId }}"
- name: USER_POOL_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: cognito-secret
      key: userPoolClientSecret
- name: DEBUG
  value: "false"
- name: PYTHONPATH
  value: "/app"
- name: S3_BUCKET
  value: "{{ .Values.s3Bucket }}"
- name: REDIS_HOST
  value: "{{ .Values.redis.host }}"
- name: REDIS_PORT
  value: "{{ .Values.redis.port }}"
- name: SURREALDB_NAMESPACE
  value: "{{ .Values.surrealdb.namespace }}"
- name: SURREALDB_DATABASE
  value: "{{ .Values.surrealdb.database }}"
- name: SURREALDB_PROTOCOL
  value: "{{ .Values.surrealdb.protocol }}"
- name: SURREALDB_HOST
  value: "{{ .Values.surrealdb.host }}"
- name: SURREALDB_PORT
  value: "{{ .Values.surrealdb.port }}"
- name: SURREALDB_USER
  valueFrom:
    secretKeyRef:
      name: surreal-secret
      key: user
- name: SURREALDB_PASS
  valueFrom:
    secretKeyRef:
      name: surreal-secret
      key: pass
- name: MIGRATION_OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: migration-openai-secret
      key: apiKey
- name: ENCRYPTION_KEY
  valueFrom:
    secretKeyRef:
      name: encryption-key
      key: ENCRYPTION_KEY
- name: MINIO_ENDPOINT
  value: "{{ .Values.minio.endpoint }}"
- name: MINIO_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: minio-secret
      key: accessKey
- name: MINIO_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: minio-secret
      key: secretKey
- name: MINIO_ENCOUNTER_RECORDINGS_BUCKET
  value: "{{ .Values.minio.encounterRecordingsBucket }}"
- name: KEYCLOAK_CLIENT_ID
  value: "{{ .Values.auth.keycloak.clientId }}"
- name: KEYCLOAK_CLIENT_SECRET
  valueFrom:
    secretKeyRef:
      name: keycloak-secret
      key: clientSecret
- name: KEYCLOAK_REALM
  value: "{{ .Values.auth.keycloak.realm }}"
- name: KEYCLOAK_AUTH_HOST
  value: "{{ .Values.auth.keycloak.authHost }}"
- name: CORS_ORIGINS
  value: "{{ .Values.flask.corsOrigins | join "," }}"
- name: FRONTEND_REDIRECT
  value: "{{ .Values.flask.frontendRedirect }}"
{{- end }}
