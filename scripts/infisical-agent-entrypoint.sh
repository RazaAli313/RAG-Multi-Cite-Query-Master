#!/bin/sh
set -e

mkdir -p /tmp/credentials /secrets
rm -f /secrets/app.env

printf '%s' "${INFISICAL_CLIENT_ID}" > /tmp/credentials/client-id
printf '%s' "${INFISICAL_CLIENT_SECRET}" > /tmp/credentials/client-secret
chmod 600 /tmp/credentials/client-id /tmp/credentials/client-secret

# Write the secrets template (quoted heredoc keeps Go template syntax intact)
cat > /tmp/secrets.tpl << 'TMPL'
{{- with secret "PROJECT_ID" "ENV_SLUG" "/" `{"recursive": true, "expandSecretReferences": true}` }}
{{- range . }}
export {{.Key}}="{{.Value}}"
{{- end }}
{{- end }}
TMPL

sed -i \
  -e "s|PROJECT_ID|${INFISICAL_PROJECT_ID}|g" \
  -e "s|ENV_SLUG|${INFISICAL_ENVIRONMENT_SLUG}|g" \
  /tmp/secrets.tpl

# Write the agent config (regular heredoc expands shell variables)
cat > /tmp/agent.yaml << YAML
infisical:
  address: "${INFISICAL_HOST}"
auth:
  type: "universal-auth"
  config:
    client-id: "/tmp/credentials/client-id"
    client-secret: "/tmp/credentials/client-secret"
templates:
  - source-path: /tmp/secrets.tpl
    destination-path: /secrets/app.env
    config:
      polling-interval: 60s
YAML

exec infisical agent --config /tmp/agent.yaml
